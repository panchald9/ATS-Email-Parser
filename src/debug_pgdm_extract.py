#!/usr/bin/env python3
"""Debug PGDM file extraction"""

from Main_Resume import extract_text, extract_education, _extract_education_section
import os

test_folder = r"D:\Project\ATS\ATS Email Parser\Qulity HR\Bulk_Resumes_1775101335"
test_file = "11739739 - Pgdm Aicte Ap.pdf"
fpath = os.path.join(test_folder, test_file)

print(f"Extracting from: {test_file}\n")

text = extract_text(fpath)

# Strategy 1: get education section
print("="*80)
print("STRATEGY 1: Extract Education Section")
print("="*80)

section_lines = _extract_education_section(text)
if section_lines:
    print(f"Found {len(section_lines)} lines in education section:")
    for i, line in enumerate(section_lines[:10]):
        print(f"  {i}: {line[:100]}")
else:
    print("No education section found")

# Full extraction
print("\n" + "="*80)
print("FULL EDUCATION EXTRACTION")
print("="*80)

education = extract_education(text)
print(f"Found {len(education)} education entries:\n")

for i, entry in enumerate(education, 1):
    print(f"Entry {i}:")
    for key, value in entry.items():
        if value:
            print(f"  {key}: {value}")
    print()
