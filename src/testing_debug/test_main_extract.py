#!/usr/bin/env python3
"""Test Main_Resume.py extract_education with the new integration."""

import sys
sys.path.insert(0, '.')

from Main_Resume import extract_text, extract_education
import json

resume_path = r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11709463 - Prashant Singh.pdf'

print("=" * 80)
print("Testing extract_education() from Main_Resume.py")
print("=" * 80)

text = extract_text(resume_path)
results = extract_education(text)

print(f"\nFound {len(results)} education entries:\n")
for i, edu in enumerate(results):
    print(f"[{i}]")
    for key, value in edu.items():
        if value is not None:
            print(f"  {key:25} : {value}")
    print()

# Also format as JSON to match user's output format
print("\n" + "=" * 80)
print("JSON Format:")
print("=" * 80)
print(json.dumps(results, indent=2))
