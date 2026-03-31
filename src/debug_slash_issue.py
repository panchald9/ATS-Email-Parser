#!/usr/bin/env python3
"""Debug why the combined number fails"""

import re
from Main_Resume import _normalize_phone_candidate

# The regex match includes the SLASH
test_input = "+91-8789633232/8434560687"

print(f"Input: {test_input}")

# Simulate what happens
cleaned = re.sub(r'(?i)(?:ext\.?|x|extension)\s*\d{1,6}\b', '', test_input).strip()
digits = re.sub(r'\D', '', cleaned)

print(f"Cleaned: {cleaned}")
print(f"Digits: {digits}")
print(f"Length: {len(digits)}")

# Check each constraint
print(f"\n7 <= len(digits) <= 15? {7 <= len(digits) <= 15}")
print(f"Cleaned starts with +? {cleaned.startswith('+')}")
print(f"No + and len > 12? {not cleaned.startswith('+') and len(digits) > 12}")

# Test normalization
result = _normalize_phone_candidate(test_input)
print(f"\nNormalized result: {result}")

# The issue is len(digits) = 20, which is > 15
print(f"\nProblem: Digit length {len(digits)} exceeds max of 15")
print("Solution: PHONE_GENERIC_RE matches too greedily across the slash separator")
