#!/usr/bin/env python3
"""Debug table extraction from resume."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor
from Main_Resume import extract_text

# Extract text
text = extract_text(r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11709463 - Prashant Singh.pdf')

# Find education section
extractor = EducationExtractor()
section_text, found = extractor.extract_education_section_text(text)

print("=" * 80)
print("EDUCATION SECTION TEXT (first 500 chars):")
print("=" * 80)
print(section_text[:500] if section_text else "Not found")

if section_text:
    lines = [line.strip() for line in section_text.split('\n')]
    
    print("\n" + "=" * 80)
    print("LINES EXTRACTED:")
    print("=" * 80)
    for i, line in enumerate(lines[:30]):
        print(f"[{i:2d}] {repr(line[:70])}")
    
    print("\n" + "=" * 80)
    print("TABLE ROWS EXTRACTED:")
    print("=" * 80)
    rows = extractor._extract_table_rows(lines)
    for i, row in enumerate(rows):
        print(f"\nRow {i}:")
        for j, cell in enumerate(row):
            print(f"  Cell [{j}]: {repr(cell[:80])}")
