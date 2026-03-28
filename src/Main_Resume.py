"""
Resume Parser
=============
Extracts: Name, Contact Number, Email, Gender, Address, Skills
Supports: PDF, DOCX, DOC

Skills are loaded from:  Skill.csv  (column: 'skill')
Output saved to:         output/resume_parsed.json

Optional speed-ups (install if available):
  pip install spacy && python -m spacy download en_core_web_sm
  pip install names-dataset
  pip install textract   # for legacy .doc files
"""

import re
import os
import csv
import json
import importlib

# ── Core deps ──────────────────────────────────────────────────
from pdfminer.high_level import extract_text as pdf_extract_text

try:
    _docx_module = importlib.import_module('docx')
    Document = _docx_module.Document
    DOCX_AVAILABLE = True
except ImportError:
    Document = None
    DOCX_AVAILABLE = False

try:
    textract = importlib.import_module('textract')
    TEXTRACT_AVAILABLE = True
except ImportError:
    textract = None
    TEXTRACT_AVAILABLE = False

# ── Optional NLP libs ──────────────────────────────────────────
try:
    from names_dataset import NameDataset
    nd = NameDataset()
    DATASET_AVAILABLE = True
except Exception:
    nd = None
    DATASET_AVAILABLE = False

try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    SPACY_AVAILABLE = True
except Exception:
    nlp = None
    SPACY_AVAILABLE = False


# ══════════════════════════════════════════════════════════════
#  CONFIGURATION  –  edit these paths before running
# ══════════════════════════════════════════════════════════════
RESUME_FOLDER  = r"D:\Ktas Project\ATS\ATS Email Parser\Resume"
SKILLS_CSV     = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Skill.csv')
OUTPUT_JSON    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'resume_parsed.json')
VALIDATION_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'validation_report.json')
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

# Logging & Error Handling
ENABLE_VALIDATION = True  # Enable accuracy validation
ENABLE_DETAILED_LOGGING = True  # Log extraction details
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'parser.log')


# ══════════════════════════════════════════════════════════════
#  BLACKLISTS & CONSTANTS
# ══════════════════════════════════════════════════════════════
BLACKLIST = {
    # address / geography
    'gate','road','street','nagar','colony','flat','floor','block','near','post',
    'dist','area','city','town','village','sector','plot','phase','tehsil','taluka',
    'apartment','society','building','chowk','lane','bypass','main','cross','will',
    'falia','kevdi','shantiniketan','dabhel','charntungi','daltungi','lalpur',
    'police','station','varachha',
    'india','gujarat','maharashtra','rajasthan','punjab','bihar','kerala','odisha',
    'haryana','uttar','pradesh','mumbai','delhi','pune','surat','ahmedabad','vapi',
    'silvassa','daman','nashik','bangalore','prayagraj','jamnagar','vadodara','bundi',
    'pratapgarh','goa','karnataka','hyderabad','chennai','kolkata','morbi',
    # resume sections
    'resume','curriculum','vitae','objective','profile','summary','education',
    'experience','skills','contact','languages','training','declaration','reference',
    'strength','project','certificate','qualification','achievement','interest',
    'personal','details','information','career','academic','professional','technical',
    'computer','work','employment','internship','key','hobbies','strengths',
    'background','academics','overview','history',
    # generic descriptors
    'troubleshooting','reporting','teamwork','leadership','communication','management',
    'thinking','planning','analysis','marketing','expertise','critical','effective',
    'strategic','analytical','logical','functional','implementation','hardworking',
    'quick','diligence','adaptable','learner','conversant','sincere','punctual',
    # job titles
    'engineer','manager','assistant','executive','analyst','developer','consultant',
    'intern','director','officer','coordinator','specialist','associate','supervisor',
    'receptionist','senior','junior','lead','trainee','operator','reliability',
    # personal info labels
    'date','birth','gender','male','female','marital','status','married','unmarried',
    'nationality','religion','father','mother','mobile','email','phone','board',
    'university','college','institute','school','class','percentage','grade',
    # sign-off / declaration words
    'hereby','declare','january','february','march','april','june','july',
    'august','september','october','november','december',
    # accounting / tool names
    'maintain','accounting','accounts','payable','receivable','statement','outlook',
    'diploma','degree','passing','course','bachelor','master','student',
    'thanks','regards','yours','faithfully','sincerely','place','signed',
    'permanent','address','detail','maintenance','projects','major',
    'engineering','chemical','mechanical','electrical','quality','control',
    'production','safety','health','requirement','specification','company',
    'sarthana','sap','hana','formerly','known',
    'cv','team','global','job','responsibilities','responsibility','output',
    'maintaining','excellent','while','submitted','request','educational',
    'qualifications','microsoft','word','power','point','excel','tally',
    'prime','basics','data','entry','related','basic','knowledge',
}

SKIP_LINES = {
    'resume','curriculum','vitae','cv','objective','contact','profile',
    'education','skills','experience','summary','reliability','key',
    'hobbies','strengths','background','academics','of','j','',
    'overview','history','work','personal','information','city','country',
}

SECTION_WORDS = re.compile(
    r'\b(WORK|EDUCATION|PROFILE|CONTACT|SKILLS|LANGUAGES|EXPERIENCE|'
    r'TRAINING|DECLARATION|OBJECTIVE|SUMMARY|PROJECTS|REFERENCE)\b'
)

BAD_CONTEXT_RE = re.compile(
    r'(?i)\b('
    r'objective|experience|education|skill|summary|profile|declaration|hobbies|'
    r'qualification|qualifications|project|projects|responsib\w*|course|board|'
    r'year|marks|percentage|position|period|role|designation|contact|address|'
    r'school|college|university|institute|manager|engineer|executive|assistant|'
    r'operator|officer|company|curriculum|vitae'
    r')\b'
)

COMPANY_HINTS = {
    'pvt','ltd','limited','llp','inc','corp','private','industries',
    'university','college','school','institute','vidyalaya','society',
    'apartment','apt','road','nagar','colony','park',
}

COMMON_SURNAMES = {
    'kumar','singh','patel','yadav','khan','sharma','gupta','verma',
    'pal','tandel','desai','patil','vasava','jogal',
}

NON_NAME_WORDS = {
    'team','global','job','responsibilities','responsibility','output',
    'maintaining','excellent','while','hile','submitted','request',
    'achievements','core','competencies','competency','citizen','citizenship',
    'styrene','acryl','acrylonitrile',
    'previous','employers','then','call','me','cisco','finance',
}

COMMON_MALE_FIRST_NAMES = {
    'aarav','abhishek','aditya','ajay','akash','alok','amit','anil','ankit','arjun',
    'ashish','ashok','bhavesh','deepak','dhruv','gaurav','hardik','harsh','jay','jatin',
    'kiran','mahesh','manish','mayur','mohit','mukesh','nikhil','nilesh','paresh',
    'pradeep','pranav','rahul','rajesh','rakesh','rohan','sachin','sagar','sanjay',
    'saurabh','shubham','siddharth','sumit','sunil','tarun','uday','vijay','vikas',
    'vivek','vamshi','yash',
}

