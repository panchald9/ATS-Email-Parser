#!/usr/bin/env python3
"""Check what causes the job context skip."""

import sys
sys.path.insert(0, '.')

from Main_Resume import extract_text

resume_path = r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf'
text = extract_text(resume_path)

lines = text.split('\n')
line = lines[0].strip()

print("First line contains:")
print(line[:200])
print("...")
print(line[-200:])

print(f"\n\nSearching for skip keywords:")
skip_keywords = ['requirement', 'prefer', 'responsible', 'manage',
                 'develop', 'design', 'work', 'years of experience', 'have experience']

line_lower = line.lower()
for keyword in skip_keywords:
    if keyword in line_lower:
        print(f"  Found '{keyword}': YES")
        pos = line_lower.find(keyword)
        print(f"    Context: ...{line[max(0,pos-30):pos+30]}...")
    else:
        print(f"  Found '{keyword}': NO")
