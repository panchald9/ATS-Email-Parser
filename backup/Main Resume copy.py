import re
import os
from pdfminer.high_level import extract_text

# Optional libs
try:
    from names_dataset import NameDataset
    nd = NameDataset()
    DATASET_AVAILABLE = True
except:
    nd = None
    DATASET_AVAILABLE = False

try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    SPACY_AVAILABLE = True
except:
    nlp = None
    SPACY_AVAILABLE = False


# ── BLACKLIST ─────────────────────────────────────────────────
BLACKLIST = {
    'gate','road','street','nagar','colony','flat','floor','block','near','post',
    'dist','area','city','town','village','sector','plot','phase','tehsil','taluka',
    'apartment','society','building','chowk','lane','bypass','main','cross','vill',
    'falia','kevdi','shantiniketan','dabhel','charntungi','daltungi','lalpur',
    'police','station','varachha',
    'india','gujarat','maharashtra','rajasthan','punjab','bihar','kerala','odisha',
    'haryana','uttar','pradesh','mumbai','delhi','pune','surat','ahmedabad','vapi',
    'silvassa','daman','nashik','bangalore','prayagraj','jamnagar','vadodara','bundi',
    'pratapgarh','goa','karnataka','hyderabad','chennai','kolkata','morbi',
    'resume','curriculum','vitae','objective','profile','summary','education',
    'experience','skills','contact','languages','training','declaration','reference',
    'strength','project','certificate','qualification','achievement','interest',
    'personal','details','information','career','academic','professional','technical',
    'computer','work','employment','internship','key','hobbies','strengths',
    'background','academics','overview','history',
    'troubleshooting','reporting','teamwork','leadership','communication','management',
    'thinking','planning','analysis','marketing','expertise','critical','effective',
    'strategic','analytical','logical','functional','implementation','hardworking',
    'quick','diligence','adaptable','learner','conversant','sincere','punctual',
    'engineer','manager','assistant','executive','analyst','developer','consultant',
    'intern','director','officer','coordinator','specialist','associate','supervisor',
    'receptionist','senior','junior','lead','trainee','operator','reliability',
    'date','birth','gender','male','female','marital','status','married','unmarried',
    'nationality','religion','father','mother','mobile','email','phone','board',
    'university','college','institute','school','class','percentage','grade',
    'hereby','declare','january','february','march','april','june','july',
    'august','september','october','november','december',
    'maintain','accounting','accounts','payable','receivable','statement','outlook',
    'diploma','degree','passing','course','bachelor','master','student',
    'thanks','regards','yours','faithfully','sincerely','place','signed',
    'permanent','address','detail','maintenance','projects','major',
    'engineering','chemical','mechanical','electrical','quality','control',
    'production','safety','health','requirement','specification','company',
    'sarthana','sap','hana','formerly','known',
}

SKIP_LINES = {
    'resume','curriculum','vitae','cv','objective','contact','profile',
    'education','skills','experience','summary','reliability','key',
    'hobbies','strengths','background','academics','of','j','',
    'overview','history','work','personal','information','city','country',
}

# Section-heading words found right AFTER a name in a blob
SECTION_WORDS = re.compile(
    r'\b(WORK|EDUCATION|PROFILE|CONTACT|SKILLS|LANGUAGES|EXPERIENCE|'
    r'TRAINING|DECLARATION|OBJECTIVE|SUMMARY|PROJECTS|REFERENCE)\b'
)


# ── Helpers ───────────────────────────────────────────────────
def normalize_caps(line):
    words = line.split()
    if words and all(w.isupper() for w in words if w.isalpha()):
        return title_case(line.lower())
    return line


def title_case(s):
    return ' '.join(w.capitalize() for w in s.split())

def is_spaced(line):
    tokens = line.split()
    if not tokens: return True
    return sum(1 for t in tokens if len(t) <= 2) / len(tokens) > 0.5

def title_case(s):
    # Also capitalize single initial: "vishwanath m pagare" → "Vishwanath M Pagare"
    return ' '.join(w.capitalize() for w in s.split())