COMMON_FEMALE_FIRST_NAMES = {
    'aarti','aishwarya','akanksha','anita','anjali','anusha','bhavika','bhumi','divya',
    'gauri','heena','hetal','janvi','jinal','kajal','karishma','khushi','kirti',
    'komal','manisha','megha','monika','muskan','neha','nidhi','nikita','payal',
    'pooja','priya','riddhi','ritu','sakshi','shreya','shruti','sonal','swati','teresa',
    'trisha','ujvala','vaishali','vijetha','vidhi',
}


# ══════════════════════════════════════════════════════════════
#  TEXT EXTRACTION
# ══════════════════════════════════════════════════════════════
def natural_file_sort_key(filename):
    """Sort 1.pdf, 2.pdf, 10.pdf in human order."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r'(\d+)', filename)]


def _append_unique_line(lines, seen, value):
    value = (value or '').strip()
    if not value:
        return
    key = re.sub(r'\s+', ' ', value).strip().lower()
    if key and key not in seen:
        seen.add(key)
        lines.append(value)


def _collect_docx_text(doc):
    lines = []
    seen = set()

    def add_paragraphs(paragraphs):
        for p in paragraphs:
            _append_unique_line(lines, seen, p.text)

    # Put header text first so name/contact in header gets higher priority.
    for section in doc.sections:
        for attr in ('header', 'first_page_header', 'even_page_header'):
            part = getattr(section, attr, None)
            if part is not None:
                add_paragraphs(part.paragraphs)

    add_paragraphs(doc.paragraphs)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                add_paragraphs(cell.paragraphs)

    for section in doc.sections:
        for attr in ('footer', 'first_page_footer', 'even_page_footer'):
            part = getattr(section, attr, None)
            if part is not None:
                add_paragraphs(part.paragraphs)

    return '\n'.join(lines)


def _normalize_phone_candidate(raw):
    if not raw:
        return None

    cleaned = re.sub(r'(?i)(?:ext\.?|x|extension)\s*\d{1,6}\b', '', raw).strip()
    digits = re.sub(r'\D', '', cleaned)

    if not (7 <= len(digits) <= 15):
        return None
    if not cleaned.startswith('+') and len(digits) > 12:
        return None
    if len(set(digits)) == 1:
        return None
    if re.match(r'^(19|20)\d{2}$', digits):
        return None

    year_hits = re.findall(r'(?:19|20)\d{2}', digits)
    if len(year_hits) >= 2:
        return None
    if len(digits) == 12 and digits.startswith('0') and year_hits:
        return None

    return f'+{digits}' if cleaned.startswith('+') else digits


def extract_text(path):
    """Extract text from PDF, DOCX, or DOC files with error handling."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Resume file not found: {path}")
    
    ext = os.path.splitext(path)[1].lower()
    text = None
    error = None
    
    try:
        if ext == '.pdf':
            try:
                text = pdf_extract_text(path)
                if not text or not text.strip():
                    error = "PDF extraction returned empty text"
            except Exception as pdf_err:
                error = f"pdfminer error: {str(pdf_err)[:100]}"
        
        elif ext == '.docx':
            if not DOCX_AVAILABLE:
                error = "python-docx not installed (pip install python-docx)"
            else:
                try:
                    doc = Document(path)
                    text = _collect_docx_text(doc)
                    if not text or not text.strip():
                        error = "DOCX extraction returned empty text"
                except Exception as docx_err:
                    error = f"python-docx error: {str(docx_err)[:100]}"
        
        elif ext == '.doc':
            if TEXTRACT_AVAILABLE:
                try:
                    raw = textract.process(path)
                    text = raw.decode('utf-8', errors='ignore')
                    if not text or not text.strip():
                        error = "DOC extraction returned empty text"
                except Exception as textract_err:
                    error = f"textract error: {str(textract_err)[:100]}"
            else:
                error = "textract not installed (pip install textract for .doc support)"
        
        else:
            error = f"Unsupported file extension: {ext}"
        
        # If we got an error but still have some text, log warning but return text
        if error and text:
            if ENABLE_DETAILED_LOGGING:
                print(f"    Warning during extraction: {error}")
            return text
        
        # If we got an error and no text, raise it
        if error:
            raise ValueError(error)
        
        return text or ""
    
    except Exception as exc:
        raise ValueError(f"Failed to extract from {os.path.basename(path)}: {str(exc)}")


def normalize_compact_text(text):
    """Break merged tokens common in PDF extraction."""
    if not text:
        return ''
    t = re.sub(r'(?<=[A-Za-z])(?=\d)', ' ', text)
    t = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', t)
    t = re.sub(r'(?<=@)(?=[A-Z])', ' ', t)
    return t


# ══════════════════════════════════════════════════════════════
#  NAME EXTRACTION
# ══════════════════════════════════════════════════════════════
def normalize_caps(line):
    words = line.split()
    if words and all(w.isupper() for w in words if w.isalpha()):
        return title_case(line.lower())
    return line


def title_case(s):
    return ' '.join(w.capitalize() for w in s.split())


def is_spaced(line):
    tokens = line.split()
    if not tokens:
        return True
    return sum(1 for t in tokens if len(t) <= 2) / len(tokens) > 0.5


def split_camel(text):
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)
    return text


def normalize_name_case(name):
    parts = []
    for token in name.split():
        core = token.strip("'-. ")
        if len(core) == 1:
            parts.append(token.upper())
        elif core.isupper() or core.islower():
            parts.append(token[0].upper() + token[1:].lower() if len(token) > 1 else token.upper())
        else:
            parts.append(token)
    return ' '.join(parts)


def sanitize_candidate(candidate):
    if not candidate:
        return ''
    c = candidate.strip()
    c = c.split('|')[0]
    c = re.sub(r'\([^)]{0,50}\)', ' ', c)

    if ',' in c:
        left, right = c.split(',', 1)
        if re.fullmatch(r'\s*[A-Z][A-Z0-9\.\-/\s]{1,20}\s*', right or ''):
            c = left

    c = re.sub(r'(?:\s+|,\s*)(?:[A-Z]{2,5}(?:/[A-Z]{2,5})*)(?:\s*\.?)*$', '', c)
    c = re.sub(r'(?i)^\s*(?:full\s+)?name\s*[:\-]\s*', '', c)
    c = re.sub(r'(?i)^\s*resume\s+of\s*', '', c)
    c = re.sub(r'^[\-–—:\.\)\(\[\]\{\}\|\s]+', '', c)
    c = re.sub(r'[\-–—:\.\)\(\[\]\{\}\|\s]+$', '', c)
    c = re.sub(r'\s+', ' ', c)
    if c.isupper() or c.islower():
        c = normalize_name_case(c)
    return c.strip()


