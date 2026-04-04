#!/usr/bin/env python3
"""Test inline education extraction on PGDM line"""

from Main_Resume import extract_text, _parse_inline_education_entry
import os
import re

# Test the specific line
test_line = "PGDM(AICTE Ap proved), Maharaja Agrasen BusinessSchool(MABS),Delhi,BBA,Guru Gobind Singh University"

print(f"Testing line: {test_line}\n")

# Test Pattern 1 to see what it matches
pattern1 = re.search(
    r'(s\.?s\.?c|ssc|hsc|12th?|10th?|b\.?(?:tech|sc|a|com|e)|m\.?(?:tech|sc|a|com|e)|diploma|iti|pgdm|mba|phd|llb|llm)'
    r'[,\s]*\(?([^)]*)\)?\s*'
    r'(?:in|from|of|at)?\s*'
    r'(\d{4})?\s*'
    r'(?:from|at)?\s*'
    r'([A-Z][A-Za-z\s&\.]*?)?\s*'
    r'(?:with|:|-)?\s*'
    r'(\d+\.?\d*%?)?',
    test_line, re.I
)

print(f"Pattern 1 match: {bool(pattern1)}")
if pattern1:
    print(f"  Group 1 (qual): '{pattern1.group(1)}'")
    print(f"  Group 2 (spec): '{pattern1.group(2)}'")
    print(f"  Group 3 (year): '{pattern1.group(3)}'")
    print(f"  Group 4 (univ): '{pattern1.group(4)}'")
    print(f"  Group 5 (grade): '{pattern1.group(5) }'\n")

result = _parse_inline_education_entry(test_line)

print(f"Result: {result}\n")

if result:
    for key, value in result.items():
        if value:
            print(f"  {key}: {value}")
