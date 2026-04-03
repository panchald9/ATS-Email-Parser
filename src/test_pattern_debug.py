#!/usr/bin/env python3
"""Debug pattern matching on Ramesh lines"""

import re

line = "M.A. (Political Science ) - from Kanpur University – 52%"

# Pattern 1 from Main_Resume.py
pattern1 = re.search(
    r'(s\.?s\.?c|ssc|hsc|12th?|10th?|b\.?(?:tech|sc|a|com|e)|m\.?(?:tech|sc|a|com|e)|diploma|iti|pgdm|mba|phd|llb|llm)'
    r'[,\s]*\(?([^)]*)\)?\s*'
    r'(?:in|from|of|at)?\s*'
    r'(\d{4})?\s*'
    r'(?:from|at)?\s*'
    r'([A-Z][A-Za-z\s&\.]*?)?\s*'
    r'(?:with|:|-)?\s*'
    r'(\d+\.?\d*%?)?',
    line, re.I
)

print(f"Line: {line}")
print(f"Pattern 1 match: {bool(pattern1)}")
if pattern1:
    print(f"  Groups: {pattern1.groups()}\n")

# Try a simpler pattern for M.A
simpler = re.search(r'\b(m\.?a|m\.a\.)\b', line, re.I)
print(f"Simpler M.A pattern: {bool(simpler)}")
if simpler:
    print(f"  Matched: {simpler.group(0)}\n")

# Try searching just for the qualification part
qual_search = re.search(r'\b(m\.?a\.?|b\.?a\.?|m\.?sc|b\.?sc)\b', line, re.I)
print(f"Qual search: {bool(qual_search)}")
if qual_search:
    print(f"  Matched: {qual_search.group(0)}\n")

# Check what the issue is with the full pattern
if not pattern1:
    print("\nTrying parts of pattern1:")
    
    # Just the qualification part
    qual_part = r'(s\.?s\.?c|ssc|hsc|12th?|10th?|b\.?(?:tech|sc|a|com|e)|m\.?(?:tech|sc|a|com|e)|diploma|iti|pgdm|mba|phd|llb|llm)'
    qual_match = re.search(qual_part, line, re.I)
    print(f"  Qual part matches: {bool(qual_match)}")
    if qual_match:
        print(f"    Matched: '{qual_match.group(0)}' at position {qual_match.span()}")