def line_has_bad_context(line):
    l = line.lower()
    if BAD_CONTEXT_RE.search(l) and not re.search(r'\bname\b', l):
        return True
    tokens = [re.sub(r'[^a-z]', '', t) for t in l.split()]
    if any(t in COMPANY_HINTS for t in tokens if t):
        return True
    return False


def has_name_case_pattern(line):
    words = re.findall(r"[A-Za-z][A-Za-z'.-]*", line)
    if not words:
        return False
    if all(w.isupper() for w in words):
        return True
    if len(words) == 1:
        return words[0][0].isupper()
    capped = sum(1 for w in words if w[0].isupper())
    return capped == len(words)


def top_header_candidate(norm_lines):
    for line in norm_lines[:5]:
        if re.search(r'[@\d]|https?://', line, re.I):
            continue
        if line_has_bad_context(line):
            continue
        if looks_like_address(line):
            continue
        if not has_name_case_pattern(line):
            continue
        c = title_case(sanitize_candidate(split_camel(line)))
        if accept(c, strict=False, allow_single=True):
            return c
    return None


def looks_like_address(line):
    if re.search(r'\d', line):
        return True
    if ',' in line and len(line.split()) >= 4 and re.search(r'\d', line):
        return True
    tokens = [t for t in re.split(r'[^a-z]+', line.lower()) if t]
    return sum(1 for w in tokens if w in BLACKLIST) >= 2


def is_valid(name, allow_single=False):
    if not name:
        return False
    name = sanitize_candidate(name)
    name = re.sub(r'\s+', ' ', name).strip()
    words = name.split()
    if allow_single:
        if not (1 <= len(words) <= 5):
            return False
    else:
        if not (2 <= len(words) <= 5):
            return False
    if allow_single and len(words) == 1:
        alpha_only = re.sub(r'[^A-Za-z]', '', words[0])
        if len(alpha_only) < 3:
            return False
    if any(ch.isdigit() for ch in name):
        return False
    if re.search(r'[^A-Za-z\s\-\.\']', name):
        return False
    for w in words:
        alpha = re.sub(r'[^A-Za-z]', '', w)
        if not alpha:
            continue
        if not alpha[0].isupper():
            return False
        if len(alpha) < 2:
            if not (len(alpha) == 1 and (w.endswith('.') or w.isupper())):
                return False
    if any(len(re.sub(r'[^A-Za-z]', '', w)) > 20 for w in words):
        return False
    if len(words) >= 3 and any(len(re.sub(r'[^A-Za-z]', '', w)) > 12 for w in words):
        return False
    if any(w.lower().strip('.,') in BLACKLIST for w in words):
        return False
    if any(w.lower().strip('.,') in COMPANY_HINTS for w in words):
        return False
    if any(w.lower().strip('.,') in NON_NAME_WORDS for w in words):
        return False
    if any(w.isupper() and len(w) > 3 for w in words):
        return False
    return True


def dataset_ok(name, min_score=2):
    if not DATASET_AVAILABLE:
        return True
    score = 0
    for i, word in enumerate(name.strip().split()):
        clean = re.sub(r'[^A-Za-z]', '', word)
        if len(clean) < 2:
            continue
        try:
            r = nd.search(clean)
            if i == 0:
                score += 3 if r.get('first_name') else (1 if r.get('last_name') else 0)
            else:
                score += 2 if r.get('last_name') else (1 if r.get('first_name') else 0)
        except Exception:
            pass
    return score >= min_score


def accept(name, strict=True, allow_single=False):
    if not is_valid(name, allow_single=allow_single):
        return False
    if strict and DATASET_AVAILABLE and len(name.split()) >= 2:
        return dataset_ok(name)
    return True


def name_from_email(full_text):
    matches = re.finditer(
        r'([A-Za-z][A-Za-z0-9._+-]{2,})@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        full_text
    )
    for m in matches:
        local = m.group(1).lower()
        chunks = [p for p in re.split(r'[^a-z0-9]+', local) if p]
        alpha_chunks = [re.sub(r'\d+', '', c) for c in chunks]
        alpha_chunks = [c for c in alpha_chunks if len(c) >= 3]

        if len(alpha_chunks) >= 2:
            c = title_case(' '.join(alpha_chunks[-2:]))
            if accept(c, strict=False):
                return c

        if alpha_chunks:
            single = alpha_chunks[-1]
            if len(single) >= 3:
                c = title_case(single)
                if accept(c, strict=False, allow_single=True):
                    return c
            if len(single) >= 6:
                for sur in sorted(COMMON_SURNAMES, key=len, reverse=True):
                    if single.endswith(sur) and len(single) > len(sur) + 2:
                        c = title_case(single[:-len(sur)] + ' ' + sur)
                        if accept(c, strict=False):
                            return c
                for i in range(3, len(single) - 2):
                    c = title_case(single[:i] + ' ' + single[i:])
                    if accept(c, strict=False):
                        return c
    return None


# ══════════════════════════════════════════════════════════════
#  CONTACT NAME EXTRACTION
# ══════════════════════════════════════════════════════════════

