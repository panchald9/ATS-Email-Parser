#!/usr/bin/env python3
"""Check line lengths and strategy flow."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor
from Main_Resume import extract_text

text = extract_text(r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf')

extractor = EducationExtractor()

print("=" * 80)
print("Checking line lengths:")
print("=" * 80)

lines = text.split('\n')
for i, line in enumerate(lines[:15]):
    line_stripped = line.strip()
    has_degree = extractor.has_degree(line_stripped)
    print(f"[{i:2d}] len={len(line_stripped):4d} has_degree={has_degree} | {line_stripped[:80]}...")
    if i > 5:
        print("...")
        break

# Check specifically if the education line would be processed
edu_line = lines[0]
print(f"\n\nFirst line details:")
print(f"Length: {len(edu_line)}")
print(f"Has degree: {extractor.has_degree(edu_line)}")
print(f"Would skip (len > 300)? {len(edu_line) > 300}")
print(f"Content: {edu_line[:200]}...")

# Test segment splitting
if extractor.has_degree(edu_line):
    segments = extractor._split_by_degree_patterns(edu_line.strip())
    print(f"\nSegments found: {len(segments)}")
    for j, seg in enumerate(segments):
        result = extractor.parse_education_entry(seg)
        print(f"  Segment {j}: qual={result['qualification']} univ={result['institute_university']}")