def looks_like_address(line):
    if re.search(r'\d', line): return True
    return sum(1 for w in line.lower().split() if w.strip('.,') in BLACKLIST) >= 2

def is_valid(name):
    if not name: return False
    name = re.sub(r'\s+', ' ', name).strip()
    words = name.split()
    if not (2 <= len(words) <= 5):              return False
    if any(ch.isdigit() for ch in name):        return False
    if re.search(r'[^A-Za-z\s\-\.\']', name):  return False
    for w in words:
        alpha = re.sub(r'[^A-Za-z]', '', w)
        if not alpha: continue
        if not alpha[0].isupper():              return False
        if len(alpha) < 2:                      return False
    if any(w.lower().strip('.,') in BLACKLIST for w in words): return False
    if any(w.isupper() and len(w) > 3 for w in words):        return False
    return True

def dataset_ok(name, min_score=2):
    if not DATASET_AVAILABLE: return True
    score = 0
    for i, word in enumerate(name.strip().split()):
        clean = re.sub(r'[^A-Za-z]', '', word)
        if len(clean) < 2: continue
        try:
            r = nd.search(clean)
            if i == 0:
                score += 3 if r.get('first_name') else (1 if r.get('last_name') else 0)
            else:
                score += 2 if r.get('last_name') else (1 if r.get('first_name') else 0)
        except Exception:
            pass
    return score >= min_score

def accept(name, strict=True):
    if not is_valid(name): return False
    if strict and DATASET_AVAILABLE: return dataset_ok(name)
    return True


