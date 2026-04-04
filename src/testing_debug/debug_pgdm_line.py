#!/usr/bin/env python3
"""Debug PGDM education entry parsing."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor

# The education line from PGDM resume
pgdm_line = "PGDM(AICTE Ap proved), Maharaja Agrasen BusinessSchool(MABS),Delhi,BBA,Guru Gobind Singh Indraprastha University, Delhi,12Th,Central Board of Secondary Education, Delhi, 2024-20262021-20242019-2020(Awaited)(80.3%)(74.5%)"

extractor = EducationExtractor()

print("=" * 80)
print("Analyzing PGDM education line:")
print("=" * 80)
print(f"Line: {pgdm_line[:100]}...")
print(f"\nLength: {len(pgdm_line)}")

# Check if it has a degree
has_degree = extractor.has_degree(pgdm_line)
print(f"\nhas_degree(): {has_degree}")

# Try to parse
if has_degree:
    print("\n" + "=" * 80)
    print("Attempting to parse as single education entry:")
    print("=" * 80)
    
    result = extractor.parse_education_entry(pgdm_line)
    print(f"\nParsed result:")
    for key, value in result.items():
        if value:
            print(f"  {key}: {repr(value)}")

# Try to split into separate entries
print("\n" + "=" * 80)
print("Trying to detect individual degrees in the line:")
print("=" * 80)

for pattern, degree_name in extractor.DEGREE_PATTERNS:
    import re
    matches = re.finditer(pattern, pgdm_line, re.I)
    for match in matches:
        print(f"Found {degree_name:15} at position {match.start():3d}: ...{pgdm_line[max(0,match.start()-10):match.end()+20]}...")
