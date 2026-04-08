from __future__ import annotations

import os
import secrets
import tempfile
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

import Main_Resume as resume_parser


_SRC_ENV_PATH = Path(__file__).resolve().parent / ".env"
_ROOT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_SRC_ENV_PATH)
load_dotenv(_ROOT_ENV_PATH)


app = FastAPI(title="Main Resume API", version="1.0.0")

API_KEY_HEADER = "x-api-key"
SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
TRUSTED_HOSTS = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "127.0.0.1,localhost,10.215.58.169").split(",") if h.strip()]

_SKILLS_LIST_CACHE = None
_COMPILED_MATCHERS_CACHE = None
_SKILL_SOURCE_CACHE = None
_CACHE_LOCK = threading.Lock()
_RATE_LIMIT_LOCK = threading.Lock()
_REQUEST_HISTORY = defaultdict(deque)


def _load_api_key() -> str:
    key = (os.getenv("API_KEY") or "").strip()
    if not key:
        raise RuntimeError("API_KEY must be set in environment")
    if key == "dev-secret-key" or len(key) < 16:
        raise RuntimeError("API_KEY is too weak; use a strong value with at least 16 characters")
    return key


API_KEY = _load_api_key()

# Configure CORS
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if TRUSTED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)


def _validate_upload_filename(filename: str) -> str:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A file name is required",
        )

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF, DOC, and DOCX are allowed.",
        )
    return suffix


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - 60

    with _RATE_LIMIT_LOCK:
        bucket = _REQUEST_HISTORY[client_ip]
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again in a minute.",
            )

        bucket.append(now)


async def verify_api_key(
    request: Request,
    x_api_key: str = Header(default=None, alias=API_KEY_HEADER),
) -> str:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return x_api_key


async def _save_upload_to_tempfile(upload: UploadFile, suffix: str) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    total_written = 0
    try:
        with temp_file:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Max allowed size is {MAX_UPLOAD_MB} MB.",
                    )
                temp_file.write(chunk)
        return temp_file.name
    except Exception:
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass
        raise


def _get_parser_context():
    global _SKILLS_LIST_CACHE, _COMPILED_MATCHERS_CACHE, _SKILL_SOURCE_CACHE

    if _SKILLS_LIST_CACHE is not None:
        return _SKILLS_LIST_CACHE, _COMPILED_MATCHERS_CACHE, _SKILL_SOURCE_CACHE

    with _CACHE_LOCK:
        if _SKILLS_LIST_CACHE is not None:
            return _SKILLS_LIST_CACHE, _COMPILED_MATCHERS_CACHE, _SKILL_SOURCE_CACHE

        skill_source = getattr(resume_parser, "SKILL_SOURCE", "auto")
        skills_list = []

        try:
            if skill_source in {"csv", "auto"}:
                skills_list = resume_parser.load_skills_from_csv(resume_parser.SKILLS_CSV)
            compiled_matchers = resume_parser.build_skill_matchers(skills_list)
        except Exception:
            compiled_matchers = None

        if skill_source == "dataset" or (skill_source == "auto" and not compiled_matchers):
            resume_parser._ensure_skillner_loaded()
        resume_parser._ensure_names_dataset_loaded()

        _SKILLS_LIST_CACHE = skills_list
        _COMPILED_MATCHERS_CACHE = compiled_matchers
        _SKILL_SOURCE_CACHE = skill_source
        return _SKILLS_LIST_CACHE, _COMPILED_MATCHERS_CACHE, _SKILL_SOURCE_CACHE


def parse_resume_from_file(file_path: str, display_filename: str) -> dict:
    if not file_path or not os.path.exists(file_path):
        raise ValueError("Uploaded file could not be found")

    process_folder = os.path.dirname(file_path)
    temp_fname = os.path.basename(file_path)
    skills_list, compiled_matchers, skill_source = _get_parser_context()

    record = resume_parser._extract_resume_record(
        fname=temp_fname,
        process_folder=process_folder,
        skill_source=skill_source,
        skills_list=skills_list,
        compiled_skill_matchers=compiled_matchers,
        fast_response=False,
    )

    if not isinstance(record, dict):
        raise RuntimeError("Invalid parser response format")
    if record.get("error"):
        raise RuntimeError(str(record.get("error")))

    record["file"] = (display_filename or temp_fname).strip()
    return record


@app.get("/health")
async def health_check(_: str = Depends(verify_api_key)):
    return {"status": "ok"}


@app.post("/parse")
async def parse_endpoint(file: UploadFile = File(...), _: str = Depends(verify_api_key)):
    if file.content_type and file.content_type not in {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported content type. Only PDF, DOC, and DOCX are allowed.",
        )

    suffix = _validate_upload_filename(file.filename)
    temp_path = await _save_upload_to_tempfile(file, suffix)

    try:
        data = await run_in_threadpool(parse_resume_from_file, temp_path, file.filename)
        return JSONResponse(status_code=status.HTTP_200_OK, content=data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to parse this resume",
        ) from exc
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


@app.post("/parse-batch")
async def parse_batch_endpoint(files: list[UploadFile] = File(...), _: str = Depends(verify_api_key)):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required.",
        )

    results = []

    for file in files:
        temp_path = None
        try:
            if file.content_type and file.content_type not in {
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }:
                results.append(
                    {
                        "file": file.filename,
                        "success": False,
                        "error": "Unsupported content type. Only PDF, DOC, and DOCX are allowed.",
                    }
                )
                continue

            suffix = _validate_upload_filename(file.filename)
            temp_path = await _save_upload_to_tempfile(file, suffix)
            data = await run_in_threadpool(parse_resume_from_file, temp_path, file.filename)
            results.append({"file": file.filename, "success": True, "data": data})
        except HTTPException as exc:
            results.append({"file": file.filename, "success": False, "error": str(exc.detail)})
        except Exception:
            results.append({"file": file.filename, "success": False, "error": "Unable to parse this resume"})
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    return JSONResponse(status_code=status.HTTP_200_OK, content={"count": len(results), "results": results})
