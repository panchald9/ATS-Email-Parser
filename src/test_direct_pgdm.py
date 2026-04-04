#!/usr/bin/env python3
"""Direct test of extract_education_pdf_doc for PGDM."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import EducationExtractor
from Main_Resume import extract_text

resume_path = r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf'

text = extract_text(resume_path)

# Manually call extract_all_education like extract_education_pdf_doc does
extractor = EducationExtractor()
results = extractor.extract_all_education(text)

print(f"Results: {len(results)} entries")
for result in results:
    print(f"  {result['qualification']} - {result['institute_university']}")
