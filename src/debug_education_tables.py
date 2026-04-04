#!/usr/bin/env python3
"""Debug education extraction from resumes."""

import sys
sys.path.insert(0, '.')

from Main_Resume import extract_text

print("=" * 80)
print("RESUME 1: Prashant Singh - Education Section in Detail")
print("=" * 80)

text1 = extract_text(r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11709463 - Prashant Singh.pdf')
lines1 = text1.split('\n')

# Find education section
edu_start = -1
for i, line in enumerate(lines1):
    if 'education' in line.lower():
        edu_start = i
        break

if edu_start >= 0:
    print("\nEducation section (lines 28-60):")
    for i in range(edu_start, min(edu_start + 32, len(lines1))):
        line = lines1[i]
        print(f"  [{i:2d}] {repr(line[:100])}")

print("\n" + "=" * 80)
print("RESUME 2: SP - Check structure")
print("=" * 80)

text2 = extract_text(r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11725204 - Sp.pdf')
print("\nFirst 1500 characters:")
print(text2[:1500])

# Look for education-like keywords
keywords = ['10th', '12th', 'b.tech', 'b.sc', 'diploma', 'master', 'degree', 'university', 'college', 'school']
print("\nSearching for education keywords:")
for keyword in keywords:
    if keyword.lower() in text2.lower():
        print(f"  ✓ Found: {keyword}")
        # Find and print context
        idx = text2.lower().find(keyword.lower())
        context = text2[max(0, idx-50):min(len(text2), idx+100)]
        print(f"    Context: {repr(context)}")