# ── Main extractor ────────────────────────────────────────────
def extract_name(text):
    raw = [l.strip() for l in text.split('\n') if l.strip()]
    if not raw: return None

    # ── EC1: Whole resume on one line (1.pdf) ─────────────────
    # Find 2-3 ALL-CAPS words JUST BEFORE a section heading
    if raw and len(raw[0]) > 150:
        blob = raw[0]
        # e.g. "...English HindiSAURABH SINGH WORK EXPERIENCE..."
        m = re.search(r'([A-Z][A-Z]+(?:\s+[A-Z][A-Z]+){1,3})\s+(?:' + SECTION_WORDS.pattern + r')', blob)
        if m:
            titled = m.group(1).title()
            if is_valid(titled): return titled
        # Fallback: any 2-cap-word sequence
        for cap in re.finditer(r'\b([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})?)\b', blob):
            t = cap.group(1).title()
            if accept(t, strict=False): return t

    # ── EC2: Lowercase last name ("Manish mishra", "Altamash khan") ──
    for line in raw[:6]:
        if re.match(r'^[A-Z][a-z]+(?:\s+[a-zA-Z][a-z]+){1,3}$', line.strip()):
            t = title_case(line.strip())
            if accept(t, strict=False): return t

    norm = [normalize_caps(l) for l in raw]
    full = '\n'.join(norm)

    # ── EC3: "Resume of" then name on next line (22.pdf) ──────
    for i, line in enumerate(norm[:5]):
        if re.match(r'^resume\s+of\s*$', line, re.I):
            if i + 1 < len(norm):
                c = re.sub(r'\s+', ' ', norm[i+1]).strip()
                if accept(c, strict=False): return c
        m = re.match(r'^resume\s+of\s+(.+)$', line, re.I)
        if m:
            c = re.sub(r'\s+', ' ', m.group(1)).strip()
            if accept(c, strict=False): return c

    # ── S0: "Name: XYZ" label ──────────────────────────────────
    m = re.search(r'(?i)(?:full\s+)?name\s*[:\-]\s*([A-Z][A-Za-z\.\-\' ]{3,45})', full)
    if m:
        c = re.sub(r'\s+', ' ', m.group(1).split('\n')[0]).strip()
        if accept(c): return c

    # ── S1: spaCy PERSON ───────────────────────────────────────
    if SPACY_AVAILABLE:
        doc = nlp(full[:600])
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                c = re.sub(r'\s+', ' ', ent.text.strip())
                if accept(c): return c

    # ── S2: Line-by-line scan (first 20 lines) ────────────────
    for i, line in enumerate(norm[:20]):
        if is_spaced(line):                             continue
        if len(line) <= 1:                              continue   # EC6: skip 'J', 'CV'
        if line.lower().strip('.,- ') in SKIP_LINES:   continue
        if re.search(r'[@#\|<>{}]', line):             continue

        # EC4: camelCase split
        spaced = split_camel(line)
        if spaced != line:
            c = re.sub(r'\s+', ' ', spaced).strip()
            if accept(c): return c

        # EC8: If THIS line is already a valid name → return immediately (don't combine)
        clean = re.sub(r'\s+', ' ', line).strip()
        if re.match(r'^[A-Za-z][A-Za-z\s\.\-\']{2,45}$', clean):
            if accept(clean): return clean

        # EC5: Combine with next line (only if next line is NOT an address)
        if i + 1 < len(norm):
            nxt = norm[i + 1]
            if (len(nxt) > 1                                    # EC6: skip 'J'
                    and not is_spaced(nxt)
                    and nxt.lower().strip() not in SKIP_LINES
                    and not looks_like_address(nxt)
                    and not re.search(r'[@#\|<>{}0-9]', nxt)
                    and len(nxt.split()) <= 3):
                combined = re.sub(r'\s+', ' ', line + ' ' + nxt).strip()
                if re.match(r'^[A-Za-z][A-Za-z\s\.\-\']{3,55}$', combined):
                    if accept(combined): return combined

    # ── EC7: Multi-column — name buried deeper (26.pdf) ───────
    for line in norm[15:55]:
        if is_spaced(line) or len(line) <= 1: continue
        if line.lower().strip() in SKIP_LINES: continue
        clean = re.sub(r'\s+', ' ', line).strip()
        if re.match(r'^[A-Za-z][A-Za-z\s\.\-\']{2,35}$', clean):
            if accept(clean): return clean

    # ── Pre-contact text ───────────────────────────────────────
    pre = re.split(r'[\w.\-+]+@[\w.\-]+\.\w+|\b\d{10}\b|\+91[\s\-]?\d', full)[0]
    for c in re.findall(r'\b([A-Z][a-z]+(?: [A-Z][a-z]+){1,4})\b', pre):
        c = re.sub(r'\s+', ' ', c).strip()
        if accept(c): return c

    # ── EC9: Signature footer "Thanks & Regards, name" (15.pdf) ─
    m = re.search(
        r'(?i)(?:thanks|regards|sincerely|faithfully)[,\.\s]+([A-Za-z][a-zA-Z \.]{4,45})',
        full
    )
    if m:
        c = title_case(re.sub(r'\s+', ' ', m.group(1)).strip())
        # Remove common trailing words
        c = re.sub(r'\s*(pvt|ltd|inc|llp|co)\.?\s*$', '', c, flags=re.I).strip()
        if accept(c, strict=False): return c

    # ── Loose full-text scan ───────────────────────────────────
    for c in re.findall(r'\b([A-Z][a-z]+(?: [A-Z][a-z]+){1,4})\b', full[:1500]):
        c = re.sub(r'\s+', ' ', c).strip()
        if is_valid(c): return c

    return None


# ── Batch runner ──────────────────────────────────────────────
if __name__ == '__main__':
    FOLDER = r"D:\Ktas Project\ATS\ATS Email Parser\Resume"
    pdf_files = sorted([f for f in os.listdir(FOLDER) if f.lower().endswith('.pdf')])
    if not pdf_files:
        print("❌ No PDF files found in:", FOLDER)
    else:
        print(f"\nFound {len(pdf_files)} resume(s)\n")
        print(f"{'#':<4} {'File':<44} {'Extracted Name'}")
        print("─" * 72)
        for i, f in enumerate(pdf_files, 1):
            path = os.path.join(FOLDER, f)
            try:
                name = extract_name(extract_text(path))
                print(f"  {i:<3} {f:<44} {name or '❌ NOT FOUND'}")
            except Exception as e:
                print(f"  {i:<3} {f:<44} ⚠️  Error: {e}")
        print("─" * 72)
        print("✅ Done.\n")