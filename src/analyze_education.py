#!/usr/bin/env python3
"""
Analyze education extraction across all resumes 
and show what formats are being missed
"""

import os
import json
import re
from Main_Resume import extract_text, extract_education, _extract_education_section

test_folder = r"D:\Project\ATS\ATS Email Parser\Qulity HR\Bulk_Resumes_1775101335"

# Get all resume files
resume_files = sorted([f for f in os.listdir(test_folder) if f.endswith(('.pdf', '.docx', '.doc'))])

print(f"\n{'='*80}")
print(f"ANALYZING {len(resume_files)} RESUMES FOR EDUCATION EXTRACTION")
print(f"{'='*80}\n")

stats = {
    'total': len(resume_files),
    'with_education': 0,
    'without_education': 0,
    'failed_to_extract': 0,
}

# Group by result
with_education = []
without_education = []

for i, fname in enumerate(resume_files[:50], 1):  # Check first 50
    fpath = os.path.join(test_folder, fname)
    
    try:
        text = extract_text(fpath)
        education = extract_education(text)
        
        if education:
            stats['with_education'] += 1
            with_education.append({
                'file': fname,
                'count': len(education),
                'entries': education
            })
        else:
            stats['without_education'] += 1
            without_education.append(fname)
            
    except Exception as e:
        stats['failed_to_extract'] += 1
        print(f"[ERR] {i:3d}. ERROR in {fname}: {str(e)[:60]}")

print(f"\n{'='*80}")
print(f"SUMMARY:")
print(f"{'='*80}")
print(f"[OK] With education found: {stats['with_education']}")
print(f"[NO] Without education:    {stats['without_education']}")
print(f"[ERR] Failed to extract:   {stats['failed_to_extract']}")
print(f"\nExtraction rate: {stats['with_education']}/{stats['with_education']+stats['without_education']} = {stats['with_education']*100/(stats['with_education']+stats['without_education'] or 1):.1f}%")

print(f"\n{'='*80}")
print(f"RESUMES WITHOUT EDUCATION FOUND:")
print(f"{'='*80}\n")

for i, fname in enumerate(without_education[:10], 1):
    fpath = os.path.join(test_folder, fname)
    print(f"{i}. {fname}")
    
    try:
        text = extract_text(fpath)
        
        # Check if education section exists in text
        education_headers = [
            'education', 'qualification', 'academic', 'degree', 
            'course', 'university', 'institute', 'college'
        ]
        
        has_education_keyword = False
        education_text = ""
        
        for line in text.splitlines():
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in education_headers):
                has_education_keyword = True
                education_text = line
                break
        
        if has_education_keyword:
            print(f"   [FOUND] Found education keyword: {education_text[:70]}")
            
            # Show next 10 lines after education section
            lines = text.splitlines()
            for j, line in enumerate(lines):
                if any(kw in line.lower() for kw in education_headers):
                    print(f"   Content after education header:")
                    for k in range(j, min(j+8, len(lines))):
                        print(f"      {lines[k][:75]}")
                    break
        else:
            print(f"   [NOT-FOUND] No education keyword found in resume")
            
            # Show first 20 lines to understand structure
            print(f"   First 20 lines:")
            for line in text.splitlines()[:20]:
                if line.strip():
                    print(f"      {line[:75]}")
    
    except Exception as e:
        print(f"   Error: {str(e)[:60]}")
    
    print()

print(f"\n{'='*80}")
print(f"RECOMMENDATION:")
print(f"{'='*80}")
print("""
To improve education extraction:

1. Add the 'without_education' resume files to your test folder
2. Check various education formats in those resumes
3. Share sample resumes with different formats (table, bullet, etc.)
4. We'll enhance the regex patterns to match those formats

Common education formats that might be missing:
- Bullet point lists under "Education" header
- Table format with columns (Exam, Stream, Board, Year, Percentage)
- Inline format (e.g., "B.Com completed in May 2025 from Dr. Babasaheb Ambedkar University")
- Multiple institutions on separate lines
- Education without a clear "Education" header (scattered in resume)
""")

print("="*80)
