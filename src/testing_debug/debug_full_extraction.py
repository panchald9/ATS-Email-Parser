#!/usr/bin/env python3
"""Debug the full experience extraction pipeline."""

from Main_Resume import extract_text, extract_professional_experience_profile
import json

RESUME_PATH = r"D:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf"

text = extract_text(RESUME_PATH)
experience = extract_professional_experience_profile(text)

print("=" * 80)
print("EXTRACTED PROFESSIONAL EXPERIENCE:")
print("=" * 80)
print(json.dumps(experience, indent=2))

if experience:
    print("\n" + "=" * 80)
    print("ANALYSIS:")
    print("=" * 80)
    for idx, exp in enumerate(experience):
        print(f"\nEntry {idx + 1}:")
        print(f"  Company: {exp.get('company_name')} (should be 'Earnifyy')")
        print(f"  Role: {exp.get('role')}")
        print(f"  Dates: {exp.get('start_date')} - {exp.get('end_date')}")
else:
    print("❌ NO EXPERIENCE EXTRACTED")
