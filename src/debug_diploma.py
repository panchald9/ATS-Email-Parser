#!/usr/bin/env python3
"""Debug script to trace Diploma extraction issue."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor

extractor = EducationExtractor()

# Simplified test case
text = """EDUCATION

Diploma in Information Technology
Government Polytechnic College
2013-2016
Percentage: 82%

ITI in Electrician
Government Institute
2011"""

print("Input text:")
print(text)
print("\n" + "="*70)

# Step 1: Extract section
section_text, found = extractor.extract_education_section_text(text)
print(f"Section found: {found}")
print(f"Section text:\n{section_text}")

print("\n" + "="*70)

# Step 2: Split education entries
if section_text:
    entries = extractor._split_education_entries(section_text)
    print(f"Split into {len(entries)} entries:")
    for i, entry in enumerate(entries, 1):
        print(f"\nEntry {i}:\n{entry}")
    
    print("\n" + "="*70)
    
    # Step 3: Parse each entry
    print("Parsing each entry:")
    for i, entry in enumerate(entries, 1):
        parsed = extractor.parse_education_entry(entry)
        print(f"\nEntry {i} parsed:")
        print(f"  Qualification: {parsed['qualification']}")
        print(f"  Year: {parsed['passing_year']}")
        print(f"  Institute: {parsed['institute_university']}")
        print(f"  Grade: {parsed['grade_cgpa']}")

print("\n" + "="*70)

# Check has_degree
print("has_degree checks:")
print(f"  'Diploma in Information Technology': {extractor.has_degree('Diploma in Information Technology')}")
print(f"  'Government Polytechnic College': {extractor.has_degree('Government Polytechnic College')}")
print(f"  '2013-2016': {extractor.has_degree('2013-2016')}")
