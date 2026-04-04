#!/usr/bin/env python3
"""
Test script for enhanced education extraction from PDF/DOC files.
Tests both Parsel-based and traditional extraction methods.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from education_extraction_utils import EducationExtractor, extract_education_pdf_doc
from Main_Resume import extract_education, pdf_extract_text, Document, DOCX_AVAILABLE, PDFMINER_AVAILABLE


def test_education_extraction():
    """Test education extraction from sample text and files."""
    
    print("=" * 70)
    print("EDUCATION EXTRACTION TEST SUITE")
    print("=" * 70)
    
    # Test 1: Simple inline format
    print("\n[Test 1] Simple Inline Education Entry")
    print("-" * 70)
    text1 = """
    B.Tech in Computer Science, from IIT Delhi, 2020, CGPA: 8.5
    M.A. (Physics) - from Delhi University - 85%
    """
    
    results1 = extract_education_pdf_doc(text1)
    print(f"Input: {text1.strip()}")
    print(f"Results: {len(results1)} entries found")
    for r in results1:
        print(f"  - {r['qualification']} from {r['institute_university']} ({r['passing_year']}, {r['grade_cgpa']})")
    
    # Test 2: Section format
    print("\n[Test 2] Structured Education Section")
    print("-" * 70)
    text2 = """
    EDUCATION
    Bachelor of Technology (B.Tech) in Computer Science
    Indian Institute of Technology, Delhi
    Year of Graduation: 2020
    CGPA: 8.5/10
    
    Master of Business Administration (MBA)
    Xavier Labour Relations Institute, Jamshedpur
    Year of Graduation: 2022
    Grade: A
    """
    
    results2 = extract_education_pdf_doc(text2)
    print(f"Input:\n{text2}")
    print(f"\nResults: {len(results2)} entries found")
    for r in results2:
        print(f"  Degree: {r['qualification']}")
        print(f"  University: {r['institute_university']}")
        print(f"  Year: {r['passing_year']}")
        print(f"  Grade: {r['grade_cgpa']}")
        print()
    
    # Test 3: Multiple degrees
    print("\n[Test 3] Multiple Education Entries")
    print("-" * 70)
    text3 = """
    EDUCATION
    10th - State Board, 2010, 78%
    12th - Central Board, 2012, 82%
    B.Sc in Mathematics, Delhi University, 2015, 7.5 CGPA
    M.Sc in Physics, IIT Mumbai, 2017, 8.2 CGPA
    """
    
    results3 = extract_education_pdf_doc(text3)
    print(f"Input:\n{text3}")
    print(f"\nResults: {len(results3)} entries found")
    for i, r in enumerate(results3, 1):
        print(f"  [{i}] {r['qualification']} - {r['institute_university']} ({r['passing_year']}, {r['grade_cgpa']})")
    
    # Test 4: PDF file if available
    if PDFMINER_AVAILABLE:
        print("\n[Test 4] PDF File Extraction")
        print("-" * 70)
        try:
            pdf_files = list(Path(".").glob("*.pdf"))[:1]  # Get first PDF if exists
            if pdf_files:
                pdf_file = pdf_files[0]
                print(f"Testing with: {pdf_file}")
                pdf_text = pdf_extract_text(str(pdf_file))
                results4 = extract_education(pdf_text)
                print(f"Results: {len(results4)} education entries found")
                for r in results4:
                    print(f"  - {r.get('qualification')} from {r.get('institute_university')} ({r.get('passing_year')})")
            else:
                print("No PDF files found in current directory")
        except Exception as e:
            print(f"Error testing PDF: {e}")
    else:
        print("\n[Test 4] PDF File Extraction - SKIPPED (pdfminer not available)")
    
    # Test 5: DOCX file if available
    if DOCX_AVAILABLE:
        print("\n[Test 5] DOCX File Extraction")
        print("-" * 70)
        try:
            docx_files = list(Path(".").glob("*.docx"))[:1]  # Get first DOCX if exists
            if docx_files:
                docx_file = docx_files[0]
                print(f"Testing with: {docx_file}")
                doc = Document(str(docx_file))
                docx_text = '\n'.join([p.text for p in doc.paragraphs])
                results5 = extract_education(docx_text)
                print(f"Results: {len(results5)} education entries found")
                for r in results5:
                    print(f"  - {r.get('qualification')} from {r.get('institute_university')} ({r.get('passing_year')})")
            else:
                print("No DOCX files found in current directory")
        except Exception as e:
            print(f"Error testing DOCX: {e}")
    else:
        print("\n[Test 5] DOCX File Extraction - SKIPPED (python-docx not available)")
    
    # Test 6: Parsel feature check
    print("\n[Test 6] Parsel Feature Check")
    print("-" * 70)
    extractor = EducationExtractor()
    print(f"Parsel available: {extractor.parsel_enabled}")
    if extractor.parsel_enabled:
        print("✓ Parsel-based extraction is enabled")
        print("  Features: Structured text parsing, HTML selector support")
    else:
        print("✗ Parsel not available (fallback to regex extraction)")
    
    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    test_education_extraction()
