#!/usr/bin/env python3
"""Debug education extraction"""

import os
import re
import sys
from Main_Resume import extract_text, _extract_education_section, EDUCATION_SECTION_RE

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Test folder
test_folder = r"D:\Project\ATS\ATS Email Parser\Qulity HR\Bulk_Resumes_1775101335"

# Get first file
files = [f for f in os.listdir(test_folder) if f.endswith(('.pdf', '.docx', '.doc'))][:1]

for fname in files:
    fpath = os.path.join(test_folder, fname)
    print(f"File: {fname}\n")
    
    try:
        text = extract_text(fpath)
        
        # Look for education section headers
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        
        print(f"Total lines: {len(lines)}\n")
        print("Looking for education section headers...")
        print(f"Pattern matches:\n")
        
        for i, line in enumerate(lines[:50]):
            if EDUCATION_SECTION_RE.match(line):
                print(f"✓ Found at line {i}: {repr(line)}")
                print(f"  Next 5 lines:")
                for j in range(i+1, min(i+6, len(lines))):
                    print(f"    {j}: {repr(lines[j])}")
                break
        else:
            print("✗ No education section header found in first 50 lines")
            print("\nFirst 30 lines (checking for pattern matches):")
            for i, line in enumerate(lines[:30]):
                is_match = "✓ MATCH" if EDUCATION_SECTION_RE.match(line) else "  "
                print(f"  {i:2d} {is_match}: {repr(line[:60])}")
        
        # Try section extraction anyway
        section_lines = _extract_education_section(text)
        print(f"\n\nExtracted section lines: {len(section_lines)}")
        if section_lines:
            print("Section content (first 10 lines):")
            for i, line in enumerate(section_lines[:10]):
                print(f"  {i}: {repr(line[:70])}")
                
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

