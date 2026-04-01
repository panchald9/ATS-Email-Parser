import sys
sys.path.insert(0,'.')
from Main_Resume import extract_text, extract_name, _infer_gender_from_name, _infer_gender_from_text_context, extract_gender
import os

folder = r'D:\Project\ATS\ATS Email Parser\Testing Resume'
cases = ['18_doc.docx','175_doc.docx','174_doc.docx','16_pdf.pdf','177_doc.docx','169_doc.docx','171_doc.docx']

print(f"{'File':<20} {'Name':<25} {'Name->G':<8} {'Text->G':<8} {'Final':<8}")
print("-" * 80)

for fname in cases:
    path = os.path.join(folder, fname)
    try:
        text = extract_text(path)
        name = extract_name(text)
        gn = _infer_gender_from_name(name)
        gt = _infer_gender_from_text_context(text)
        gf = extract_gender(text, name=name)
        print(f"{fname:<20} {str(name):<25} {str(gn):<8} {str(gt):<8} {str(gf):<8}")
    except Exception as e:
        print(f"{fname:<20} ERROR: {e}")
