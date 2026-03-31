#!/usr/bin/env python3
"""Debug +1 phone normalization"""

import re

def _normalize_phone_candidate_debug(raw):
    if not raw:
        return None

    print(f"\n    DEBUG: {raw}")
    
    cleaned = re.sub(r'(?i)(?:ext\.?|x|extension)\s*\d{1,6}\b', '', raw).strip()
    print(f"    After extension removal: {cleaned}")
    
    digits = re.sub(r'\D', '', cleaned)
    print(f"    Digits only: {digits} (length={len(digits)})")

    if not (7 <= len(digits) <= 15):
        print(f"    ✗ FAIL: Digit length {len(digits)} not in range 7-15")
        return None
    print(f"    ✓ Digit length OK")
    
    if not cleaned.startswith('+') and len(digits) > 12:
        print(f"    ✗ FAIL: No + prefix and {len(digits)} > 12")
        return None
    print(f"    ✓ Prefix/length OK")
    
    if len(set(digits)) == 1:
        print(f"    ✗ FAIL: All digits same")
        return None
    print(f"    ✓ Digit variety OK")
    
    if re.match(r'^(19|20)\d{2}$', digits):
        print(f"    ✗ FAIL: Looks like year (19XX or 20XX)")
        return None
    print(f"    ✓ Not a year")

    # Check for suspicious year patterns at START
    if re.match(r'^19\d{2}[0-9]{6,}$|^20\d{2}[0-9]{6,}$', digits):
        print(f"    ✗ FAIL: Looks like YYYY + digits")
        return None
    print(f"    ✓ Not YYYY+digits pattern")
    
    # Only reject if there's a 12-digit number starting with 0 AND contains year
    if len(digits) == 12 and digits.startswith('0'):
        year_hits = re.findall(r'(?:19|20)\d{2}', digits)
        if year_hits:
            print(f"    ✗ FAIL: 12-digit starting with 0 and has year patterns")
            return None
    print(f"    ✓ All checks passed")

    result = f'+{digits}' if cleaned.startswith('+') else digits
    print(f"    RESULT: {result}")
    return result

# Test US phone
print("="*80)
print("US PHONE: +1(940)437-0150")
print("="*80)
result = _normalize_phone_candidate_debug("+1(940)437-0150")
print(f"\nFinal: {result}")
