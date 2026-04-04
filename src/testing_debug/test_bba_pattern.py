#!/usr/bin/env python3
"""Check if BBA matches the pattern."""

import sys
sys.path.insert(0, '.')

import re
from education_extraction_utils import EducationExtractor

pgdm_line = "PGDM(AICTE Ap proved), Maharaja Agrasen BusinessSchool(MABS),Delhi,BBA,Guru Gobind Singh Indraprastha University, Delhi,12Th,Central Board of Secondary Education, Delhi, 2024-20262021-20242019-2020(Awaited)(80.3%)(74.5%)"

extractor = EducationExtractor()

print("Checking BBA pattern...")
bba_pattern = None
for pattern, degree_name in extractor.DEGREE_PATTERNS:
    if degree_name == 'BBA':
        bba_pattern = pattern
        break

if bba_pattern:
    print(f"BBA Pattern: {bba_pattern}")
    match = re.search(bba_pattern, pgdm_line, re.I)
    if match:
        print(f"Match found at position {match.start()}-{match.end()}: '{match.group()}'")
        print(f"Context: ...{pgdm_line[max(0,match.start()-20):match.end()+20]}...")
    else:
        print("No match found in the line")
        print(f"\nSearching for just 'BBA':")
        if 'BBA' in pgdm_line:
            pos = pgdm_line.find('BBA')
            print(f"Found 'BBA' at position {pos}: '{pgdm_line[pos-10:pos+20]}'")
else:
    print("BBA degree pattern not found")
