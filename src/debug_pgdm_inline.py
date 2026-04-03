#!/usr/bin/env python3
"""Debug PGDM inline extraction"""

from Main_Resume import extract_text, _parse_inline_education_entry
import os
import re

test_folder = r"D:\Project\ATS\ATS Email Parser\Qulity HR\Bulk_Resumes_1775101335"
test_file = "11739739 - Pgdm Aicte Ap.pdf"
fpath = os.path.join(test_folder, test_file)

print(f"Extracting from: {test_file}\n")

text = extract_text(fpath)

# Look for PGDM line
lines = text.splitlines()
pgdm_lines = [i for i, line in enumerate(lines) if 'pgdm' in line.lower()]

print(f"Found {len(pgdm_lines)} lines with 'PGDM':\n")

for idx in pgdm_lines[:5]:
    line = lines[idx]
    print(f"\nLine {idx} (len={len(line)}):")
    print(f"  Content: {line[:150]}...")
    
    # Check education marker
    has_edu_marker = any(marker in line.lower() for marker in [
        'from ', 'at ', 'passing year', 'year', 'board', '%', '–', 
        'university', 'college', 'institute', 'school', 'iti', 'pgdm', 'mba'
    ])
    print(f"  Has education marker: {has_edu_marker}")
    
    # Check length limits
    print(f"  Len > 500 and no marker: {len(line) > 500 and not has_edu_marker}")
    print(f"  Len > 1000: {len(line) > 1000}")
    
    if len(line) <= 1000 and (len(line) <= 500 or has_edu_marker):
        # Try parsing
        result = _parse_inline_education_entry(line)
        print(f"  Parse result: {result}")
