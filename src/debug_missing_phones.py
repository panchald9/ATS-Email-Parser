"""
Debug script to analyze why certain resumes don't have contact numbers extracted.
"""
import os
import re
from Main_Resume import extract_text, extract_contact_number

# Resumes missing contact numbers
missing_phone = ["2_doc.docx", "2_pdf.pdf", "3_pdf.pdf", "5_pdf.pdf", "11_doc.docx"]

resume_folder = r"D:\Project\ATS\ATS Email Parser\Resume"

PHONE_LABEL_RE = re.compile(
    r'(?i)\b(?:mobile|mob|phone|ph|contact|tel|telephone|call|whatsapp)\b\s*[:\-]?\s*([+()0-9][0-9()\s.\-/]{6,25})'
)
PHONE_GENERIC_RE = re.compile(
    r'(?<!\w)(?:\+?\d{1,3}[ \t.\-]?)?(?:\(?\d{2,5}\)?[ \t.\-]?)?\d(?:[\d \t()./\-]{5,}\d)(?!\w)'
)

print("\n" + "="*80)
print("ANALYZING MISSING PHONE NUMBERS IN RESUMES")
print("="*80)

for fname in missing_phone[:3]:  # Check first 3
    fpath = os.path.join(resume_folder, fname)
    if not os.path.exists(fpath):
        print(f"\n❌ {fname}: FILE NOT FOUND")
        continue
    
    print(f"\n{'='*80}")
    print(f"Analyzing: {fname}")
    print(f"{'='*80}")
    
    try:
        text = extract_text(fpath)
        extracted = extract_contact_number(text)
        
        print(f"Extracted phone: {extracted}")
        
        # Search for phone-like patterns manually
        labeled_phones = PHONE_LABEL_RE.findall(text)
        generic_phones = PHONE_GENERIC_RE.findall(text)
        
        print(f"\nManual PHONE_LABEL_RE matches: {labeled_phones[:5]}")
        print(f"Manual PHONE_GENERIC_RE matches: {generic_phones[:5]}")
        
        # Show first 1000 chars to see structure
        print(f"\nFirst 1000 characters:")
        sample = text[:1000]
        # Safely encode/decode to handle unicode
        print(sample.encode('utf-8', errors='replace').decode('utf-8'))
        
    except Exception as e:
        error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
        print(f"Error analyzing: {error_msg}")

print("\n" + "="*80)
