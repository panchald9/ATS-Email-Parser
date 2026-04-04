#!/usr/bin/env python3
"""Debug PGDM extraction."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor
from Main_Resume import extract_text

# Extract text
text = extract_text(r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf')

print("=" * 80)
print("TEXT PREVIEW (first 2000 chars):")
print("=" * 80)
print(text[:2000])

print("\n" + "=" * 80)
print("SEARCHING FOR EDUCATION SECTION:")
print("=" * 80)

extractor = EducationExtractor()
section_text, found_header = extractor.extract_education_section_text(text)

if section_text:
    print(f"Found education section (header found: {found_header})")
    print(f"\nEducation section text (first 500 chars):")
    print(section_text[:500])
    
    # Try table extraction
    lines = [line.strip() for line in section_text.split('\n')]
    print(f"\n\nLines in section ({len(lines)} lines):")
    for i, line in enumerate(lines[:30]):
        print(f"[{i:2d}] {repr(line[:70])}")
    
    # Try table row extraction
    rows = extractor._extract_table_rows(lines)
    print(f"\n\nTable rows extracted: {len(rows)}")
    for i, row in enumerate(rows):
        print(f"\nRow {i} ({len(row)} cells):")
        for j, cell in enumerate(row[:5]):
            print(f"  Cell[{j}]: {repr(cell[:50])}")
else:
    print("No education section found")
    print("\nSearching for PGDM keyword in text:")
    if "pgdm" in text.lower():
        idx = text.lower().find("pgdm")
        print(f"Found at position {idx}")
        print(f"Context: {text[max(0, idx-100):idx+200]}")
    else:
        print("PGDM keyword not found in text")