def extract_name(text):
    raw = [l.strip() for l in text.split('\n') if l.strip()]
    if not raw:
        return None

    compact_text = normalize_compact_text(text)
    norm = [normalize_caps(l) for l in raw]
    full = '\n'.join(norm)

    # S-Blob: single-line / heavily merged resumes
    if len(raw) <= 3 or sum(1 for l in raw if len(l) > 120) >= 1:
        m = re.search(
            r'(?<![A-Z])([A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})'
            r'(?=(?:Address|Phone|Email|Contact|Objective|Summary|Skills|Work|Experience|$))',
            compact_text
        )
        if m:
            c = title_case(sanitize_candidate(m.group(1)))
            if accept(c, strict=False):
                return c

    # S0.3: Strong top-line candidates
    for i, line in enumerate(norm[:10]):
        if re.search(r'[@\d]|https?://', line, re.I):
            continue
        if line.lower().strip('.,- ') in SKIP_LINES:
            continue
        if line_has_bad_context(line):
            continue
        if not has_name_case_pattern(line):
            continue
        if looks_like_address(line):
            continue
        c = title_case(sanitize_candidate(split_camel(line)))
        if accept(c, strict=False, allow_single=(i < 4)):
            return c

    # S0: Explicit "Name:" label in first 20 lines
    early_text = '\n'.join(norm[:20])
    for m in re.finditer(r'(?im)^(?:full\s+)?name\s*[:\-]\s*[-–—]*\s*([^\n]{2,60})$', early_text):
        c = title_case(sanitize_candidate(m.group(1).split('|')[0]))
        if accept(c, strict=False, allow_single=True):
            head = top_header_candidate(norm)
            if head and head.lower() != c.lower():
                if sorted(w.lower() for w in head.split()) == sorted(w.lower() for w in c.split()):
                    return head
            return c

    # S0.1: "Resume of …"
    for i, line in enumerate(norm[:6]):
        if re.match(r'^resume\s+of\s*$', line, re.I):
            if i + 1 < len(norm):
                c = title_case(sanitize_candidate(norm[i + 1]))
                if accept(c, strict=False, allow_single=True):
                    return c
        m = re.match(r'^resume\s+of\s+(.+)$', line, re.I)
        if m:
            c = title_case(sanitize_candidate(m.group(1)))
            if accept(c, strict=False, allow_single=True):
                return c

    # S0.2: Two-line header
    for i in range(min(len(norm) - 1, 8)):
        a, b = norm[i], norm[i + 1]
        if re.search(r'[@\d]', a + b):
            continue
        if a.lower().strip('.,- ') in SKIP_LINES or b.lower().strip('.,- ') in SKIP_LINES:
            continue
        if line_has_bad_context(a) or line_has_bad_context(b):
            continue
        if not (has_name_case_pattern(a) and has_name_case_pattern(b)):
            continue
        if looks_like_address(a) or looks_like_address(b):
            continue
        ca, cb = sanitize_candidate(a), sanitize_candidate(b)
        if not ca or not cb:
            continue
        combined = f"{title_case(ca)} {title_case(cb)}"
        if accept(combined, strict=False):
            return combined

    # EC1: Whole resume on one line
    if raw and len(raw[0]) > 150:
        blob = raw[0]
        m = re.search(
            r'([A-Z][A-Z]+(?:\s+[A-Z][A-Z]+){1,3})\s+(?:' + SECTION_WORDS.pattern + r')',
            blob
        )
        if m:
            titled = m.group(1).title()
            if is_valid(titled):
                return titled
        for cap in re.finditer(r'\b([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})?)\b', blob):
            t = cap.group(1).title()
            if accept(t, strict=False):
                return t

    # EC2: Lowercase last name
    for line in raw[:6]:
        if ',' in line or line_has_bad_context(line):
            continue
        if re.match(r'^[A-Z][a-z]+(?:\s+[a-zA-Z][a-z]+){1,3}$', line.strip()):
            t = title_case(sanitize_candidate(line.strip()))
            if accept(t, strict=False):
                return t

    # S1: spaCy PERSON entities
    if SPACY_AVAILABLE:
        doc = nlp(full[:600])
        for ent in doc.ents:
            if ent.label_ == 'PERSON' and not line_has_bad_context(ent.text):
                c = title_case(sanitize_candidate(ent.text.strip()))
                if accept(c, strict=False):
                    return c

    # S2: Line-by-line scan (first 15 lines)
    for i, line in enumerate(norm[:15]):
        if is_spaced(line):
            continue
        if len(line) <= 1:
            continue
        if line.lower().strip('.,- ') in SKIP_LINES:
            continue
        if re.search(r'[@#\|<>{}]', line):
            continue
        if line_has_bad_context(line):
            continue
        if not has_name_case_pattern(line):
            continue
        if looks_like_address(line):
            continue

        spaced = split_camel(line)
        if spaced != line:
            c = title_case(sanitize_candidate(re.sub(r'\s+', ' ', spaced).strip()))
            if accept(c, strict=False):
                return c

        clean = title_case(sanitize_candidate(re.sub(r'\s+', ' ', line).strip()))
        if re.match(r'^[A-Za-z][A-Za-z\s\.\-\']{2,45}$', clean):
            if accept(clean, strict=False, allow_single=(i < 4)):
                return clean

        if i + 1 < len(norm):
            nxt = norm[i + 1]
            if (len(nxt) > 1
                    and not is_spaced(nxt)
                    and nxt.lower().strip() not in SKIP_LINES
                    and not line_has_bad_context(nxt)
                    and not looks_like_address(nxt)
                    and not re.search(r'[@#\|<>{}0-9]', nxt)
                    and len(nxt.split()) <= 3):
                combined = title_case(
                    sanitize_candidate(re.sub(r'\s+', ' ', line + ' ' + nxt).strip())
                )
                if re.match(r'^[A-Za-z][A-Za-z\s\.\-\']{3,55}$', combined):
                    if accept(combined, strict=False):
                        return combined

    # EC7: Tail-signature checks
    m = re.search(
        r'(?i)(?:thanks|regards|sincerely|faithfully)[,\.\s]+([A-Za-z][a-zA-Z \.]{4,45})',
        full
    )
    if m:
        c = title_case(sanitize_candidate(re.sub(r'\s+', ' ', m.group(1)).strip()))
        c = re.sub(r'\s*(pvt|ltd|inc|llp|co)\.?\s*$', '', c, flags=re.I).strip()
        if accept(c, strict=False):
            return c

    m = re.search(r'(?im)^\s*submitted\s+by\s*[:\-]\s*([A-Za-z][A-Za-z\.\s\'\-]{2,45})\s*$', full)
    if m:
        c = title_case(sanitize_candidate(m.group(1)))
        if accept(c, strict=False):
            return c

    m = re.search(r'(?im)^\s*date\s*:\s*(?:[^A-Za-z\n]*)([A-Z][A-Z\.\s]{4,45})\s*$', full)
    if m:
        c = title_case(sanitize_candidate(m.group(1)))
        if accept(c, strict=False):
            return c

    tail = '\n'.join(norm[-40:])
    for m in re.finditer(r'\(([A-Za-z][A-Za-z\.\'\- ]{3,45})\)\s*$', tail, flags=re.M):
        c = title_case(sanitize_candidate(m.group(1)))
        if accept(c, strict=False):
            return c

    email_name = name_from_email(text)
    if email_name:
        return email_name

    # Final strict fallback only on early lines to avoid deep section-heading false positives.
    for i, line in enumerate(norm[:20]):
        if re.search(r'[@\d]|https?://', line, re.I):
            continue
        if line.lower().strip('.,- ') in SKIP_LINES:
            continue
        if line_has_bad_context(line):
            continue
        if not has_name_case_pattern(line):
            continue
        if looks_like_address(line):
            continue

        c = title_case(sanitize_candidate(split_camel(line)))
        if accept(c, strict=True, allow_single=(i < 3)):
            return c

    return None


