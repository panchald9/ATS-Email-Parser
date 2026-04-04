import sys, re
sys.path.insert(0,'.')
from Main_Resume import extract_text, normalize_compact_text
import os

folder = r'D:\Project\ATS\ATS Email Parser\Testing Resume'
text = extract_text(os.path.join(folder, '175_doc.docx'))
t = normalize_compact_text(text).lower()

# Show all ms. matches with context
ms_matches = re.findall(r'.{0,30}ms\.?.{0,30}', t)
print(f"Total ms matches: {len(ms_matches)}")
for m in ms_matches[:20]:
    print(f"  {repr(m)}")
