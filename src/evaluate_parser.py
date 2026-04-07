"""
Resume parser evaluation CLI.

Provides two kinds of evaluation:
1. Performance benchmarking for text-only extraction and full parsing.
2. Accuracy scoring against a JSON file of gold labels.

Example usage:
    .venv\Scripts\python.exe src\evaluate_parser.py --mode perf --limit 20
    .venv\Scripts\python.exe src\evaluate_parser.py --mode perf --workers 1 2 4 8
    .venv\Scripts\python.exe src\evaluate_parser.py --mode accuracy --labels tests\resume_gold_labels.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Iterable, List, Optional, Tuple

import Main_Resume as parser_module


DEFAULT_FOLDER = parser_module.RESUME_FOLDER
DEFAULT_WORKERS = [1, 2, 4, parser_module.DEFAULT_MAX_WORKERS]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate resume parser performance and accuracy")
    parser.add_argument(
        "--mode",
        choices=("perf", "accuracy", "both"),
        default="both",
        help="Which evaluation to run",
    )
    parser.add_argument(
        "--folder",
        default=DEFAULT_FOLDER,
        help="Folder containing resumes to process",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of files (0 = all)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        nargs="+",
        default=DEFAULT_WORKERS,
        help="Worker counts to benchmark",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Benchmark repeats per worker count",
    )
    parser.add_argument(
        "--skill-source",
        choices=("auto", "csv", "dataset"),
        default="auto",
        help="Skill extraction source for full parsing",
    )
    parser.add_argument(
        "--fast-response",
        action="store_true",
        help="Skip slower fields like gender/address during full parsing",
    )
    parser.add_argument(
        "--labels",
        help="Path to JSON gold labels for accuracy mode",
    )
    return parser.parse_args()


def get_resume_files(folder: str, limit: int = 0) -> List[str]:
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Resume folder not found: {folder}")

    files = [
        name
        for name in os.listdir(folder)
        if os.path.splitext(name)[1].lower() in parser_module.SUPPORTED_EXTENSIONS
    ]
    files.sort(key=parser_module.natural_file_sort_key)
    if limit > 0:
        files = files[:limit]
    if not files:
        raise FileNotFoundError(f"No supported resume files found in: {folder}")
    return files


def load_skill_context(skill_source: str) -> Tuple[List[str], Optional[object]]:
    skills_list: List[str] = []
    compiled_skill_matchers = None

    if skill_source in {"csv", "auto"}:
        skills_list = parser_module.load_skills_from_csv(parser_module.SKILLS_CSV)
        compiled_skill_matchers = parser_module.build_skill_matchers(skills_list)

    if skill_source == "dataset" or (skill_source == "auto" and not compiled_skill_matchers):
        parser_module._ensure_skillner_loaded()

    return skills_list, compiled_skill_matchers


def run_text_extract(folder: str, fname: str) -> Dict:
    path = os.path.join(folder, fname)
    try:
        text = parser_module.extract_text(path)
        return {
            "file": fname,
            "text_length": len(text),
        }
    except Exception as exc:
        return {
            "file": fname,
            "text_length": 0,
            "error": str(exc),
        }


def run_full_extract(
    folder: str,
    fname: str,
    skill_source: str,
    skills_list: List[str],
    compiled_skill_matchers,
    fast_response: bool,
) -> Dict:
    return parser_module._extract_resume_record(
        fname,
        folder,
        skill_source,
        skills_list,
        compiled_skill_matchers,
        fast_response,
    )


def benchmark_once(
    files: List[str],
    folder: str,
    workers: int,
    mode: str,
    skill_source: str,
    skills_list: List[str],
    compiled_skill_matchers,
    fast_response: bool,
) -> Dict:
    start = time.perf_counter()

    def task(fname: str) -> Dict:
        if mode == "text":
            return run_text_extract(folder, fname)
        return run_full_extract(
            folder,
            fname,
            skill_source,
            skills_list,
            compiled_skill_matchers,
            fast_response,
        )

    if workers <= 1:
        results = [task(fname) for fname in files]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(task, files))

    elapsed = time.perf_counter() - start
    error_count = sum(1 for row in results if row.get("error"))
    total_chars = sum(int(row.get("text_length", 0)) for row in results)
    return {
        "files": len(files),
        "workers": workers,
        "seconds": elapsed,
        "files_per_second": (len(files) / elapsed) if elapsed else 0.0,
        "error_count": error_count,
        "total_text_chars": total_chars,
    }


def benchmark_suite(
    files: List[str],
    folder: str,
    worker_counts: Iterable[int],
    repeats: int,
    fast_response: bool,
    skill_source: str,
) -> Dict[str, List[Dict]]:
    skills_list, compiled_skill_matchers = load_skill_context(skill_source)
    report: Dict[str, List[Dict]] = {"text": [], "full": []}

    for benchmark_mode in ("text", "full"):
        for workers in sorted(set(max(1, int(w)) for w in worker_counts)):
            runs = [
                benchmark_once(
                    files,
                    folder,
                    workers,
                    benchmark_mode,
                    skill_source,
                    skills_list,
                    compiled_skill_matchers,
                    fast_response,
                )
                for _ in range(max(1, repeats))
            ]
            seconds = [row["seconds"] for row in runs]
            throughputs = [row["files_per_second"] for row in runs]
            report[benchmark_mode].append(
                {
                    "workers": workers,
                    "runs": len(runs),
                    "files": len(files),
                    "avg_seconds": statistics.mean(seconds),
                    "min_seconds": min(seconds),
                    "max_seconds": max(seconds),
                    "avg_files_per_second": statistics.mean(throughputs),
                    "best_files_per_second": max(throughputs),
                    "errors": max(row["error_count"] for row in runs),
                }
            )
    return report


def normalize_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def normalize_phone(value: Optional[str]) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_skills(values: Optional[List[str]]) -> List[str]:
    skills = []
    for value in values or []:
        normalized = normalize_text(value)
        if normalized:
            skills.append(normalized)
    return sorted(set(skills))


def field_match(field: str, expected, actual) -> bool:
    if field == "contact_number":
        return normalize_phone(expected) == normalize_phone(actual)
    if field == "skills":
        expected_skills = set(normalize_skills(expected))
        actual_skills = set(normalize_skills(actual))
        return expected_skills.issubset(actual_skills)
    return normalize_text(expected) == normalize_text(actual)


def score_accuracy(
    files: List[str],
    folder: str,
    labels_path: str,
    skill_source: str,
    fast_response: bool,
) -> Dict:
    if not labels_path:
        raise ValueError("--labels is required for accuracy mode")
    if not os.path.exists(labels_path):
        raise FileNotFoundError(f"Labels file not found: {labels_path}")

    with open(labels_path, "r", encoding="utf-8") as fh:
        gold = json.load(fh)

    if not isinstance(gold, dict):
        raise ValueError("Labels JSON must be an object keyed by file name")

    skills_list, compiled_skill_matchers = load_skill_context(skill_source)
    per_file = []
    field_totals: Dict[str, Dict[str, int]] = {}

    for fname in files:
        expected = gold.get(fname)
        if not expected:
            continue

        actual = run_full_extract(
            folder,
            fname,
            skill_source,
            skills_list,
            compiled_skill_matchers,
            fast_response,
        )

        checks = {}
        for field, expected_value in expected.items():
            if field == "notes":
                continue
            actual_value = actual.get(field)
            matched = field_match(field, expected_value, actual_value)
            checks[field] = {
                "matched": matched,
                "expected": expected_value,
                "actual": actual_value,
            }
            field_totals.setdefault(field, {"matched": 0, "total": 0})
            field_totals[field]["total"] += 1
            if matched:
                field_totals[field]["matched"] += 1

        total_fields = len(checks)
        matched_fields = sum(1 for item in checks.values() if item["matched"])
        per_file.append(
            {
                "file": fname,
                "matched_fields": matched_fields,
                "total_fields": total_fields,
                "score": (matched_fields / total_fields * 100.0) if total_fields else 0.0,
                "checks": checks,
            }
        )

    summary_fields = {}
    for field, totals in field_totals.items():
        total = totals["total"]
        matched = totals["matched"]
        summary_fields[field] = {
            "matched": matched,
            "total": total,
            "accuracy_percent": (matched / total * 100.0) if total else 0.0,
        }

    overall_total = sum(item["total_fields"] for item in per_file)
    overall_matched = sum(item["matched_fields"] for item in per_file)

    return {
        "labeled_files_seen": len(per_file),
        "overall_matched_fields": overall_matched,
        "overall_total_fields": overall_total,
        "overall_accuracy_percent": (overall_matched / overall_total * 100.0) if overall_total else 0.0,
        "field_accuracy": summary_fields,
        "per_file": per_file,
    }


def print_perf_report(report: Dict[str, List[Dict]]) -> None:
    print("\nPERFORMANCE BENCHMARK")
    print("=" * 72)
    for mode in ("text", "full"):
        print(f"\n[{mode.upper()}]")
        for row in report[mode]:
            print(
                f"workers={row['workers']:>2} | files={row['files']:>3} | "
                f"avg={row['avg_seconds']:.3f}s | min={row['min_seconds']:.3f}s | "
                f"throughput={row['avg_files_per_second']:.2f} files/s | errors={row['errors']}"
            )


def print_accuracy_report(report: Dict) -> None:
    print("\nACCURACY REPORT")
    print("=" * 72)
    print(
        f"Labeled files: {report['labeled_files_seen']} | "
        f"Overall: {report['overall_matched_fields']}/{report['overall_total_fields']} "
        f"({report['overall_accuracy_percent']:.1f}%)"
    )
    print("\nField accuracy:")
    for field, row in sorted(report["field_accuracy"].items()):
        print(
            f"  {field}: {row['matched']}/{row['total']} "
            f"({row['accuracy_percent']:.1f}%)"
        )

    print("\nPer-file scores:")
    for row in report["per_file"]:
        print(
            f"  {row['file']}: {row['matched_fields']}/{row['total_fields']} "
            f"({row['score']:.1f}%)"
        )


def main() -> None:
    args = parse_args()
    files = get_resume_files(args.folder, args.limit)

    if args.mode in {"perf", "both"}:
        perf_report = benchmark_suite(
            files,
            args.folder,
            args.workers,
            args.repeats,
            args.fast_response,
            args.skill_source,
        )
        print_perf_report(perf_report)

    if args.mode in {"accuracy", "both"}:
        accuracy_report = score_accuracy(
            files,
            args.folder,
            args.labels,
            args.skill_source,
            args.fast_response,
        )
        print_accuracy_report(accuracy_report)


if __name__ == "__main__":
    main()
