#!/usr/bin/env python3
"""Test the _split_by_degree_patterns method."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor

pgdm_line = "PGDM(AICTE Ap proved), Maharaja Agrasen BusinessSchool(MABS),Delhi,BBA,Guru Gobind Singh Indraprastha University, Delhi,12Th,Central Board of Secondary Education, Delhi, 2024-20262021-20242019-2020(Awaited)(80.3%)(74.5%)"

extractor = EducationExtractor()

print("=" * 80)
print("Testing _split_by_degree_patterns:")
print("=" * 80)

segments = extractor._split_by_degree_patterns(pgdm_line)
print(f"\nFound {len(segments)} segments:")
for i, segment in enumerate(segments):
    print(f"\n[{i}] {segment[:100]}...")
