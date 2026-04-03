#!/usr/bin/env python3
"""Test education extraction on a sample resume"""

import os
import json
from Main_Resume import extract_text, extract_education

# Test folder
test_folder = r"D:\Project\ATS\ATS Email Parser\Qulity HR\Bulk_Resumes_1775101335"

# Get first 3 PDF files
files = [f for f in os.listdir(test_folder) if f.endswith(('.pdf', '.docx', '.doc'))][:3]

print(f"Testing education extraction on {len(files)} files:\n")

for fname in files:
    fpath = os.path.join(test_folder, fname)
    print(f"\n{'='*70}")
    print(f"File: {fname}")
    print('='*70)
    
    try:
        text = extract_text(fpath)
        education = extract_education(text)
        
        print(f"\nEducation entries found: {len(education)}")
        
        if education:
            for i, edu in enumerate(education, 1):
                print(f"\nEntry {i}:")
                for key, value in edu.items():
                    if value:
                        print(f"  {key}: {value}")
        else:
            print("No education found")
            
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*70)
print("Test complete!")
