#!/usr/bin/env python3
"""Detailed analysis of remaining missing phones"""

import json
import re
from Main_Resume import extract_text
from pathlib import Path

# Resumes still missing phones
missing_files = ['2_doc.docx', '2_pdf.pdf', '3_doc.docx', '5_pdf.pdf', '7_doc.docx', '11_doc.docx']

PHONE_LABEL_RE = re.compile(
    r'(?i)\b(?:mobile|mob|phone|ph|contact|tel|telephone|call|whatsapp)\b\s*[:\-]?\s*([+()0-9][0-9()\s.\-/]{6,25})'
)

print("\n" + "="*80)
print("DETAILED ANALYSIS OF MISSING PHONE NUMBERS")
print("="*80 + "\n")

for fname in missing_files:
    filepath = Path('../Resume') / fname
    if not filepath.exists():
        print(f"❌ {fname}: FILE NOT FOUND")
        continue
    
    try:
        text = extract_text(str(filepath))
        
        # Check if ANY phone-like pattern exists
        label_matches = PHONE_LABEL_RE.findall(text)
        
        # Look for any digit sequences that might be phone numbers
        digit_sequences = re.findall(r'\b\d{10,12}\b', text)
        phone_patterns = re.findall(r'\+?\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{1,4}', text)
        
        print(f"\n{fname}:")
        print(f"  Labeled phones (mobile:, phone:, etc): {label_matches[:3] if label_matches else 'None'}")
        print(f"  Phone patterns found: {phone_patterns[:3] if phone_patterns else 'None'}")
        print(f"  Long digit sequences (10-12): {digit_sequences[:3] if digit_sequences else 'None'}")
        
        # Sample of text to see structure
        lines = text.split('\n')[:10]
        print(f"  First few lines:")
        for line in lines[:3]:
            if line.strip():
                sample = line.strip()[:70]
                print(f"    {sample}")
        
    except Exception as e:
        print(f"  Error: {str(e)[:100]}")

print("\n" + "="*80)
