#!/usr/bin/env python3
"""Debug regex patterns for Diploma."""

import re

# Test the diploma pattern
pattern = r'\bdiplomaed?\b'
test_strings = [
    'Diploma in Information Technology',
    'diploma',
    'DIPLOMA',
    'Diploma',
]

print("Testing pattern:", pattern)
for text in test_strings:
    match = re.search(pattern, text, re.I)
    print(f"  '{text}' → {bool(match)}")

print()

# Test in context of all patterns
from education_extraction_utils import EducationExtractor

extractor = EducationExtractor()
for pattern, degree_name in extractor.DEGREE_PATTERNS:
    test_text = 'Diploma in Information Technology'
    if re.search(pattern, test_text, re.I):
        print(f"MATCHED: Pattern '{pattern}' with degree '{degree_name}'")

print("\nTesting extract_degree() method:")
result = extractor.extract_degree('Diploma in Information Technology')
print(f"extract_degree('Diploma in Information Technology') = {result}")

print("\nTesting has_degree() method:")
result = extractor.has_degree('Diploma in Information Technology')
print(f"has_degree('Diploma in Information Technology') = {result}")
