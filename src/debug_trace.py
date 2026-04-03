#!/usr/bin/env python3
"""Trace through the full extraction pipeline with debug output."""

from Main_Resume import (
    extract_text,
    normalize_compact_text,
    _extract_experience_section_lines,
    _normalize_experience_section_lines,
    extract_professional_experience_profile,
)

RESUME_PATH = r"D:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf"

text = extract_text(RESUME_PATH)

print("=" * 80)
print("STEP 1: EXTRACT EXPERIENCE SECTION LINES")
print("=" * 80)
section_lines = _extract_experience_section_lines(text)
print(f"Found {len(section_lines)} lines:")
for idx, line in enumerate(section_lines[:20]):
    print(f"  [{idx}] {line}")

print("\n" + "=" * 80)
print("STEP 2: FULL PROFESSIONAL EXPERIENCE EXTRACTION")
print("=" * 80)
experience = extract_professional_experience_profile(text)
print(f"Found {len(experience)} experience entries")

if experience:
    for idx, exp in enumerate(experience[:3]):
        print(f"\nEntry {idx + 1}:")
        print(f"  Company: {exp.get('company_name')}")
        print(f"  Role: {exp.get('role')}")
        print(f"  Start: {exp.get('start_date')}, End: {exp.get('end_date')}")
        print(f"  Tech: {exp.get('technologies', [])}")
