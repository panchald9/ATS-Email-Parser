"""
benchmark.py
============
Comprehensive benchmark for the ATS Resume Parser covering:
  1. Performance  - per-file parse time, throughput, memory usage
  2. Accuracy     - field-level extraction vs. ground truth
  3. Quality      - validation scoring on existing parsed output

Usage:
  python benchmark.py                          # all modes, uses Testing Resume folder
  python benchmark.py --mode perf             # performance only
  python benchmark.py --mode accuracy         # accuracy only (needs ground_truth.json)
  python benchmark.py --mode quality          # quality scoring on resume_parsed.json
  python benchmark.py --folder "path/to/dir"  # custom folder
  python benchmark.py --limit 20              # cap file count
"""

import os
import sys
import json
import time
import argparse
import tracemalloc
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Fix Windows console encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add src to path so imports work when run from any directory
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from Main_Resume import (
    extract_text, extract_name, extract_contact_number,
    extract_email_from_resume, extract_gender, extract_address,
    extract_skills_from_resume, load_skills_from_csv,
    RESUME_FOLDER, SKILLS_CSV, OUTPUT_JSON,
    SUPPORTED_EXTENSIONS, natural_file_sort_key,
)
from validation import ResumeValidator

OUTPUT_DIR        = os.path.join(SRC_DIR, 'output')
BENCHMARK_JSON    = os.path.join(OUTPUT_DIR, 'benchmark_report.json')
GROUND_TRUTH_JSON = os.path.join(SRC_DIR, 'ground_truth.json')

SEP  = "=" * 70
SEP2 = "-" * 60


# ======================================================================
#  HELPERS
# ======================================================================
def _get_resume_files(folder, limit=0):
    files = sorted(
        [f for f in os.listdir(folder)
         if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS],
        key=natural_file_sort_key,
    )
    return files[:limit] if limit > 0 else files


def _parse_one(fname, folder, skills_list):
    """Parse a single resume. Returns (record, elapsed_s, peak_mb)."""
    path = os.path.join(folder, fname)
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        text   = extract_text(path)
        name   = extract_name(text)
        phone  = extract_contact_number(text)
        email  = extract_email_from_resume(text)
        gender = extract_gender(text, name=name)
        addr   = extract_address(text)
        skills = extract_skills_from_resume(text, skills_list)
        record = {
            'file': fname, 'name': name, 'contact_number': phone,
            'email': email, 'gender': gender, 'address': addr, 'skills': skills,
        }
    except Exception as exc:
        record = {
            'file': fname, 'error': str(exc), 'name': None,
            'contact_number': None, 'email': None, 'gender': None,
            'address': None, 'skills': [],
        }
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return record, elapsed, peak / 1024 / 1024


# ======================================================================
#  1. PERFORMANCE BENCHMARK
# ======================================================================
def run_performance_benchmark(folder, limit=0, workers=1):
    print("\n" + SEP)
    print("  PERFORMANCE BENCHMARK")
    print(SEP)

    files = _get_resume_files(folder, limit)
    if not files:
        print(f"  [ERROR] No resume files found in: {folder}")
        return {}

    skills_list = load_skills_from_csv(SKILLS_CSV)
    print(f"  Files   : {len(files)}")
    print(f"  Workers : {workers}")
    print(f"  Skills  : {len(skills_list)} loaded\n")

    timings, memories, errors = [], [], []

    if workers <= 1:
        for i, fname in enumerate(files, 1):
            record, elapsed, peak_mb = _parse_one(fname, folder, skills_list)
            timings.append(elapsed)
            memories.append(peak_mb)
            tag = "[OK]" if 'error' not in record else "[ERR]"
            if 'error' in record:
                errors.append(fname)
            print(f"  [{i:>3}/{len(files)}] {tag} {fname:<30} {elapsed:.3f}s  {peak_mb:.1f} MB")
    else:
        results_map = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_parse_one, f, folder, skills_list): f for f in files}
            for fut in as_completed(futures):
                fname = futures[fut]
                record, elapsed, peak_mb = fut.result()
                results_map[fname] = (record, elapsed, peak_mb)
        for i, fname in enumerate(files, 1):
            record, elapsed, peak_mb = results_map[fname]
            timings.append(elapsed)
            memories.append(peak_mb)
            tag = "[OK]" if 'error' not in record else "[ERR]"
            if 'error' in record:
                errors.append(fname)
            print(f"  [{i:>3}/{len(files)}] {tag} {fname:<30} {elapsed:.3f}s  {peak_mb:.1f} MB")

    total_time = sum(timings)
    avg_time   = total_time / len(timings) if timings else 0
    throughput = len(files) / total_time if total_time > 0 else 0

    print(f"\n  {SEP2}")
    print(f"  Total time      : {total_time:.2f}s")
    print(f"  Avg per file    : {avg_time:.3f}s")
    print(f"  Throughput      : {throughput:.1f} files/sec")
    print(f"  Fastest         : {min(timings):.3f}s  ({files[timings.index(min(timings))]})")
    print(f"  Slowest         : {max(timings):.3f}s  ({files[timings.index(max(timings))]})")
    print(f"  Peak memory avg : {sum(memories)/len(memories):.1f} MB")
    print(f"  Peak memory max : {max(memories):.1f} MB")
    print(f"  Errors          : {len(errors)}")

    return {
        'total_files': len(files),
        'total_time_s': round(total_time, 3),
        'avg_time_s': round(avg_time, 3),
        'min_time_s': round(min(timings), 3),
        'max_time_s': round(max(timings), 3),
        'throughput_files_per_sec': round(throughput, 2),
        'avg_memory_mb': round(sum(memories) / len(memories), 1),
        'max_memory_mb': round(max(memories), 1),
        'error_count': len(errors),
        'error_files': errors,
    }


