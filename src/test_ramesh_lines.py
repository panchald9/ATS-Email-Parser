#!/usr/bin/env python3
"""Test if Ramesh education lines can be parsed"""

from Main_Resume import _parse_inline_education_entry

test_lines = [
    "M.A. (Political Science ) - from Kanpur University – 52%",
    "BA – (Political Science /Sociology) – Purvanchal University – 51%",
    "HSC: - Passed with science stream from Subhash Inter Collage UP Board – 60%",
    "SSC :- passed from MRD Govt HSS Jokahara Azamgarh, UP Board – 65%",
]

print("Testing Ramesh education lines:\n")

for line in test_lines:
    print(f"Line: {line}")
    
    # Check markers
    has_edu_marker = any(marker in line.lower() for marker in [
        'from ', 'at ', 'passing year', 'year', 'board', '%', '–', 
        'university', 'college', 'institute', 'school', 'iti', 'pgdm', 'mba'
    ])
    print(f"  Has edu marker: {has_edu_marker}")
    
    # Check skip words
    skip_words = ['email', 'phone', 'mobile', 'whatsapp', 'address', 'job', 'role', 'experience']
    has_skip = any(skip in line.lower() for skip in skip_words)
    print(f"  Has skip word: {has_skip}")
    
    # Parse
    result = _parse_inline_education_entry(line)
    print(f"  Parsed: {result}")
    print()
