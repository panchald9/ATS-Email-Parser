import sys, re
sys.path.insert(0,'.')
from Main_Resume import extract_text, extract_name, normalize_compact_text
import os

folder = r'D:\Project\ATS\ATS Email Parser\Testing Resume'
cases = ['18_doc.docx','175_doc.docx','174_doc.docx','169_doc.docx','171_doc.docx']

for fname in cases:
    path = os.path.join(folder, fname)
    text = extract_text(path)
    name = extract_name(text)
    t = normalize_compact_text(text).lower()
    head = t[:3500]

    male_titles   = len(re.findall(r'\b(?:mr\.?|mister|sir|shri|shree)\b', t)) * 2
    female_titles = len(re.findall(r'\b(?:mrs\.?|ms\.?|miss|madam|smt|kumari)\b', t)) * 2
    male_pron     = len(re.findall(r'\b(?:he|him|his)\b', head))
    female_pron   = len(re.findall(r'\b(?:she|her|hers)\b', head))

    # Show actual pronoun matches
    she_matches = re.findall(r'.{0,20}\bshe\b.{0,20}', head)
    her_matches = re.findall(r'.{0,20}\bher\b.{0,20}', head)
    he_matches  = re.findall(r'.{0,20}\bhe\b.{0,20}', head)

    print(f"\n--- {fname} | name={name} ---")
    print(f"  male_titles={male_titles}, female_titles={female_titles}")
    print(f"  he/him/his={male_pron}, she/her/hers={female_pron}")
    if she_matches:
        print(f"  'she' contexts: {she_matches[:3]}")
    if her_matches:
        print(f"  'her' contexts: {her_matches[:3]}")
    if he_matches:
        print(f"  'he' contexts:  {he_matches[:3]}")
