#!/usr/bin/env python3
"""Debug Pattern 3 regex matching"""

import re

# Test line from Pgdm Aicte Ap.pdf
test_line = "PGDM(AICTE Ap proved), Maharaja Agrasen BusinessSchool(MABS),Delhi,BBA,Guru Gobind Singh University"

print(f"Test line: {test_line}\n")

# Pattern 1: "SSC in 2016 from GSEB with 51%"
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
    print(f"  Groups: {pattern1.groups()}\n")

# Pattern 3 (OLD): "PGDM(AICTE Approved), Maharaja Agrasen BusinessSchool(MABS), Delhi, BBA, Guru Gobind Singh University"
pattern3_old = re.search(
    r'(pgdm|mba|b\.?(?:tech|sc|a|com)|m\.?(?:tech|sc|a|com))'
    r'\s*\(([^)]*)\)?\s*,\s*'
    r'([A-Z][A-Za-z\s&\.,-]*?)\s*(?:\(([^)]+)\))?',
    test_line, re.I
)

print(f"Pattern 3 OLD match: {bool(pattern3_old)}")
if pattern3_old:
    print(f"  Groups: {pattern3_old.groups()}\n")

# Pattern 3 (NEW): With better university capture
pattern3_new = re.search(
    r'(pgdm|mba|b\.?(?:tech|sc|a|com)|m\.?(?:tech|sc|a|com))'
    r'\s*\(([^)]*)\)?\s*,\s*'
    r'([A-Z][A-Za-z\s&\.,-]*?)(?:\s*\([^)]*\))?(?:,|[A-Z]|$)',
    test_line, re.I
)

print(f"Pattern 3 NEW match: {bool(pattern3_new)}")
if pattern3_new:
    print(f"  Groups: {pattern3_new.groups()}\n")

# Pattern 3 (BETTER): Greedy capture up to comma or parenthesis
pattern3_better = re.search(
    r'(pgdm|mba|b\.?(?:tech|sc|a|com)|m\.?(?:tech|sc|a|com))'
    r'\s*\(([^)]*)\)?\s*,\s*'
    r'([A-Z][A-Za-z\s&\.\,-]+)',
    test_line, re.I
)

print(f"Pattern 3 BETTER match: {bool(pattern3_better)}")
if pattern3_better:
    print(f"  Groups: {pattern3_better.groups()}\n")

# Pattern 3 (GREEDY): Very greedy capture
pattern3_greedy = re.search(
    r'(pgdm|mba|b\.?(?:tech|sc|a|com)|m\.?(?:tech|sc|a|com))'
    r'\s*\(([^)]*)\)?\s*,\s*'
    r'([^,\n]+?)(?:\s*\([^)]*\))?(?:,|$)',
    test_line, re.I
)

print(f"Pattern 3 GREEDY match: {bool(pattern3_greedy)}")
if pattern3_greedy:
    print(f"  Groups: {pattern3_greedy.groups()}\n")

# Try without comma requirement first
pattern3_debug = re.search(
    r'(pgdm|mba|b\.?(?:tech|sc|a|com)|m\.?(?:tech|sc|a|com))',
    test_line, re.I
)

print(f"Pattern 3 PGDM match: {bool(pattern3_debug)}")
if pattern3_debug:
    print(f"  Found: {pattern3_debug.group(1)}")
    print(f"  Position: {pattern3_debug.span()}\n")
