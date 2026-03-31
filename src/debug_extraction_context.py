#!/usr/bin/env python3
"""Debug why +91 phone not extracted from context"""

import re
from Main_Resume import normalize_compact_text, PHONE_GENERIC_RE, _normalize_phone_candidate

# The actual text from 5_pdf.pdf
context = """ajaybhuims@gmail.com
+91-8789633232/8434560687"""

print("="*80)
print("TESTING EXTRACTION CONTEXT")
print("="*80)
print(f"Input context:\n{repr(context)}\n")

# Step 1: Normalize
normalized_text = normalize_compact_text(context).replace('\r', '\n')
print(f"After normalize_compact_text:\n{repr(normalized_text)}\n")

# Step 2: Split into segments
segments = [seg.strip() for seg in re.split(r'[\n|]+', normalized_text) if seg and seg.strip()]
if not segments:
    segments = [normalized_text]

print(f"Segments: {segments}\n")

# Step 3: Search for generic phones
candidates = []
for seg_idx, seg in enumerate(segments):
    print(f"Checking segment {seg_idx}: {seg}")
    
    for m in PHONE_GENERIC_RE.finditer(seg):
        raw = m.group(0)
        print(f"  Found match: {raw}")
        
        number = _normalize_phone_candidate(raw)
        print(f"  Normalized: {number}")
        
        if not number:
            print(f"  -> Skipped (normalization returned None)")
            continue
        
        digits_len = len(re.sub(r'\D', '', number))
        print(f"  Digits length: {digits_len}")
        
        if digits_len < 10:
            print(f"  -> Skipped (too few digits: {digits_len} < 10)")
            continue
        
        # Calculate score
        ctx = seg[max(0, m.start()-35):min(len(seg), m.end()+35)].lower()
        score = 1
        print(f"  Context around match: {repr(ctx[:70])}")
        
        if re.search(r'\b(phone|mobile|mob|contact|call|tel|telephone|whatsapp)\b', ctx):
            score += 3
            print(f"    +3 for phone label")
        if re.search(r'\b(fax|pin|pincode|zip|dob|date|year|salary|ctc)\b', ctx):
            score -= 3
            print(f"    -3 for non-phone label")
        if number.startswith('+'):
            score += 1
            print(f"    +1 for + prefix")
        if digits_len >= 10:
            score += 1
            print(f"    +1 for digits >= 10")
        
        len_pref = 0 if 10 <= digits_len <= 12 else (1 if digits_len == 13 else 2)
        print(f"  Score: {score}, Length pref: {len_pref}, Digits: {digits_len}")
        
        candidates.append((score, len_pref, digits_len, seg_idx, m.start(), number))
        print(f"  -> Added to candidates")
    print()

print(f"Total candidates: {len(candidates)}")
if candidates:
    candidates.sort(key=lambda x: (-x[0], x[1], -x[2], x[3], x[4]))
    print(f"Sorted candidates:")
    for i, (score, len_pref, digits_len, seg_idx, start, number) in enumerate(candidates):
        print(f"  {i}. Score={score}, Len_pref={len_pref}, Digits={digits_len}, Number={number}")
    print(f"\nSelected (highest score): {candidates[0][5]}")
else:
    print("No candidates found!")

print("\n" + "="*80)
