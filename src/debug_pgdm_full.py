#!/usr/bin/env python3
"""Debug full PGDM extraction flow."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import extract_education_pdf_doc
from Main_Resume import extract_text

text = extract_text(r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf')

print("=" * 80)
print("Testing extract_education_pdf_doc():")
print("=" * 80)

results = extract_education_pdf_doc(text)

print(f"\nFound {len(results)} education entries:")
for i, edu in enumerate(results, 1):
    print(f"\n[{i}] {edu['qualification']} | {edu['institute_university']} | {edu['passing_year']} | {edu['grade_cgpa']}")
    if edu['specialization_branch']:
        print(f"    └─ Specialization: {edu['specialization_branch']}")

# Also check what's in the first line
print("\n" + "=" * 80)
print("Looking at first 500 chars of text:")
print("=" * 80)
print(text[:500])
