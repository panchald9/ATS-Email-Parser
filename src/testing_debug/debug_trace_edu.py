#!/usr/bin/env python3
"""Detailed trace of PGDM extraction flow."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor
from Main_Resume import extract_text

text = extract_text(r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf')

extractor = EducationExtractor()
results = []
seen = set()

print("=" * 80)
print("STRATEGY 1: Section-based extraction")
print("=" * 80)

section_text, found_header = extractor.extract_education_section_text(text)
print(f"Section found: {section_text is not None}, Header found: {found_header}")

print("\n" + "=" * 80)
print("STRATEGY 3: Line-by-line fallback")
print("=" * 80)

if not results:
    lines = text.split('\n')
    print(f"Processing {len(lines)} lines...")
    
    for i, line in enumerate(lines[:3]):
        line_stripped = line.strip()
        has_deg = extractor.has_degree(line_stripped)
        will_skip = (not line_stripped) or (len(line_stripped) > 300 and not has_deg)
        print(f"\nLine {i}: len={len(line_stripped)}, has_degree={has_deg}, skip={will_skip}")
        
        if not will_skip and has_deg:
            print(f"  Processing this line...")
            segments = extractor._split_by_degree_patterns(line_stripped)
            print(f"  Found {len(segments)} segments")
            
            for j, seg in enumerate(segments[:3]):
                res = extractor.parse_education_entry(seg)
                print(f"    [{j}] qual={res['qualification']}, univ={res['institute_university']}, year={res['passing_year']}")
                if res['qualification']:
                    results.append(res)

print(f"\n\nTotal entries found: {len(results)}")
