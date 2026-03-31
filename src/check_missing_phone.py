#!/usr/bin/env python3
"""Check which resumes are missing contact numbers"""

import json

with open('output/resume_parsed.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

missing = [(d['file'], d.get('name', 'N/A')) for d in data if d.get('contact_number') is None]

print(f"\n=== CONTACT NUMBERS ANALYSIS ===\n")
print(f"Total resumes: {len(data)}")
print(f"Missing phones: {len(missing)}")
print(f"Success rate: {(len(data) - len(missing)) / len(data) * 100:.1f}%\n")

if missing:
    print("Resumes without contact numbers:")
    for i, (fname, name) in enumerate(missing, 1):
        print(f"  {i}. {fname:20} - {name}")
else:
    print("✓ All resumes have contact numbers extracted!")

print()
