#!/usr/bin/env python3
"""Test enhanced education extraction on actual resumes."""

import sys
sys.path.insert(0, '.')

from education_extraction_utils import extract_education_pdf_doc
from Main_Resume import extract_text

resumes = [
    (r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11709463 - Prashant Singh.pdf', 'Prashant Singh - TABLE FORMAT'),
    (r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11725204 - Sp.pdf', 'SP - Prajapati - FREE-FORM FORMAT'),
    (r'd:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050\11739739 - Pgdm Aicte Ap.pdf', 'Mayank Kumar - PGDM'),
]

for resume_path, name in resumes:
    print("=" * 80)
    print(f"Testing: {name}")
    print("=" * 80)
    
    try:
        text = extract_text(resume_path)
        results = extract_education_pdf_doc(text)
        
        if results:
            print(f"\nFound {len(results)} education entries:\n")
            for i, edu in enumerate(results, 1):
                qual = edu['qualification'] or 'N/A'
                univ = edu['institute_university'] or 'N/A'
                year = edu['passing_year'] or 'N/A'
                grade = edu['grade_cgpa'] or 'N/A'
                spec = edu['specialization_branch'] or 'N/A'
                
                print(f"[{i}] {qual:15} | {univ:35} | {year:6} | {grade:8}")
                if edu['specialization_branch']:
                    print(f"    └─ Specialization: {spec}")
        else:
            print("No education entries found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