# ══════════════════════════════════════════════════════════════
#  CONTACT NUMBER EXTRACTION
# ══════════════════════════════════════════════════════════════
def extract_contact_number(text):
    if not text:
        return None

    t = normalize_compact_text(text).replace('\r', '\n')
    candidates = []
    segments = [seg.strip() for seg in re.split(r'[\n|]+', t) if seg and seg.strip()]
    if not segments:
        segments = [t]

    label_pattern = re.compile(
        r'(?i)\b(?:mobile|mob|phone|ph|contact|tel|telephone|call|whatsapp)\b\s*[:\-]?\s*([+()0-9][0-9()\s.\-/]{6,25})'
    )
    generic_pattern = re.compile(
        r'(?<!\w)(?:\+?\d{1,3}[ \t.\-]?)?(?:\(?\d{2,5}\)?[ \t.\-]?)?\d(?:[\d \t()./\-]{5,}\d)(?!\w)'
    )

    for seg_idx, seg in enumerate(segments):
        for m in label_pattern.finditer(seg):
            raw = m.group(1)
            number = _normalize_phone_candidate(raw)
            if not number:
                continue
            digits_len = len(re.sub(r'\D', '', number))
            len_pref = 0 if 10 <= digits_len <= 12 else (1 if digits_len == 13 else 2)
            candidates.append((8, len_pref, digits_len, seg_idx, m.start(), number))

        for m in generic_pattern.finditer(seg):
            raw = m.group(0)
            number = _normalize_phone_candidate(raw)
            if not number:
                continue

            # For unlabeled text, avoid short numeric fragments that are often dates/IDs.
            digits_len = len(re.sub(r'\D', '', number))
            if digits_len < 10:
                continue

            ctx = seg[max(0, m.start()-35):min(len(seg), m.end()+35)].lower()
            score = 1
            if re.search(r'\b(phone|mobile|mob|contact|call|tel|telephone|whatsapp)\b', ctx):
                score += 3
            if re.search(r'\b(fax|pin|pincode|zip|dob|date|year|salary|ctc)\b', ctx):
                score -= 3
            if number.startswith('+'):
                score += 1
            if digits_len >= 10:
                score += 1

            len_pref = 0 if 10 <= digits_len <= 12 else (1 if digits_len == 13 else 2)
            candidates.append((score, len_pref, digits_len, seg_idx, m.start(), number))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (-x[0], x[1], -x[2], x[3], x[4]))
    return candidates[0][5]


# ══════════════════════════════════════════════════════════════
#  EMAIL EXTRACTION
# ══════════════════════════════════════════════════════════════
def extract_email_from_resume(text):
    if not text:
        return None

    domain_prefix_pattern = re.compile(
        r"^([a-z0-9-]{1,30}(?:\.[a-z0-9-]{1,30}){0,2}"
        r"\.(?:co\.in|org\.in|ac\.in|gov\.in|com|org|net|edu|gov|in|co|io|ai|info|biz|me|us|uk|ca|au|de|fr|jp|sg))",
        re.I,
    )
    strict_email = re.compile(r"^[a-z0-9][a-z0-9._%+-]{1,63}@[a-z0-9-]+(?:\.[a-z0-9-]+)+$")
    noisy_prefix = re.compile(r"^(?:contact|skills|languages|profile|email|mobile|phone)+", re.I)

    def normalize_piece(s):
        s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
        s = re.sub(r"(?i)\(\s*at\s*\)|\[\s*at\s*\]|\sat\s", "@", s)
        s = re.sub(r"(?i)\(\s*dot\s*\)|\[\s*dot\s*\]|\sdot\s", ".", s)
        s = re.sub(r"\s*@\s*", "@", s)
        s = re.sub(r"\s*\.\s*", ".", s)
        return re.sub(r"\s+", " ", s).strip("<>()[]{}|,;:\\'\" ")

    def clean_local(local_raw):
        local = local_raw.strip(" ._-+%")
        for _ in range(2):
            local = noisy_prefix.sub("", local)
        for _ in range(3):
            lowered = local.lower()
            cut = None
            for p in ("emailid","email","mailid","contact","skills","skill",
                      "objective","profile","resume"):
                if lowered.startswith(p) and len(local) > len(p) + 3:
                    cut = len(p)
                    break
            if cut is None:
                break
            local = local[cut:]
        local = re.sub(r"(?i)^s[^a-z0-9]*k[^a-z0-9]*i[^a-z0-9]*l[^a-z0-9]*l[^a-z0-9]*s", "", local)
        looks_noisy = (
            len(local) > 22
            or bool(re.search(r"[A-Z]{3,}", local))
            or bool(re.search(r"\d{8,}.*[A-Za-z]{4,}", local))
        )
        if looks_noisy:
            alpha_parts = [p for p in re.split(r"\d{6,}", local) if re.search(r"[A-Za-z]", p)]
            if alpha_parts and len(alpha_parts[-1]) >= 4:
                local = alpha_parts[-1]
        if re.match(r"^\d{2,}[A-Za-z]", local):
            local = re.sub(r"^\d+", "", local)
        return local.strip(" ._-+%").rstrip(".")

    def build_email(raw_fragment):
        frag = normalize_piece(raw_fragment)
        if "@" not in frag:
            return None
        if frag.count("@") > 1:
            left, right = frag.rsplit("@", 1)
        else:
            left, right = frag.split("@", 1)
        local_tokens = re.findall(r"[A-Za-z0-9._%+-]+", left)
        ignore = {"email","mail","id","contact","e","mailid"}
        local_tokens = [t for t in local_tokens if t.lower() not in ignore]
        if not local_tokens:
            return None
        single_ratio = sum(1 for t in local_tokens if len(t) == 1) / len(local_tokens)
        if len(local_tokens) >= 8 and single_ratio >= 0.6:
            collected = []
            for tok in reversed(local_tokens):
                if len(tok) == 1 or tok.isdigit():
                    collected.append(tok)
                else:
                    if len(''.join(reversed(collected))) >= 5:
                        break
                    collected.append(tok)
            local_raw = ''.join(reversed(collected))
        elif (len(local_tokens) >= 2
              and len(local_tokens[-1]) <= 6
              and len(local_tokens[-2]) <= 12
              and local_tokens[-2].lower() not in ignore):
            local_raw = local_tokens[-2] + local_tokens[-1]
        else:
            local_raw = local_tokens[-1]
        local = clean_local(local_raw)
        local = re.sub(r"(?i)^(?:skills?|contact|email|mailid|objective|profile|resume)+", "", local).strip("._-+")
        if len(local) < 3:
            return None
        right_tokens = re.findall(r"[A-Za-z0-9.-]+", right)
        if not right_tokens:
            return None
        domain_head = ''.join(right_tokens[:4]).strip('.')
        dm = domain_prefix_pattern.search(domain_head)
        if not dm:
            domain_head = ''.join(right_tokens[:8]).strip('.')
            dm = domain_prefix_pattern.search(domain_head)
        if not dm:
            return None
        domain = dm.group(1).lower()
        email = f"{local.lower()}@{domain}"
        if not strict_email.match(email):
            return None
        if ".." in email or email.endswith("."):
            return None
        return email

    candidates = []

    for m in re.finditer(r"[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9.-]{3,}", text):
        email = build_email(m.group(0))
        if email:
            ctx = text[max(0,m.start()-35):min(len(text),m.end()+35)].lower()
            score = 2 if re.search(r"email|e-mail|mail\s*id|contact", ctx) else 1
            candidates.append((score, len(email), email))

    for m in re.finditer(r"[A-Za-z0-9._%+\-\s]{2,90}@[A-Za-z0-9.\-\s]{2,120}", text):
        email = build_email(m.group(0))
        if email:
            ctx = text[max(0,m.start()-35):min(len(text),m.end()+35)].lower()
            score = 2 if re.search(r"email|e-mail|mail\s*id|contact", ctx) else 1
            if re.search(r"\d{8,}", m.group(0)):
                score -= 1
            candidates.append((score, len(email), email))

    for m in re.finditer(
        r"[A-Za-z0-9._%+\-\s]{2,80}(?:\(|\[)?\s*at\s*(?:\)|\])?[A-Za-z0-9.\-\s]{2,80}"
        r"(?:\(|\[)?\s*dot\s*(?:\)|\])?\s*[A-Za-z\s]{2,20}",
        text, re.I
    ):
        email = build_email(m.group(0))
        if email:
            ctx = text[max(0,m.start()-35):min(len(text),m.end()+35)].lower()
            score = 2 if re.search(r"email|e-mail|mail\s*id|contact", ctx) else 1
            candidates.append((score, len(email), email))

    if not candidates:
        return None
    candidates = list(set(candidates))
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    return candidates[0][2]


