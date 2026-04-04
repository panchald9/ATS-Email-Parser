#!/usr/bin/env python3
"""Debug B.Tech grade extraction."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor
from Main_Resume import extract_text

# Extract text
text = extract_text(r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11709463 - Prashant Singh.pdf')

# Find education section
extractor = EducationExtractor()
section_text, found = extractor.extract_education_section_text(text)

if section_text:
    lines = [line.strip() for line in section_text.split('\n')]
    rows = extractor._extract_table_rows(lines)
    
    if rows:
        print("=" * 80)
        print("Debugging B.Tech Row (Row 0):")
        print("=" * 80)
        
        row = rows[0]
        print(f"\nRow cells ({len(row)} cells):")
        for i, cell in enumerate(row):
            print(f"  [{i}]: {repr(cell)}")
        
        print(f"\nCombined text: {repr(' '.join(row))}")
        
        # Test extraction methods
        combined = ' '.join(row)
        print(f"\nExtraction test:")
        print(f"  Degree: {extractor.extract_degree(combined)}")
        print(f"  Year: {extractor.extract_year(combined)}")
        print(f"  Grade: {extractor.extract_grade(combined)}")
        print(f"  University: {extractor.extract_university(combined)}")
        
        # Parse the row
        parsed = extractor._parse_table_row(row)
        print(f"\nParsed result:")
        for key, value in parsed.items():
            print(f"  {key}: {repr(value)}")
