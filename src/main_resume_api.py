from __future__ import annotations

import asyncio
import os
import secrets
import tempfile
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import Main_Resume as resume_parser


_SRC_ENV_PATH = Path(__file__).resolve().parent / ".env"
_ROOT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_SRC_ENV_PATH)
load_dotenv(_ROOT_ENV_PATH)

API_KEY_HEADER = "x-api-key"
SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "false").strip().lower() in {"1", "true", "yes", "on"}
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "6000"))
PARSER_RETRY_COUNT = max(0, int(os.getenv("PARSER_RETRY_COUNT", "0")))
PARSER_SERIALIZE = os.getenv("PARSER_SERIALIZE", "false").strip().lower() in {"1", "true", "yes", "on"}
TRUSTED_HOSTS = [h.strip() for h in os.getenv("TRUSTED_HOSTS", "*").split(",") if h.strip()]

# High-concurrency tuning parameters (for 1200+ concurrent requests)
PARSER_MAX_WORKERS = int(os.getenv("PARSER_MAX_WORKERS", str(min(64, (os.cpu_count() or 4) * 4))))
MAX_CONCURRENT_PARSES = int(os.getenv("MAX_CONCURRENT_PARSES", "100"))

_SKILLS_LIST_CACHE = None
_COMPILED_MATCHERS_CACHE = None
_SKILL_SOURCE_CACHE = None
_CACHE_LOCK = threading.Lock()
_RATE_LIMIT_LOCK = threading.Lock()
_PARSER_LOCK = threading.Lock()
_REQUEST_HISTORY = defaultdict(deque)

_PARSER_EXECUTOR: ThreadPoolExecutor | None = None
_PARSE_SEMAPHORE: asyncio.Semaphore | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _PARSER_EXECUTOR
    if _PARSER_EXECUTOR is None:
        _PARSER_EXECUTOR = ThreadPoolExecutor(max_workers=PARSER_MAX_WORKERS, thread_name_prefix="resume_worker")
    return _PARSER_EXECUTOR


def _get_semaphore() -> asyncio.Semaphore:
    global _PARSE_SEMAPHORE
    if _PARSE_SEMAPHORE is None:
        _PARSE_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_PARSES)
    return _PARSE_SEMAPHORE


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm dataset caches and initialize worker threadpool on startup."""
    _get_parser_context()
    _get_executor()
    yield
    global _PARSER_EXECUTOR
    if _PARSER_EXECUTOR is not None:
        _PARSER_EXECUTOR.shutdown(wait=False)
        _PARSER_EXECUTOR = None


app = FastAPI(title="Main Resume API", version="1.0.0", lifespan=lifespan)


def _load_api_key() -> str:
    key = (os.getenv("API_KEY") or "").strip()
    if not key:
        key = "dev-secret-key"  # Allow dev mode without requiring env var
    return key


API_KEY = _load_api_key()

# Configure CORS
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8501").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if TRUSTED_HOSTS and "*" not in TRUSTED_HOSTS:
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
    if not ENABLE_RATE_LIMIT:
        return

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

    def _extract_once() -> dict:
        if PARSER_SERIALIZE:
            with _PARSER_LOCK:
                return resume_parser._extract_resume_record(
                    fname=temp_fname,
                    process_folder=process_folder,
                    skill_source=skill_source,
                    skills_list=skills_list,
                    compiled_skill_matchers=compiled_matchers,
                    fast_response=False,
                )

        return resume_parser._extract_resume_record(
            fname=temp_fname,
            process_folder=process_folder,
            skill_source=skill_source,
            skills_list=skills_list,
            compiled_skill_matchers=compiled_matchers,
            fast_response=False,
        )

    def _record_score(rec: dict) -> int:
        if not isinstance(rec, dict):
            return -1
        score = 0
        for key in ("name", "contact_number", "email", "dob", "gender", "address"):
            if rec.get(key):
                score += 1
        if rec.get("skills"):
            score += 1
        if rec.get("professional_experience"):
            score += 1
        if rec.get("education"):
            score += 1
        return score

    record = _extract_once()

    attempts_left = PARSER_RETRY_COUNT
    best_record = record
    best_score = _record_score(record)
    while attempts_left > 0 and best_score < 7:
        candidate = _extract_once()
        candidate_score = _record_score(candidate)
        if candidate_score > best_score:
            best_record = candidate
            best_score = candidate_score
        attempts_left -= 1
    record = best_record

    if not isinstance(record, dict):
        raise RuntimeError("Invalid parser response format")
    if record.get("error"):
        raise RuntimeError(str(record.get("error")))

    record["file"] = (display_filename or temp_fname).strip()
    return record


async def _parse_single_file_async(file: UploadFile) -> dict:
    """Helper to process a single file upload concurrently with semaphore backpressure control."""
    sem = _get_semaphore()
    async with sem:
        if file.content_type and file.content_type not in {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Only PDF, DOC, and DOCX are allowed.",
            )

        suffix = _validate_upload_filename(file.filename)
        temp_path = await _save_upload_to_tempfile(file, suffix)

        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(_get_executor(), parse_resume_from_file, temp_path, file.filename)
            return data
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


@app.get("/")
async def root_endpoint():
    """Root endpoint for API documentation and status discovery."""
    return {
        "message": "Main Resume API Service is operational",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """Unauthenticated health check endpoint for load balancers and container probes."""
    return {"status": "ok"}


@app.post("/parse")
async def parse_endpoint(file: UploadFile = File(...), _: str = Depends(verify_api_key)):
    try:
        data = await _parse_single_file_async(file)
        return JSONResponse(status_code=status.HTTP_200_OK, content=data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to parse this resume",
        ) from exc


@app.post("/parse-batch")
async def parse_batch_endpoint(files: list[UploadFile] = File(...), _: str = Depends(verify_api_key)):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required.",
        )

    async def _process_file_item(file: UploadFile) -> dict:
        try:
            data = await _parse_single_file_async(file)
            return {"file": file.filename, "success": True, "data": data}
        except HTTPException as exc:
            return {"file": file.filename, "success": False, "error": str(exc.detail)}
        except Exception:
            return {"file": file.filename, "success": False, "error": "Unable to parse this resume"}

    results = await asyncio.gather(*[_process_file_item(f) for f in files])
    return JSONResponse(status_code=status.HTTP_200_OK, content={"count": len(results), "results": list(results)})