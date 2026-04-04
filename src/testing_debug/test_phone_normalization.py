#!/usr/bin/env python3
"""Test phone normalization function"""

import re
from Main_Resume import _normalize_phone_candidate, PHONE_GENERIC_RE

# Test the phone from Dhruv Panchal's resume
test_phone = "+91-9601945583"

print("="*80)
print(f"Testing phone: {test_phone}")
print("="*80)

# Step 1: Does PHONE_GENERIC_RE match?
match = PHONE_GENERIC_RE.search(test_phone)
print(f"1. PHONE_GENERIC_RE matches: {bool(match)}")
if match:
    print(f"   Match group: {match.group(0)}")

# Step 2: Does normalize function work?
normalized = _normalize_phone_candidate(test_phone)
print(f"2. After _normalize_phone_candidate(): {normalized}")

# Step 3: Debug the normalization process
print("\n3. Debug normalization process:")
raw = test_phone
print(f"   Input: {raw}")

# Remove extensions
cleaned = re.sub(r'(?i)(?:ext\.?|x|extension)\s*\d{1,6}\b', '', raw).strip()
print(f"   After extension removal: {cleaned}")

digits = re.sub(r'\D', '', cleaned)
print(f"   Digits only: {digits} (length={len(digits)})")

# Check validations
print(f"\n4. Validation checks:")
print(f"   7 <= len(digits) <= 15? {7 <= len(digits) <= 15} (actual len={len(digits)})")
print(f"   Starts with +? {cleaned.startswith('+')}")
print(f"   If no +, len(digits) <= 12? {not cleaned.startswith('+') and len(digits) <= 12}")
print(f"   len(set(digits)) == 1? {len(set(digits)) == 1} (unique digits: {set(digits)})")
year_pattern = r'^(19|20)\d{2}$'
looks_like_year = bool(re.match(year_pattern, digits))
print(f"   Looks like year (19XX or 20XX)? {looks_like_year}")

year_hits = re.findall(r'(?:19|20)\d{2}', digits)
print(f"   Year-like patterns found: {year_hits}")
print(f"   >= 2 years found? {len(year_hits) >= 2}")
print(f"   len=12, starts with 0, has year? {len(digits) == 12 and digits.startswith('0') and year_hits}")

print("\n5. Final result:")
print(f"   {normalized}")
