#!/usr/bin/env python3
"""Test company name extraction for pipe-delimited format."""

import re
from Main_Resume import (
    _parse_inline_experience_header,
    _looks_like_role,
    _looks_like_company,
    ROLE_HINT_RE,
    COMPANY_HINT_RE,
)

# The problematic line from the resume
test_line = "Operation Executive Operation & Strategy Planner |Earnifyy (Styflowne Finance Services Pvt. Ltd.) Jan 2023 – jun2024"

print(f"Testing line: {test_line}\n")

# Test inline header parsing
print("=" * 80)
print("TESTING _parse_inline_experience_header():")
print("=" * 80)
result = _parse_inline_experience_header(test_line)
if result:
    print(f"SUCCESS!")
    print(f"  Company: {result.get('company')}")
    print(f"  Role: {result.get('role')}")
    print(f"  Location: {result.get('location')}")
    print(f"  Date Range: {result.get('date_range')}")
else:
    print("FAILED - returned None")

# Debug: Test pipe splitting manually
print("\n" + "=" * 80)
print("DEBUG: MANUAL PIPE SPLITTING:")
print("=" * 80)
pieces = [p.strip() for p in test_line.split('|') if p.strip()]
print(f"Pieces ({len(pieces)}):")
for idx, piece in enumerate(pieces):
    print(f"  [{idx}] {piece}")
    print(f"      _looks_like_role: {_looks_like_role(piece)}")
    print(f"      _looks_like_company: {_looks_like_company(piece)}")
    print(f"      ROLE_HINT_RE match: {bool(ROLE_HINT_RE.search(piece))}")
    print(f"      COMPANY_HINT_RE match: {bool(COMPANY_HINT_RE.search(piece))}")
