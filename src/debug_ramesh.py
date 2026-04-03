#!/usr/bin/env python3
"""Debug Ramesh Mishra specifically"""

from Main_Resume import extract_text
import os

test_folder = r"D:\Project\ATS\ATS Email Parser\Qulity HR\Bulk_Resumes_1775101335"
fpath = os.path.join(test_folder, "11771721 - Ramesh Mishra.pdf")

text = extract_text(fpath)
lines = text.splitlines()

print(f"Total lines: {len(lines)}\n")

# Find lines with education keywords
print("Lines with M.A., B.A., HSC, or SSC keywords:")
for i, line in enumerate(lines):
    if any(kw in line.lower() for kw in ['m.a.', 'm.a ', 'b.a.', 'b.a ', 'hsc', 'ssc', 'kanpur', 'purvanchal']):
        print(f"  Line {i}: {line[:120]}")

# Show lines 30-80 where education might be
print("\n\nLines 30-80 (looking for education):")
for i in range(30, min(80, len(lines))):
    print(f"  {i}: {lines[i][:100]}")