# ======================================================================
#  2. ACCURACY BENCHMARK  (requires ground_truth.json)
# ======================================================================
def _normalize_phone(p):
    import re
    return re.sub(r'\D', '', p or '')

def _normalize_email(e):
    return (e or '').strip().lower()

def _normalize_name(n):
    return ' '.join((n or '').strip().lower().split())

def _skills_match_ratio(extracted, expected):
    if not expected:
        return 1.0
    ext_lower = [s.lower().strip() for s in (extracted or [])]
    matched = sum(
        1 for exp in expected
        if any(exp.lower() in e or e in exp.lower() for e in ext_lower)
    )
    return matched / len(expected)


def run_accuracy_benchmark(folder, ground_truth_path, limit=0):
    print("\n" + SEP)
    print("  ACCURACY BENCHMARK")
    print(SEP)

    if not os.path.exists(ground_truth_path):
        print(f"  [WARN] Ground truth file not found: {ground_truth_path}")
        print("  Creating ground_truth.json template from parser output...")
        _create_ground_truth_template(folder, ground_truth_path, limit)
        print(f"  [OK] Template created at: {ground_truth_path}")
        print("  Edit the file with correct expected values, then re-run.")
        return {}

    with open(ground_truth_path, encoding='utf-8') as f:
        ground_truth = {item['file']: item for item in json.load(f)}

    files = _get_resume_files(folder, limit)
    files = [f for f in files if f in ground_truth]

    if not files:
        print("  [ERROR] No files match ground truth entries.")
        return {}

    skills_list = load_skills_from_csv(SKILLS_CSV)
    print(f"  Files with ground truth: {len(files)}\n")

    field_results = {'name': [], 'email': [], 'phone': [], 'skills': []}
    per_file = []

    for fname in files:
        gt = ground_truth[fname]
        record, _, _ = _parse_one(fname, folder, skills_list)

        name_ok     = _normalize_name(record.get('name'))         == _normalize_name(gt.get('name'))
        email_ok    = _normalize_email(record.get('email'))        == _normalize_email(gt.get('email'))
        phone_ok    = _normalize_phone(record.get('contact_number')) == _normalize_phone(gt.get('contact_number'))
        skill_ratio = _skills_match_ratio(record.get('skills'), gt.get('skills'))
        skills_ok   = skill_ratio >= 0.6

        field_results['name'].append(name_ok)
        field_results['email'].append(email_ok)
        field_results['phone'].append(phone_ok)
        field_results['skills'].append(skills_ok)

        tag = "[OK]" if all([name_ok, email_ok, phone_ok]) else "[!!]"
        print(f"  {tag} {fname:<30}  "
              f"name={'Y' if name_ok else 'N'}  "
              f"email={'Y' if email_ok else 'N'}  "
              f"phone={'Y' if phone_ok else 'N'}  "
              f"skills={skill_ratio*100:.0f}%")

        per_file.append({
            'file': fname,
            'name_correct': name_ok,
            'email_correct': email_ok,
            'phone_correct': phone_ok,
            'skill_match_ratio': round(skill_ratio, 2),
        })

    def pct(lst):
        return round(sum(lst) / len(lst) * 100, 1) if lst else 0

    print(f"\n  {SEP2}")
    print(f"  Name  accuracy : {pct(field_results['name'])}%  ({sum(field_results['name'])}/{len(files)})")
    print(f"  Email accuracy : {pct(field_results['email'])}%  ({sum(field_results['email'])}/{len(files)})")
    print(f"  Phone accuracy : {pct(field_results['phone'])}%  ({sum(field_results['phone'])}/{len(files)})")
    print(f"  Skills >=60%   : {pct(field_results['skills'])}%  ({sum(field_results['skills'])}/{len(files)})")

    overall = pct([
        all([n, e, p]) for n, e, p in
        zip(field_results['name'], field_results['email'], field_results['phone'])
    ])
    print(f"\n  Overall (name+email+phone all correct): {overall}%")

    return {
        'files_tested': len(files),
        'name_accuracy_pct': pct(field_results['name']),
        'email_accuracy_pct': pct(field_results['email']),
        'phone_accuracy_pct': pct(field_results['phone']),
        'skills_60pct_match_pct': pct(field_results['skills']),
        'overall_all_fields_pct': overall,
        'per_file': per_file,
    }


