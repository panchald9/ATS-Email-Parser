#!/usr/bin/env python3
"""Debug the 5 remaining failing resumes"""

from Main_Resume import extract_text, extract_education, _extract_education_section
import os

test_folder = r"D:\Project\ATS\ATS Email Parser\Qulity HR\Bulk_Resumes_1775101335"

failing_resumes = [
    "11771721 - Ramesh Mishra.pdf",
    "11771939 - Gaurav Patare.pdf",
    "11771945 - Manish Ghode.pdf",
    "11771934 - Vivekanand Vishwakarma.pdf",
    "11771717 - Pradeep Murmu.pdf",
]

for fname in failing_resumes:
    fpath = os.path.join(test_folder, fname)
    
    if not os.path.exists(fpath):
        print(f"\n[SKIP] {fname} not found")
        continue
    
    print(f"\n{'='*80}")
    print(f"FILE: {fname}")
    print(f"{'='*80}")
    
    text = extract_text(fpath)
    
    # Get education section
    section_lines = _extract_education_section(text)
    if section_lines:
        print(f"\n[SECTION FOUND] {len(section_lines)} lines in education section")
        for i, line in enumerate(section_lines[:10]):
            print(f"  {i}: {line[:100]}")
    else:
        print(f"\n[NO SECTION] Education section not found")
        # Show first 30 lines to see what's there
        lines = text.splitlines()[:30]
        print(f"First 30 lines:")
        for i, line in enumerate(lines):
            print(f"  {i}: {line[:100]}")
    
    # TRY EXTRACTION
    education = extract_education(text)
    print(f"\n[EXTRACTED] {len(education)} entries found")
    for i, entry in enumerate(education, 1):
        print(f"  {i}: {entry['qualification']} from {entry['institute_university']}")
