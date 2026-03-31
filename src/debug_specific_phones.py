#!/usr/bin/env python3
"""Debug specific phones that should work"""

import re
from Main_Resume import extract_contact_number, _normalize_phone_candidate

test_phones = [
    "+1(940)437-0150",  # From 3_doc.docx - Saiteja
    "+91-8789633232",   # From 5_pdf.pdf - Ajay Kumar
    "8434560687",       # From 5_pdf.pdf - Ajay Kumar
]

print("="*80)
print("TESTING SPECIFIC PHONES FROM RESUMES")
print("="*80 + "\n")

for phone in test_phones:
    print(f"\nPhone: {phone}")
    
    # Test normalization
    normalized = _normalize_phone_candidate(phone)
    print(f"  Normalized: {normalized}")
    
    # Test in context (simulating how it appears in resume)
    if "+1(" in phone:
        context = f"Saiteja\n{phone}\nsaitejaatwork@gmail.com"
    elif "+91-8789" in phone:
        context = f"ajaybhuims@gmail.com\n{phone}/8434560687"
    else:
        context = f"Secondary phone: {phone}"
    
    # Run extraction on the context
    result = extract_contact_number(context)
    print(f"  Extracted from context: {result}")
    
    # Check regex patterns
    PHONE_LABEL_RE = re.compile(r'(?i)\b(?:mobile|mob|phone|ph|contact|tel|telephone|call|whatsapp)\b\s*[:\-]?\s*([+()0-9][0-9()\s.\-/]{6,25})')
    PHONE_GENERIC_RE = re.compile(r'(?<!\w)(?:\+?\d{1,3}[ \t.\-]?)?(?:\(?\d{2,5}\)?[ \t.\-]?)?\d(?:[\d \t()./\-]{5,}\d)(?!\w)')
    
    label_match = PHONE_LABEL_RE.search(phone)
    generic_match = PHONE_GENERIC_RE.search(phone)
    
    print(f"  PHONE_LABEL_RE match: {bool(label_match)}")
    print(f"  PHONE_GENERIC_RE match: {bool(generic_match)}")

print("\n" + "="*80)
