#!/usr/bin/env python3
"""Debug extract_all_education flow with instrumentation."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor
from Main_Resume import extract_text

resume_path = r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf'
text = extract_text(resume_path)

extractor = EducationExtractor()
results = []
seen = set()

print("=" * 80)
print("Manually executing extract_all_education logic with debugging")
print("=" * 80)

# Strategy 1
print("\nSTRATEGY 1: Section-based extraction")
section_text, found_header = extractor.extract_education_section_text(text)
print(f"  section_text found: {section_text is not None}")
print(f"  Results after Strategy 1: {len(results)}")

if len(results) >= 1:
    print("  -> Early return (Strategy 1 has results)")
else:
    print("  -> Continuing to Strategy 2")

# Strategy 2
print("\nSTRATEGY 2: Parsel extraction")
print(f"  parsel_enabled: {extractor.parsel_enabled}")
print(f"  results is empty: {not results}")

if extractor.parsel_enabled and not results:
    try:
        parsel_lines = extractor.extract_with_parsel(text)
        print(f"  Parsel returned {len(parsel_lines)} lines")
        for line in parsel_lines[:3]:
            print(f"    - {line[:80]}...")
            parsed = extractor.parse_education_entry(line)
            if parsed['qualification']:
                key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
                if key not in seen:
                    seen.add(key)
                    results.append(parsed)
                    print(f"      Added: {parsed['qualification']}")
    except Exception as e:
        print(f"  Exception in Parsel: {e}")
        import traceback
        traceback.print_exc()

print(f"  Results after Strategy 2: {len(results)}")

if len(results) >= 1:
    print("  -> Early return (Strategy 2 has results)")
else:
    print("  -> Continuing to Strategy 3")

# Strategy 3
print("\nSTRATEGY 3: Fallback line-by-line search")
if not results:
    lines = text.split('\n')
    print(f"  Processing {len(lines)} lines")
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # Skip long lines unless they have degrees
        if len(line) > 300 and not extractor.has_degree(line):
            continue
        
        if extractor.has_degree(line):
            print(f"  Line {i} has degree (len={len(line)})")
            
            # Skip experience context
            if any(skip in line.lower() for skip in
                   ['requirement', 'prefer', 'responsible', 'manage',
                    'develop', 'design', 'work', 'years of experience', 'have experience']):
                print(f"    -> Skipped (job context)")
                continue
            
            segments = extractor._split_by_degree_patterns(line)
            print(f"    Found {len(segments)} segments")
            
            if len(segments) > 1:
                for j, segment in enumerate(segments):
                    parsed = extractor.parse_education_entry(segment)
                    if parsed['qualification']:
                        key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
                        if key not in seen:
                            seen.add(key)
                            results.append(parsed)
                            print(f"      Added segment {j}: {parsed['qualification']}")
            else:
                parsed = extractor.parse_education_entry(line)
                if parsed['qualification']:
                    key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
                    if key not in seen:
                        seen.add(key)
                        results.append(parsed)
                        print(f"      Added: {parsed['qualification']}")

print(f"\n  Results after Strategy 3: {len(results)}")
print(f"\nFinal results: {len(results)} entries")
for r in results:
    print(f"  - {r['qualification']} | {r['institute_university']}")