# ══════════════════════════════════════════════════════════════
#  GENDER & ADDRESS EXTRACTION
# ══════════════════════════════════════════════════════════════
def _infer_gender_from_name(name):
    if not name:
        return None

    tokens = [re.sub(r"[^A-Za-z]", "", t).lower() for t in name.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return None

    male_titles = {'mr', 'mister', 'sir', 'shri'}
    female_titles = {'mrs', 'ms', 'miss', 'madam', 'smt'}

    first = tokens[0]
    if first in male_titles:
        return 'Male'
    if first in female_titles:
        return 'Female'

    if first in {'mr', 'mrs', 'ms', 'miss'} and len(tokens) >= 2:
        first = tokens[1]

    if first in COMMON_MALE_FIRST_NAMES:
        return 'Male'
    if first in COMMON_FEMALE_FIRST_NAMES:
        return 'Female'

    female_suffixes = (
        'a', 'aa', 'i', 'ita', 'isha', 'ina', 'ani', 'ika', 'shree', 'lata', 'rani',
        'laxmi', 'lakshmi', 'preeti', 'priya', 'jyoti', 'swati', 'rati',
    )
    male_suffixes = (
        'kumar', 'singh', 'bhai', 'raj', 'veer', 'vir', 'jeet', 'deep', 'esh', 'ish',
        'endra', 'kant', 'nath', 'pal', 'jit', 'dev', 'prakash', 'teja',
    )
    male_end_a_exceptions = {
        'krishna', 'arya', 'siva', 'shiva', 'rama', 'vishva', 'jaya', 'vijaya',
    }

    if first.endswith('kumar') or first.endswith('singh') or first.endswith('bhai'):
        return 'Male'
    if first.endswith('ben'):
        return 'Female'

    if any(first.endswith(suf) for suf in male_suffixes):
        return 'Male'

    if first not in male_end_a_exceptions and any(first.endswith(suf) for suf in female_suffixes):
        return 'Female'

    # Lightweight final heuristic: consonant-ending first names are more often male in this dataset.
    if first[-1] in {'n', 'r', 'l', 'k', 't', 'm', 'd', 's', 'v', 'y', 'h'}:
        return 'Male'

    return None


def extract_gender(text, name=None):
    if not text:
        return _infer_gender_from_name(name)

    t = normalize_compact_text(text)
    lines = [re.sub(r'\s+', ' ', line).strip() for line in t.splitlines() if line.strip()]

    label_re = re.compile(
        r'(?i)\b(?:gender|sex)\b\s*[:\-]?\s*(male|female|m|f)\b'
    )

    for line in lines[:80]:
        m = label_re.search(line)
        if not m:
            continue
        raw = m.group(1).lower()
        if raw in {'male', 'm'}:
            return 'Male'
        if raw in {'female', 'f'}:
            return 'Female'

    # Fallback: gender token near gender/sex labels.
    early = '\n'.join(lines[:35]).lower()
    if re.search(r'\b(?:gender|sex)\b[^\n]{0,24}\b(?:male|m)\b', early):
        return 'Male'
    if re.search(r'\b(?:gender|sex)\b[^\n]{0,24}\b(?:female|f)\b', early):
        return 'Female'

    # Last fallback: infer from the extracted candidate name.
    return _infer_gender_from_name(name)


def extract_address(text):
    if not text:
        return None

    t = normalize_compact_text(text)
    lines = [re.sub(r'\s+', ' ', line).strip(' ,;:-') for line in t.splitlines() if line.strip()]
    if not lines:
        return None

    label_re = re.compile(
        r'(?i)^(?:permanent|current|present|communication|residential)?\s*address\s*[:\-]?\s*(.*)$'
    )
    stop_re = re.compile(
        r'(?i)^(?:education|skills?|experience|objective|summary|profile|projects?|languages?|'
        r'declaration|reference|hobbies|strengths|certificates?|achievements?|'
        r'bachelor|master|diploma|degree|university|college|institute|school|'
        r'professional\s+experience|technical\s+skills|work\s+experience)\b'
    )
    contact_re = re.compile(r'(?i)(?:@|\b(?:phone|mobile|contact|email|tel|whatsapp)\b|https?://)')
    hint_re = re.compile(
        r'(?i)\b(?:road|rd\.?|street|st\.?|lane|ln\.?|nagar|colony|sector|plot|block|'
        r'flat|floor|apartment|society|near|taluka|tehsil|dist|district|city|state|india|'
        r'gujarat|maharashtra|rajasthan|punjab|bihar|kerala|odisha|haryana|pradesh|goa|'
        r'karnataka|postcode|pincode|zip)\b'
    )
    non_address_re = re.compile(
        r'(?i)\b(?:bachelor|master|diploma|degree|university|college|school|institute|cgpa|gpa|'
        r'certification|training|course|project|client|role|responsibilit\w*|experience|'
        r'java|python|spring|hibernate|oracle|mysql|sql|javascript|html|css|aws|jira|agile|'
        r'scrum|methodology|environment|objective|summary|profile|skills?)\b'
    )

    def clean_address(value):
        value = re.sub(r'\s+', ' ', value).strip(' ,;:-')
        if len(value) < 8:
            return None
        if len(value) > 220:
            return None
        if len(value.split()) > 30:
            return None
        if value.count(',') > 6:
            return None
        if contact_re.search(value):
            return None
        # Count how many non-address keywords appear - reject only if heavily loaded
        bad_words = len(re.findall(non_address_re, value))
        if bad_words >= 3:
            return None
        # Address should have location hints or numbers
        digit_hits = len(re.findall(r'\d', value))
        hint_hits = len(hint_re.findall(value))
        if digit_hits == 0 and hint_hits < 1:
            return None
        return value

    # First preference: explicit address label.
    for i, line in enumerate(lines[:80]):
        m = label_re.match(line)
        if not m:
            continue

        parts = []
        first = m.group(1).strip()
        if first and not stop_re.match(first) and not contact_re.search(first):
            parts.append(first)

        # Capture a few immediate continuation lines.
        for j in range(i + 1, min(i + 5, len(lines))):
            nxt = lines[j]
            if stop_re.match(nxt):
                break
            if contact_re.search(nxt):
                break
            if non_address_re.search(nxt):
                break
            if len(nxt.split()) <= 1:
                break
            parts.append(nxt)

        candidate = clean_address(', '.join(parts))
        if candidate:
            return candidate

    # Fallback: best-scoring address-like line block.
    best = None
    best_score = -1
    for i, line in enumerate(lines[:120]):
        if stop_re.match(line) or contact_re.search(line):
            continue
        # Count problematic keywords but don't auto-reject
        bad_count = len(re.findall(non_address_re, line))
        if bad_count >= 3:
            continue
        
        score = 0
        if re.search(r'\d', line):
            score += 3
        if ',' in line:
            score += 1
        if hint_re.search(line):
            score += 3
        if 2 <= len(line.split()) <= 20:
            score += 1
        
        # Penalize lines with too many non-address terms
        score -= bad_count

        if score < 3:
            continue

        parts = [line]
        for j in range(i + 1, min(i + 5, len(lines))):
            nxt = lines[j]
            if stop_re.match(nxt) or contact_re.search(nxt):
                break
            bad_nxt = len(re.findall(non_address_re, nxt))
            if bad_nxt >= 3:
                break
            if len(nxt.split()) <= 1:
                break
            parts.append(nxt)

        candidate = clean_address(', '.join(parts))
        if candidate and score > best_score:
            best = candidate
            best_score = score

    return best


# ══════════════════════════════════════════════════════════════
#  SKILLS LOADING & MATCHING
# ══════════════════════════════════════════════════════════════
def is_valid_skill(skill):
    """Return True if the skill string is usable."""
    if not skill:
        return False
    if len(skill) < 2 or len(skill) > 120:
        return False
    invalid_patterns = [
        r"^i'm unable to extract",
        r"^unable to extract",
        r"^error",
        r"^n/a$",
        r"^none$",
        r"^unknown$",
        r"^not applicable",
    ]
    skill_lower = skill.lower()
    for pattern in invalid_patterns:
        if re.search(pattern, skill_lower):
            return False
    alpha_count = sum(1 for c in skill if c.isalpha())
    if alpha_count < len(skill) * 0.4:
        return False
    punct_count = sum(1 for c in skill if c in "!@#$%^&*()[]{}|\\<>?/~`")
    if punct_count > len(skill) * 0.3:
        return False
    return True


def normalize_skill_key(skill):
    """Canonical key so formatting variants collapse to one skill."""
    if not skill:
        return ''
    k = skill.lower().strip()
    k = re.sub(r'\s+', ' ', k)
    k = re.sub(r'[^a-z0-9+#]+', '', k)   # keep + and # for C++, C#
    return k


def load_skills_from_csv(csv_path):
    """
    Load skills from CSV.

    Accepts two formats:
      1. Our generated CSV  – columns: skill, category, normalized_skill, resume_match_weight
         → reads the 'skill' column (raw lowercase token)
      2. Simple single-column CSV  – each row is one skill string
         → reads every non-header cell as a skill

    Returns list of unique skill strings.
    """
    skills = []
    seen = set()
    invalid_count = 0

    if not os.path.exists(csv_path):
        print(f"⚠️  Skills CSV not found: {csv_path}")
        return skills

    with open(csv_path, mode='r', encoding='utf-8', errors='ignore', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Detect format: does it have our generated columns?
        has_skill_col = 'skill' in [fn.strip().lower() for fn in fieldnames]
        has_norm_col  = 'normalized_skill' in [fn.strip().lower() for fn in fieldnames]

        for row in reader:
            if has_skill_col:
                # Our generated CSV: use both 'skill' (raw) and 'normalized_skill' (display)
                raw_skill  = row.get('skill', '').strip()
                norm_skill = row.get('normalized_skill', '').strip() if has_norm_col else ''

                for candidate in filter(None, [raw_skill, norm_skill]):
                    candidate = re.sub(r'\s+', ' ', candidate).strip(" \t\r\n\"'")
                    if not is_valid_skill(candidate):
                        if candidate:
                            invalid_count += 1
                        continue
                    key = normalize_skill_key(candidate)
                    if key and key not in seen:
                        seen.add(key)
                        skills.append(candidate)
            else:
                # Simple single-column CSV
                for cell in row.values():
                    skill = re.sub(r'\s+', ' ', cell).strip(" \t\r\n\"'")
                    if not is_valid_skill(skill):
                        if skill:
                            invalid_count += 1
                        continue
                    key = normalize_skill_key(skill)
                    if key and key not in seen:
                        seen.add(key)
                        skills.append(skill)

    if invalid_count > 0:
        print(f"⚠️  Filtered out {invalid_count} invalid skill entries from CSV")

    return skills


def extract_skills_from_resume(text, skills_list):
    """
    Return every skill from skills_list that appears in the resume text.
    Uses whole-word / alphanumeric-boundary matching (case-insensitive).
    """
    if not text or not skills_list:
        return []

    normalized_text = normalize_compact_text(text)
    matched_skills = []
    seen = set()

    for skill in skills_list:
        if not skill:
            continue
        escaped = re.escape(skill.strip())
        escaped = escaped.replace(r'\ ', r'\s+')
        pattern = re.compile(
            rf'(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])',
            re.IGNORECASE
        )
        if pattern.search(normalized_text):
            key = normalize_skill_key(skill)
            if key and key not in seen:
                seen.add(key)
                matched_skills.append(skill)

    return matched_skills


# ══════════════════════════════════════════════════════════════
#  BATCH RUNNER
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#  BATCH RUNNER with Validation & Logging
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':

    # ── Import validation module ──────────────────────────────
    try:
        if ENABLE_VALIDATION:
            from validation import ResumeValidator, print_validation_report
            validator = ResumeValidator()
        else:
            validator = None
    except ImportError:
        print("⚠️  validation module not found. Running without accuracy checking.")
        validator = None
    
    # ── Setup logging ─────────────────────────────────────────
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log_messages = []
    
    def log_message(msg):
        """Log to both console and file."""
        print(msg)
        log_messages.append(msg)
    
    # ── Load skills ───────────────────────────────────────────
    skills_list = load_skills_from_csv(SKILLS_CSV)
    results = []

    # Set the folder path for resumes - can be changed here
    PROCESS_FOLDER = "D:\\Ktas Project\\ATS\\ATS Email Parser\\pending resume"
    
    # If folder doesn't exist, use default
    if not os.path.isdir(PROCESS_FOLDER):
        PROCESS_FOLDER = RESUME_FOLDER

    # ── Discover resume files ─────────────────────────────────
    if not os.path.isdir(PROCESS_FOLDER):
        log_message(f"❌ Resume folder not found: {PROCESS_FOLDER}")
        raise SystemExit(1)

    resume_files = sorted(
        [f for f in os.listdir(PROCESS_FOLDER)
         if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS],
        key=natural_file_sort_key
    )

    if not resume_files:
        log_message(f"❌ No supported files (.pdf, .doc, .docx) found in: {PROCESS_FOLDER}")
        raise SystemExit(1)

    log_message(f"📄 Loaded {len(skills_list)} skills from: {SKILLS_CSV}")
    log_message(f"📂 Processing {len(resume_files)} resume file(s) from: {PROCESS_FOLDER}\n")

    col_w = {'#': 4, 'file': 22, 'name': 30, 'phone': 14, 'gender': 8, 'email': 38}
    header = (
        f"{'#':<{col_w['#']}} "
        f"{'File':<{col_w['file']}} "
        f"{'Name':<{col_w['name']}} "
        f"{'Phone':<{col_w['phone']}} "
        f"{'Gender':<{col_w['gender']}} "
        f"Email"
    )
    log_message(header)
    log_message("─" * 120)

    # Track statistics
    stats = {
        'total': len(resume_files),
        'successful': 0,
        'errors': 0,
        'missing_name': 0,
        'missing_email': 0,
        'missing_phone': 0,
        'skills_found': 0,
    }

    for i, fname in enumerate(resume_files, 1):
        path = os.path.join(PROCESS_FOLDER, fname)
        extraction_error = None
        
        try:
            # Extract all data
            text            = extract_text(path)
            name            = extract_name(text)
            contact_number  = extract_contact_number(text)
            email           = extract_email_from_resume(text)
            gender          = extract_gender(text, name=name)
            address         = extract_address(text)
            matched_skills  = extract_skills_from_resume(text, skills_list)

            results.append({
                'file'          : fname,
                'name'          : name,
                'contact_number': contact_number,
                'email'         : email,
                'gender'        : gender,
                'address'       : address,
                'skills'        : matched_skills,
            })

            # Update statistics
            stats['successful'] += 1
            if not name:
                stats['missing_name'] += 1
            if not email:
                stats['missing_email'] += 1
            if not contact_number:
                stats['missing_phone'] += 1
            if matched_skills:
                stats['skills_found'] += 1

            # Format output with validation indicators
            name_col  = (name or '❌ NOT FOUND')[:col_w['name']-1]
            phone_col = (contact_number or '❌ NOT FOUND')[:col_w['phone']-1]
            gender_col = (gender or '❌ N/A')[:col_w['gender']-1]
            email_col = email or '❌ NOT FOUND'
            
            log_message(
                f"  {i:<{col_w['#']}} "
                f"{fname:<{col_w['file']}} "
                f"{name_col:<{col_w['name']}} "
                f"{phone_col:<{col_w['phone']}} "
                f"{gender_col:<{col_w['gender']}} "
                f"{email_col}"
            )

            # Print address and skills on separate lines
            if address:
                log_message(f"       Address: {address[:60]}...")
            else:
                log_message("       Address: ❌ NOT FOUND")

            if matched_skills:
                preview = ', '.join(matched_skills[:8])
                if len(matched_skills) > 8:
                    preview += f"  (+{len(matched_skills) - 8} more)"
                log_message(f"       Skills [{len(matched_skills)}]: {preview}")
            else:
                log_message("       Skills: ❌ NOT FOUND")

        except Exception as exc:
            stats['errors'] += 1
            extraction_error = str(exc)
            results.append({
                'file'          : fname,
                'name'          : None,
                'contact_number': None,
                'email'         : None,
                'gender'        : None,
                'address'       : None,
                'skills'        : [],
                'error'         : extraction_error,
            })
            log_message(f"  {i:<{col_w['#']}} {fname:<{col_w['file']}} ❌ Error: {exc}")

    # ── Validation & Reports ──────────────────────────────────
    validation_summary = None
    if validator and results:
        validation_summary = validator.validate_batch(results)
        log_message("\n" + "="*120)
        print_validation_report(validation_summary)
        
        # Save validation report
        os.makedirs(os.path.dirname(VALIDATION_JSON), exist_ok=True)
        with open(VALIDATION_JSON, 'w', encoding='utf-8') as vf:
            json.dump(validation_summary, vf, indent=2, ensure_ascii=False)
        log_message(f"💾 Validation report saved → {VALIDATION_JSON}")

    # ── Save JSON ─────────────────────────────────────────────
    results.sort(key=lambda item: natural_file_sort_key(item.get('file', '')))
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as jf:
        json.dump(results, jf, indent=2, ensure_ascii=False)

    # ── Print Summary Statistics ──────────────────────────────
    log_message("\n" + "─" * 120)
    log_message("📊 PROCESSING SUMMARY:")
    log_message(f"   Total files processed: {stats['total']}")
    log_message(f"   Successfully parsed: {stats['successful']} ({stats['successful']/stats['total']*100:.1f}%)")
    log_message(f"   Extraction errors: {stats['errors']} ({stats['errors']/stats['total']*100:.1f}%)")
    log_message(f"\n📋 EXTRACTION QUALITY:")
    log_message(f"   Names found: {stats['total'] - stats['missing_name']}/{stats['total']} ({(stats['total'] - stats['missing_name'])/stats['total']*100:.1f}%)")
    log_message(f"   Emails found: {stats['total'] - stats['missing_email']}/{stats['total']} ({(stats['total'] - stats['missing_email'])/stats['total']*100:.1f}%)")
    log_message(f"   Phones found: {stats['total'] - stats['missing_phone']}/{stats['total']} ({(stats['total'] - stats['missing_phone'])/stats['total']*100:.1f}%)")
    log_message(f"   Resumes with skills: {stats['skills_found']}/{stats['total']} ({stats['skills_found']/stats['total']*100:.1f}%)")
    
    log_message(f"\n💾 Results saved:")
    log_message(f"   Main output → {OUTPUT_JSON}")
    log_message(f"   Processing log → {LOG_FILE}")
    log_message(f"✅ Done.\n")

    # ── Save log file ─────────────────────────────────────────
    with open(LOG_FILE, 'w', encoding='utf-8') as lf:
        lf.write('\n'.join(log_messages))