def _create_ground_truth_template(folder, output_path, limit=0):
    """Parse resumes and write a template ground_truth.json for manual correction."""
    files = _get_resume_files(folder, limit or 10)
    skills_list = load_skills_from_csv(SKILLS_CSV)
    template = []
    for fname in files:
        record, _, _ = _parse_one(fname, folder, skills_list)
        template.append({
            'file': fname,
            'name': record.get('name') or '',
            'email': record.get('email') or '',
            'contact_number': record.get('contact_number') or '',
            'skills': record.get('skills', [])[:5],
            '_note': 'Verify and correct these values - they are parser output, not ground truth',
        })
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)


# ======================================================================
#  3. QUALITY BENCHMARK  (uses existing resume_parsed.json)
# ======================================================================
def run_quality_benchmark(parsed_json_path=None):
    print("\n" + SEP)
    print("  QUALITY / VALIDATION BENCHMARK")
    print(SEP)

    path = parsed_json_path or OUTPUT_JSON
    if not os.path.exists(path):
        print(f"  [ERROR] Parsed JSON not found: {path}")
        print("  Run Main_Resume.py first to generate parsed output.")
        return {}

    with open(path, encoding='utf-8') as f:
        results = json.load(f)

    print(f"  Loaded {len(results)} records from: {path}\n")

    validator = ResumeValidator()
    summary   = validator.validate_batch(results)

    dist = summary['quality_distribution']
    pct  = summary['quality_percentage']

    print(f"  Average score   : {summary['average_score']:.1f} / 100")
    print(f"  Score range     : {summary['min_score']:.1f} - {summary['max_score']:.1f}")
    print(f"\n  Quality distribution:")
    print(f"    [EX] Excellent : {dist['excellent']:>4}  ({pct['excellent']:.1f}%)")
    print(f"    [OK] Good      : {dist['good']:>4}  ({pct['good']:.1f}%)")
    print(f"    [!!] Fair      : {dist['fair']:>4}  ({pct['fair']:.1f}%)")
    print(f"    [XX] Poor      : {dist['poor']:>4}  ({pct['poor']:.1f}%)")

    fields       = ['name', 'email', 'phone', 'gender', 'address', 'skills']
    field_labels = {'phone': 'contact_number'}
    print(f"\n  Field extraction rates:")
    field_stats = {}
    for field in fields:
        key       = field_labels.get(field, field)
        found     = sum(1 for r in results if r.get(key) not in (None, '', []))
        pct_found = found / len(results) * 100 if results else 0
        bar       = '#' * int(pct_found / 5) + '.' * (20 - int(pct_found / 5))
        print(f"    {field:<12}: [{bar}]  {found:>3}/{len(results)}  ({pct_found:.1f}%)")
        field_stats[field] = {'found': found, 'total': len(results), 'pct': round(pct_found, 1)}

    validated    = summary['validated_results']
    poor_records = [v for v in validated if v['quality_level'] == 'poor']
    if poor_records:
        print(f"\n  Poor quality records ({len(poor_records)}):")
        for v in poor_records[:10]:
            warnings = '; '.join(v['warnings'][:2])
            print(f"    [XX] {v['file']:<30} score={v['overall_score']:.0f}  {warnings}")

    return {
        'total_records': len(results),
        'average_score': summary['average_score'],
        'min_score': summary['min_score'],
        'max_score': summary['max_score'],
        'quality_distribution': dist,
        'quality_percentage': pct,
        'field_extraction_rates': field_stats,
        'poor_record_count': len(poor_records),
    }


# ======================================================================
#  MAIN
# ======================================================================
def main():
    parser = argparse.ArgumentParser(description='ATS Resume Parser Benchmark')
    parser.add_argument('--mode',    choices=['all', 'perf', 'accuracy', 'quality'], default='all')
    parser.add_argument('--folder',  default=RESUME_FOLDER)
    parser.add_argument('--limit',   type=int, default=0, help='Max files (0=all)')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--ground-truth', default=GROUND_TRUTH_JSON)
    parser.add_argument('--parsed-json',  default=OUTPUT_JSON)
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n{SEP}")
    print(f"  ATS RESUME PARSER - BENCHMARK SUITE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)
    print(f"  Folder  : {args.folder}")
    print(f"  Mode    : {args.mode}")
    print(f"  Limit   : {args.limit or 'all'}")
    print(f"  Workers : {args.workers}")

    report = {'timestamp': datetime.now().isoformat(), 'config': vars(args)}

    if args.mode in ('all', 'perf'):
        report['performance'] = run_performance_benchmark(
            args.folder, args.limit, args.workers
        )

    if args.mode in ('all', 'accuracy'):
        report['accuracy'] = run_accuracy_benchmark(
            args.folder, args.ground_truth, args.limit
        )

    if args.mode in ('all', 'quality'):
        report['quality'] = run_quality_benchmark(args.parsed_json)

    with open(BENCHMARK_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{SEP}")
    print(f"  Benchmark complete")
    print(f"  Report saved -> {BENCHMARK_JSON}")
    print(f"{SEP}\n")


if __name__ == '__main__':
    main()
