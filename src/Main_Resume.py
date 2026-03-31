import re
import os
import csv
import json
import sys
import importlib
import argparse
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# ── Lazy-loaded name validation dataset ─────────────────────────
nd = None
DATASET_AVAILABLE = False
ND_TOKEN_CACHE = {}
_ND_CACHE_LOCK = threading.Lock()

def _ensure_names_dataset_loaded():
    """Lazy-load names_dataset on first use."""
    global nd, DATASET_AVAILABLE
    if nd is not None:
        return True
    try:
        from names_dataset import NameDataset
        nd = NameDataset()
        DATASET_AVAILABLE = True
        return True
    except Exception:
        DATASET_AVAILABLE = False
        return False

# ── Lazy-loaded NLP libs (only load when needed) ────────────
nlp = None
skill_extractor = None
SPACY_AVAILABLE = False
SKILLNER_AVAILABLE = False

def _ensure_spacy_loaded():
    """Lazy-load spacy model on first use."""
    global nlp, SPACY_AVAILABLE
    if nlp is not None:
        return True
    try:
        import spacy
        nlp = spacy.load('en_core_web_sm')
        SPACY_AVAILABLE = True
        return True
    except Exception:
        SPACY_AVAILABLE = False
        return False

def _ensure_skillner_loaded():
    """Lazy-load SkillNer and spacy model on first use."""
    global skill_extractor, SKILLNER_AVAILABLE, nlp
    if skill_extractor is not None:
        return True
    try:
        if not _ensure_spacy_loaded():
            return False
        from spacy.matcher import PhraseMatcher
        from skillNer.general_params import SKILL_DB
        from skillNer.skill_extractor_class import SkillExtractor
        skill_extractor = SkillExtractor(nlp, SKILL_DB, PhraseMatcher)
        SKILLNER_AVAILABLE = True
        return True
    except Exception:
        SKILLNER_AVAILABLE = False
        return False


# ══════════════════════════════════════════════════════════════
#  CONFIGURATION  –  edit these paths before running
# ══════════════════════════════════════════════════════════════
RESUME_FOLDER  = r"D:\Project\ATS\ATS Email Parser\Resume"
SKILLS_CSV     = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Skill.csv')
OUTPUT_JSON    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'resume_parsed.json')
VALIDATION_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'validation_report.json')
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

# Skill extraction source:
#   dataset -> SkillNer dataset only
#   csv     -> Skill.csv only
#   auto    -> CSV first, dataset fallback
SKILL_SOURCE = 'auto'

# SkillNer performance tuning
FAST_SKILLNER_MODE = True
SKILLNER_MAX_TEXT_CHARS = 2200

# Logging & Error Handling
ENABLE_VALIDATION = True  # Enable accuracy validation
ENABLE_DETAILED_LOGGING = True  # Log extraction details
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'parser.log')

# Batch performance tuning
DEFAULT_MAX_WORKERS = min(8, (os.cpu_count() or 4))


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

# Hot-path precompiled regex patterns (used once per resume, many resumes in batch)
PHONE_LABEL_RE = re.compile(
    r'(?i)\b(?:mobile|mob|phone|ph|contact|tel|telephone|call|whatsapp)\b\s*[:\-]?\s*([+()0-9][0-9()\s.\-/]{6,25})'
)
PHONE_GENERIC_RE = re.compile(
    r'(?<!\w)(?:\+?\d{1,3}[ \t.\-]?)?(?:\(?\d{2,5}\)?[ \t.\-]?)?\d(?:[\d \t()\.\-]{5,}\d)(?!\w)'
)

EMAIL_DOMAIN_PREFIX_RE = re.compile(
    r"^([a-z0-9-]{1,30}(?:\.[a-z0-9-]{1,30}){0,2}"
    r"\.(?:co\.in|org\.in|ac\.in|gov\.in|com|org|net|edu|gov|in|co|io|ai|info|biz|me|us|uk|ca|au|de|fr|jp|sg))",
    re.I,
)
EMAIL_STRICT_RE = re.compile(r"^[a-z0-9][a-z0-9._%+-]{1,63}@[a-z0-9-]+(?:\.[a-z0-9-]+)+$")
EMAIL_NOISY_PREFIX_RE = re.compile(r"^(?:contact|skills|languages|profile|email|mobile|phone)+", re.I)

GENDER_LABEL_RE = re.compile(r'(?i)\b(?:gender|sex)\b\s*[:\-]?\s*(male|female|m|f)\b')
GENDER_EARLY_MALE_RE = re.compile(r'\b(?:gender|sex)\b[^\n]{0,24}\b(?:male|m)\b', re.I)
GENDER_EARLY_FEMALE_RE = re.compile(r'\b(?:gender|sex)\b[^\n]{0,24}\b(?:female|f)\b', re.I)

ADDRESS_LABEL_RE = re.compile(
    r'(?i)^(?:permanent|current|present|communication|residential)?\s*address\s*[:\-]?\s*(.*)$'
)
ADDRESS_STOP_RE = re.compile(
    r'(?i)^(?:education|skills?|experience|objective|summary|profile|projects?|languages?|'
    r'declaration|reference|hobbies|strengths|certificates?|achievements?|'
    r'bachelor|master|diploma|degree|university|college|institute|school|'
    r'professional\s+experience|technical\s+skills|work\s+experience)\b'
)
ADDRESS_CONTACT_RE = re.compile(r'(?i)(?:@|\b(?:phone|mobile|contact|email|tel|whatsapp)\b|https?://)')
ADDRESS_HINT_RE = re.compile(
    r'(?i)\b(?:road|rd\.?|street|st\.?|lane|ln\.?|nagar|colony|sector|plot|block|'
    r'flat|floor|apartment|society|near|taluka|tehsil|dist|district|city|state|india|'
    r'gujarat|maharashtra|rajasthan|punjab|bihar|kerala|odisha|haryana|pradesh|goa|'
    r'karnataka|postcode|pincode|zip)\b'
)
ADDRESS_NON_RE = re.compile(
    r'(?i)(?:'
    r'\b(?:bachelor|master|diploma|degree|b\.com|b\.a|b\.sc|m\.sc|btech|mtech|b\.tech|m\.tech|b\.e|m\.e|'
    r'university|college|school|institute|cgpa|gpa|graduation|'
    r'certification|training|course|project|client|role|responsibilit\w*|experience|'
    r'java|python|spring|hibernate|oracle|mysql|sql|javascript|html|css|aws|jira|agile|'
    r'scrum|methodology|environment|objective|summary|profile|skills?|expertise|strong|'
    r'knowledge|proficien\w*|skilled|experienced|development|deployment|'
    r'profess\w*|technical|specialized|migrat\w*|implement\w*|architecture|framework|'
    r'built|created|developed|designed|managed|handled|responsible|worked|contributed|'
    r'maintained|monitored|tested|deployed|configur\w*|installed|support\w*|provid\w*|'
    r'ensur\w*|verif\w*|analyzed|coordinated|september|april|june|july|november|'
    r'january|february|march|may|december|october|duration|present|coursework|'
    r'relevant|pvt|ltd|limited|inc|corp|bank|company|corporation|office|factory|'
    r'plant|bhavan|till|birth|date|certified|certif\w*|apmg|use\s+case|uml|modeling|'
    r'model\w*|design\w*)\b|'
    r'\d+\s*-\s*\d+|'  # Match year/number ranges like "2007 - 2009"
    r'(?:to|–)\s*\d{4}|'  # Match "to 2020" or "– 2020"
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|aug)\s*\d{4}' # Match "Jan 2020"
    r')'
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

EMAIL_LOCAL_NON_PERSON_TOKENS = {
    'admin', 'administrator', 'admission', 'career', 'careers', 'contact', 'cv', 'enquiry',
    'enquiries', 'hello', 'help', 'hr', 'hrd', 'info', 'mail', 'naukri', 'no', 'noreply',
    'office', 'recruitment', 'reply', 'resume', 'sales', 'service', 'support', 'team', 'user',
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

    # Improved: Only reject dates that clearly look like MM/DD/YYYY or DD/MM/YYYY
    # Don't reject just because year-like patterns appear scattered in the digits
    # (common in international numbers like +91-9601945583 which has "1960", "1945")
    # or US numbers like +1(940)437-0150 which have "1940"
    
    # Only reject if ALL digits suggest a date format (e.g., 12-digit 01011990)
    if len(digits) == 12 and digits.startswith('0'):
        year_hits = re.findall(r'(?:19|20)\d{2}', digits)
        if year_hits and len(year_hits) >= 2:
            # Multiple year patterns in a 12-digit number starting with 0
            # This is likely a date field like (01/01/1990)
            return None

    return f'+{digits}' if cleaned.startswith('+') else digits


def _extract_doc_with_word_com(path):
    """Fallback .doc text extraction on Windows using installed Microsoft Word."""
    word = None
    doc = None
    try:
        import win32com.client
    except Exception as exc:
        return None, f"pywin32 not available for Word COM fallback: {str(exc)[:120]}"

    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Open(path, ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False)
        text = (doc.Content.Text or '').strip()
        if text:
            return text, None
        return None, "Word COM returned empty text"
    except Exception as exc:
        return None, f"Word COM extraction error: {str(exc)[:140]}"
    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass


def _clean_extracted_text(text):
    """Normalize raw extractor output into stable line-oriented plain text."""
    if not text:
        return ''

    # Normalize newline styles first.
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Convert vertical tab / form feed to line breaks.
    text = text.replace('\x0b', '\n').replace('\x0c', '\n')

    # Strip remaining control chars except tab/newline.
    text = re.sub(r'[\x00-\x08\x0e-\x1f\x7f]', ' ', text)

    # Normalize spacing while preserving line boundaries.
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


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
                    textract_msg = str(textract_err)
                    if 'antiword' in textract_msg.lower():
                        fallback_text, fallback_err = _extract_doc_with_word_com(path)
                        if fallback_text and fallback_text.strip():
                            text = fallback_text
                            error = None
                        else:
                            error = (
                                "textract error: antiword missing for .doc support; "
                                + (fallback_err or "Word COM fallback unavailable")
                            )
                    else:
                        error = f"textract error: {textract_msg[:100]}"
            else:
                fallback_text, fallback_err = _extract_doc_with_word_com(path)
                if fallback_text and fallback_text.strip():
                    text = fallback_text
                    error = None
                else:
                    error = (
                        "textract not installed (pip install textract for .doc support); "
                        + (fallback_err or "Word COM fallback unavailable")
                    )
        
        else:
            error = f"Unsupported file extension: {ext}"
        
        if text:
            text = _clean_extracted_text(text)

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
    def _case_word(word):
        alpha = re.sub(r'[^A-Za-z]', '', word)
        if not alpha:
            return word

        # Preserve initials formatting like K., .K., A.B.
        if len(alpha) <= 2 and '.' in word:
            return re.sub(r'[a-z]', lambda m: m.group(0).upper(), word)

        chars = list(word)
        seen_alpha = False
        for i, ch in enumerate(chars):
            if not ch.isalpha():
                continue
            if not seen_alpha:
                chars[i] = ch.upper()
                seen_alpha = True
            else:
                chars[i] = ch.lower()
        return ''.join(chars)

    return ' '.join(_case_word(w) for w in s.split())


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
    # Normalize dotted initials such as ".k." -> ".K."
    c = re.sub(r'\b([a-z])(?=\.)', lambda m: m.group(1).upper(), c)
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
    def _looks_name_cased(word):
        alpha = re.sub(r'[^A-Za-z]', '', word)
        if not alpha:
            return False
        # Allow initials like K / K. / .K.
        if len(alpha) == 1:
            return True
        return alpha[0].isupper()

    capped = sum(1 for w in words if _looks_name_cased(w))
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
        if len(alpha) == 1:
            # Accept initials regardless of case if punctuation/initial style is present.
            if w.endswith('.') or w.isupper() or w.startswith('.'):
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
            r = ND_TOKEN_CACHE.get(clean)
            if r is None:
                result = nd.search(clean)
                with _ND_CACHE_LOCK:
                    ND_TOKEN_CACHE[clean] = result
                r = result
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


def _dataset_first_or_last_hit(token):
    token = (token or '').strip().lower()
    if not token:
        return False, False
    cached = ND_TOKEN_CACHE.get(token)
    if cached is not None:
        if isinstance(cached, tuple) and len(cached) == 2:
            return cached
        return bool(cached.get('first_name')), bool(cached.get('last_name'))
    if not DATASET_AVAILABLE:
        return False, False
    try:
        result = nd.search(token)
        hit = bool(result.get('first_name')), bool(result.get('last_name'))
        with _ND_CACHE_LOCK:
            ND_TOKEN_CACHE[token] = hit
        return hit
    except Exception:
        return False, False


def _token_looks_like_first_name(token):
    t = re.sub(r'[^a-z]', '', token.lower())
    if len(t) < 3:
        return False
    if t in COMMON_MALE_FIRST_NAMES or t in COMMON_FEMALE_FIRST_NAMES:
        return True
    first_hit, _ = _dataset_first_or_last_hit(t)
    return first_hit


def _token_looks_like_surname(token):
    t = re.sub(r'[^a-z]', '', token.lower())
    if len(t) < 2:
        return False
    if t in COMMON_SURNAMES:
        return True
    _, last_hit = _dataset_first_or_last_hit(t)
    return last_hit


def _email_local_looks_like_name(local, alpha_chunks):
    if not alpha_chunks:
        return False

    if any(part in EMAIL_LOCAL_NON_PERSON_TOKENS for part in alpha_chunks):
        return False

    if any(part in BLACKLIST or part in NON_NAME_WORDS or part in COMPANY_HINTS for part in alpha_chunks):
        return False

    compact = re.sub(r'[^a-z0-9]', '', local.lower())
    if compact:
        digit_ratio = sum(ch.isdigit() for ch in compact) / len(compact)
        if len(compact) >= 5 and digit_ratio > 0.35:
            return False

    if len(alpha_chunks) >= 2:
        first, second = alpha_chunks[-2], alpha_chunks[-1]
        if len(first) < 3 or len(second) < 2:
            return False
        if _token_looks_like_first_name(first) and len(second) >= 3:
            return True
        if _token_looks_like_first_name(second) and len(first) >= 3:
            return True
        if _token_looks_like_first_name(first) and _token_looks_like_surname(second):
            return True
        return False

    single = alpha_chunks[-1]
    if len(single) < 6:
        return False

    if _token_looks_like_first_name(single):
        return True

    for sur in sorted(COMMON_SURNAMES, key=len, reverse=True):
        if single.endswith(sur) and len(single) > len(sur) + 2:
            first_part = single[:-len(sur)]
            if _token_looks_like_first_name(first_part):
                return True

    return False


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

        # Email username fallback is intentionally conservative to avoid
        # false names like admin/support/hr/team style usernames.
        if not _email_local_looks_like_name(local, alpha_chunks):
            continue

        if len(alpha_chunks) >= 2:
            c = title_case(' '.join(alpha_chunks[-2:]))
            if accept(c, strict=False):
                return c

        if alpha_chunks:
            single = alpha_chunks[-1]
            if len(single) >= 3 and _token_looks_like_first_name(single):
                c = title_case(single)
                if accept(c, strict=False, allow_single=True):
                    return c
            if len(single) >= 6:
                for sur in sorted(COMMON_SURNAMES, key=len, reverse=True):
                    if single.endswith(sur) and len(single) > len(sur) + 2:
                        first_part = single[:-len(sur)]
                        if not _token_looks_like_first_name(first_part):
                            continue
                        c = title_case(first_part + ' ' + sur)
                        if accept(c, strict=False):
                            return c
    return None


def _resolve_process_folder():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--folder', dest='folder', default='')
    parser.add_argument('--no-validation', action='store_true')
    parser.add_argument('--skill-source', dest='skill_source', default=SKILL_SOURCE)
    parser.add_argument('--workers', dest='workers', type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument('--limit', dest='limit', type=int, default=0)
    parser.add_argument('--random-order', action='store_true')
    parser.add_argument('--seed', dest='seed', type=int, default=42)
    parser.add_argument('--fast-response', dest='fast_response', action='store_true')
    parser.add_argument('--full-accuracy', dest='fast_response', action='store_false')
    parser.set_defaults(fast_response=False)
    args, _ = parser.parse_known_args()

    cli_folder = (args.folder or '').strip().strip('"')

    # Single-folder mode:
    # 1) Use --folder if provided.
    # 2) Otherwise use RESUME_FOLDER only.
    chosen_folder = cli_folder or RESUME_FOLDER
    source = (args.skill_source or SKILL_SOURCE).strip().lower()
    if source not in {'dataset', 'csv', 'auto'}:
        source = SKILL_SOURCE
    workers = max(1, int(args.workers or 1))
    limit = max(0, int(args.limit or 0))
    return (
        chosen_folder,
        args.no_validation,
        source,
        workers,
        limit,
        bool(args.random_order),
        int(args.seed),
        bool(args.fast_response),
    )


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

    for seg_idx, seg in enumerate(segments):
        for m in PHONE_LABEL_RE.finditer(seg):
            raw = m.group(1)
            number = _normalize_phone_candidate(raw)
            if not number:
                continue
            digits_len = len(re.sub(r'\D', '', number))
            len_pref = 0 if 10 <= digits_len <= 12 else (1 if digits_len == 13 else 2)
            candidates.append((8, len_pref, digits_len, seg_idx, m.start(), number))

        for m in PHONE_GENERIC_RE.finditer(seg):
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
            local = EMAIL_NOISY_PREFIX_RE.sub("", local)
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
        dm = EMAIL_DOMAIN_PREFIX_RE.search(domain_head)
        if not dm:
            domain_head = ''.join(right_tokens[:8]).strip('.')
            dm = EMAIL_DOMAIN_PREFIX_RE.search(domain_head)
        if not dm:
            return None
        domain = dm.group(1).lower()
        email = f"{local.lower()}@{domain}"
        if not EMAIL_STRICT_RE.match(email):
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


def _infer_gender_from_text_context(text):
    """Infer gender from common self-identification cues in resume text."""
    if not text:
        return None

    t = normalize_compact_text(text).lower()
    if not t:
        return None

    # Strong direct statements.
    if re.search(r'\b(?:i\s*am|im|i\'m)\s+male\b', t):
        return 'Male'
    if re.search(r'\b(?:i\s*am|im|i\'m)\s+female\b', t):
        return 'Female'

    male_score = 0
    female_score = 0

    # Honorific/title cues.
    male_score += len(re.findall(r'\b(?:mr\.?|mister|sir|shri)\b', t)) * 2
    female_score += len(re.findall(r'\b(?:mrs\.?|ms\.?|miss|madam|smt)\b', t)) * 2

    # Pronoun cues in first part of resume (avoid overfitting on long docs).
    head = t[:3500]
    male_score += len(re.findall(r'\b(?:he|him|his)\b', head))
    female_score += len(re.findall(r'\b(?:she|her|hers)\b', head))

    if male_score >= 2 and male_score >= female_score + 1:
        return 'Male'
    if female_score >= 2 and female_score >= male_score + 1:
        return 'Female'

    return None


def extract_gender(text, name=None):
    if not text:
        return _infer_gender_from_name(name)

    t = normalize_compact_text(text)
    lines = [re.sub(r'\s+', ' ', line).strip() for line in t.splitlines() if line.strip()]

    for line in lines[:80]:
        m = GENDER_LABEL_RE.search(line)
        if not m:
            continue
        raw = m.group(1).lower()
        if raw in {'male', 'm'}:
            return 'Male'
        if raw in {'female', 'f'}:
            return 'Female'

    # Fallback: gender token near gender/sex labels.
    early = '\n'.join(lines[:35]).lower()
    if GENDER_EARLY_MALE_RE.search(early):
        return 'Male'
    if GENDER_EARLY_FEMALE_RE.search(early):
        return 'Female'

    # Additional fallback: use self-identification cues from resume narrative.
    inferred_from_text = _infer_gender_from_text_context(t)
    if inferred_from_text:
        return inferred_from_text

    # Last fallback: infer from the extracted candidate name.
    return _infer_gender_from_name(name)


def extract_address(text):
    if not text:
        return None

    t = normalize_compact_text(text)
    lines = [re.sub(r'\s+', ' ', line).strip(' ,;:-') for line in t.splitlines() if line.strip()]
    if not lines:
        return None

    def clean_address(value):
        value = re.sub(r'\s+', ' ', value).strip(' ,;:-')
        if len(value) < 8:
            return None
        if len(value) > 220:
            return None
        if len(value.split()) > 35:
            return None
        if value.count(',') > 6:
            return None
        if ADDRESS_CONTACT_RE.search(value):
            return None
        
        # *** CRITICAL: Reject employment date patterns BEFORE other checks ***
        # Match "August 2007", "2007 to 2009", "Aug 2020 - Sep 2021", etc.
        if re.search(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)[.,\-\s]+\d{4}', value, re.I):
            return None
        # Match patterns like "2007 to 2009", "2020 - present", "August 2007 to September 2009", etc.
        if re.search(r'(?:\d{4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)\s+\d{4})\s*(?:to|–|-|–)\s*(?:\d{4}|present|till|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december))', value, re.I):
            return None
        
        # Count how many non-address keywords appear
        bad_words = len(re.findall(ADDRESS_NON_RE, value))
        if bad_words >= 1:
            return None
        
        # Address should have strong location indicators
        digit_hits = len(re.findall(r'\d', value))
        hint_hits = len(ADDRESS_HINT_RE.findall(value))
        # Require either: strong address hints, OR (digit + comma), OR (digit + postal zip code pattern)
        has_postal = bool(re.search(r'\b\d{3,6}\b', value))
        if hint_hits == 0 and not has_postal:
            return None
        return value

    # First preference: explicit address label.
    for i, line in enumerate(lines[:80]):
        m = ADDRESS_LABEL_RE.match(line)
        if not m:
            continue

        parts = []
        first = m.group(1).strip()
        if first and not ADDRESS_STOP_RE.match(first) and not ADDRESS_CONTACT_RE.search(first):
            bad_first = len(re.findall(ADDRESS_NON_RE, first))
            if bad_first == 0:
                # Also reject if contains employment date patterns
                if not re.search(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)\s+\d{4}', first, re.I):
                    if not re.search(r'\d{4}\s*(?:to|–|-)\s*(?:\d{4}|present)', first, re.I):
                        parts.append(first)

        # Capture a few immediate continuation lines.
        for j in range(i + 1, min(i + 4, len(lines))):
            nxt = lines[j]
            if ADDRESS_STOP_RE.match(nxt):
                break
            if ADDRESS_CONTACT_RE.search(nxt):
                break
            bad_nxt = len(re.findall(ADDRESS_NON_RE, nxt))
            if bad_nxt >= 1:
                break
            # Reject if this line has employment dates
            if re.search(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)\s+\d{4}', nxt, re.I):
                break
            if re.search(r'\d{4}\s*(?:to|–|-)\s*(?:\d{4}|present)', nxt, re.I):
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
        if ADDRESS_STOP_RE.match(line) or ADDRESS_CONTACT_RE.search(line):
            continue
        
        # *** REJECT: Employment/work dates immediately ***
        if re.search(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)\s+\d{4}', line, re.I):
            continue
        if re.search(r'\d{4}\s*(?:to|–|-)\s*(?:\d{4}|present)', line, re.I):
            continue
        
        # Count problematic keywords - be VERY strict
        bad_count = len(re.findall(ADDRESS_NON_RE, line))
        if bad_count >= 1:
            continue
        
        score = 0
        digit_hits = len(re.findall(r'\d', line))
        if digit_hits > 0:
            score += 3
        if ',' in line:
            score += 1
        hint_hits = len(ADDRESS_HINT_RE.findall(line))
        if hint_hits > 0:
            score += 5
        if 2 <= len(line.split()) <= 25:
            score += 1
        
        # Require meaningful address patterns
        has_postal = bool(re.search(r'\b\d{3,6}\b', line))
        if has_postal:
            score += 2
        
        if score < 6:
            continue

        parts = [line]
        for j in range(i + 1, min(i + 3, len(lines))):
            nxt = lines[j]
            if ADDRESS_STOP_RE.match(nxt) or ADDRESS_CONTACT_RE.search(nxt):
                break
            bad_nxt = len(re.findall(ADDRESS_NON_RE, nxt))
            if bad_nxt >= 1:
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


# Generic terms that often appear in resume prose and should not be emitted as skills.
GENERIC_SKILL_STOPWORDS = {
    'ability', 'abilities', 'analysis', 'analytical', 'application', 'applications',
    'assurance', 'background', 'batch', 'capability', 'capabilities', 'communication',
    'compliance', 'control', 'coordination', 'creative', 'data', 'decision', 'delivery',
    'design', 'development', 'documentation', 'environment', 'evaluation', 'execution',
    'experience', 'framework', 'frameworks', 'functional', 'implementation', 'improvement',
    'knowledge', 'leadership', 'learning', 'maintenance', 'management', 'methodology',
    'methods', 'model', 'modeling', 'modelling', 'monitoring', 'operations', 'optimization',
    'organizing', 'performance', 'planning', 'problem', 'process', 'processes', 'production',
    'professional', 'project', 'projects', 'quality', 'reporting', 'research', 'responsibility',
    'responsibilities', 'safety', 'skills', 'solution', 'solutions', 'strategy', 'support',
    'systems', 'technical', 'technology', 'testing', 'training', 'troubleshooting', 'work',
    'certification', 'certifications',
    'manufacturing', 'materials', 'balance', 'routing',
}

# Keep essential one-word technical skills even when generic filtering is active.
STRONG_SINGLE_WORD_SKILLS = {
    'aws', 'azure', 'c', 'c#', 'c++', 'cad', 'css', 'excel', 'git', 'go', 'html', 'java',
    'javascript', 'jira', 'json', 'kafka', 'kubernetes', 'linux', 'matlab', 'mongodb',
    'mysql', 'oracle', 'php', 'postgresql', 'powerbi', 'powershell', 'python', 'sap',
    'selenium', 'snowflake', 'sql', 'tableau', 'terraform', 'typescript', 'unix', 'xml', 'yaml',
}

SKILL_SECTION_HEADER_RE = re.compile(
    r'(?i)\b('
    r'technical\s+skills?|core\s+skills?|key\s+skills?|skills?\s*&\s*technolog(?:y|ies)|'
    r'skills?\s*&\s*tools?|core\s+competenc(?:y|ies)|areas?\s+of\s+(?:expertise|excellence)|'
    r'technical\s+specifications?|competencies?|technolog(?:y|ies)|tools?|software|'
    r'expertise|proficien(?:cy|cies)|frameworks?|languages?|certifications?'
    r')\b'
)

NON_SKILL_SECTION_HEADER_RE = re.compile(
    r'(?i)^\s*(?:'
    r'professional\s+summary|summary|profile|career\s+objective|objective|'
    r'work\s+experience|professional\s+experience|experience|employment\s+history|'
    r'education|academic\s+qualification(?:s)?|projects?|internships?|'
    r'personal\s+details?|contact|declaration|references?|hobbies|interests?|'
    r'achievements?|awards?|publications?'
    r')\b'
)


def _is_weak_generic_skill(skill):
    """Return True when a skill token is too generic for reliable extraction."""
    if not skill:
        return True

    normalized = normalize_skill_key(skill)
    if not normalized:
        return True

    if normalized in STRONG_SINGLE_WORD_SKILLS:
        return False

    if normalized in GENERIC_SKILL_STOPWORDS:
        return True

    words = re.findall(r'[A-Za-z0-9+#]+', skill.lower())
    if not words:
        return True

    # Reject fragmented tokens like "e e" or "t t" from OCR/NER noise.
    if len(words) >= 2 and all(len(w) == 1 for w in words):
        return True

    if normalized in {'com', 'iam'}:
        return True

    # Most false positives are single generic words from resume narrative text.
    if len(words) == 1:
        w = words[0]
        if w in STRONG_SINGLE_WORD_SKILLS:
            return False
        if w in GENERIC_SKILL_STOPWORDS or w in BLACKLIST:
            return True
        if len(w) <= 2:
            return True

    return False


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
        print(f"[!] Skills CSV not found: {csv_path}")
        return skills

    with open(csv_path, mode='r', encoding='utf-8', errors='ignore', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Detect format: does it have our generated columns?
        has_skill_col = 'skill' in [fn.strip().lower() for fn in fieldnames]
        has_norm_col  = 'normalized_skill' in [fn.strip().lower() for fn in fieldnames]
        has_weight_col = 'resume_match_weight' in [fn.strip().lower() for fn in fieldnames]

        for row in reader:
            if has_skill_col:
                # Our generated CSV: use both 'skill' (raw) and 'normalized_skill' (display)
                raw_skill  = row.get('skill', '').strip()
                norm_skill = row.get('normalized_skill', '').strip() if has_norm_col else ''
                try:
                    weight = int((row.get('resume_match_weight', '0') or '0').strip()) if has_weight_col else 0
                except Exception:
                    weight = 0

                for candidate in filter(None, [raw_skill, norm_skill]):
                    candidate = re.sub(r'\s+', ' ', candidate).strip(" \t\r\n\"'")
                    if not is_valid_skill(candidate):
                        if candidate:
                            invalid_count += 1
                        continue
                    # Ignore low-weight one-word generic tokens from broad CSV inventories.
                    words = re.findall(r'[A-Za-z0-9+#]+', candidate.lower())
                    if has_weight_col and weight <= 2 and len(words) == 1:
                        w = words[0]
                        if w not in STRONG_SINGLE_WORD_SKILLS and len(w) <= 12:
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
        print(f"[!] Filtered out {invalid_count} invalid skill entries from CSV")

    return skills


def build_skill_matchers(skills_list):
    """Precompile skill regex patterns once for faster CSV matching across many resumes."""
    matchers = []
    seen = set()
    for skill in skills_list or []:
        if not skill or _is_weak_generic_skill(skill):
            continue
        key = normalize_skill_key(skill)
        if not key or key in seen:
            continue
        escaped = re.escape(skill.strip()).replace(r'\ ', r'\s+')
        pattern = re.compile(rf'(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])', re.IGNORECASE)
        seen.add(key)
        matchers.append((key, skill, pattern))
    return matchers


INFERRED_SKILL_RULES = [
    (r'\breact(?:\.?\s*js)?\b', 'ReactJS'),
    (r'\bnode(?:\.?\s*js)?\b', 'NodeJS'),
    (r'\bbootstrap\b', 'Bootstrap'),
    (r'\bcss(?:3)?\b', 'CSS'),
    (r'\bvisual\s+studio\s+code\b|\bvs\.?\s*code\b|\bvscode\b', 'Visual Studio Code'),
    (r'\bpy\s*charm\b|\bpycharm\b', 'PyCharm'),
    (r'\bms\.?\s*word\b|\bmicrosoft\s+word\b', 'MS Word'),
    (r'\bextrusion\b', 'Extrusion'),
    (r'\binjection\s*mou?ld(?:ing)?\b', 'Injection Molding'),
    (r'\bplastic\s+processing\b', 'Plastic Processing'),
    (r'\bquality\s*assurance\b|\bq\.?\s*a\.?\b', 'Quality Assurance'),
    (r'\bquality\s*control\b|\bq\.?\s*c\.?\b', 'Quality Control'),
    (r'\binternal\s+auditor\b|\bauditing\b', 'Internal Auditing'),
    (r'\binspection\b', 'Inspection'),
    (r'\bprocess\s+parameter\b', 'Process Parameter Control'),
    (r'\btroubleshooting\b', 'Troubleshooting'),
    (r'\bprocess\s+improvement\b|\bkaizen\b', 'Process Improvement'),
    (r'\bproduction\s+schedul(?:e|ing)\b', 'Production Scheduling'),
    (r'\bmanpower\s+planning\b', 'Manpower Planning'),
    (r'\braw\s+material\b', 'Raw Material Handling'),
    (r'\blaboratory\s+testing\b|\bmaterial\s+testing\b', 'Material Testing'),
    (r'\bmfi\b|\bmelt\s+flow\s+index\b', 'MFI Testing'),
    (r'\btensile\s+strength\b', 'Tensile Testing'),
    (r'\bimpact\b', 'Impact Testing'),
    (r'\bhydro\s*pressure\b', 'Hydro Pressure Testing'),
    (r'\bdensity\b', 'Density Testing'),
    (r'\biso\s*9001(?::?2015)?\b', 'ISO 9001'),
    (r'\biso\s*14001(?::?2015)?\b', 'ISO 14001'),
    (r'\biso\s*45001(?::?2018)?\b|\bohsas\s*18001(?::?2007)?\b', 'ISO 45001'),
    (r'\bhdpe\b', 'HDPE'),
    (r'\bupvc\b', 'UPVC'),
    (r'\bcpvc\b', 'CPVC'),
    (r'\bppr\b', 'PPR'),
    (r'\bdrip\s+irrigation\b', 'Drip Irrigation Systems'),
    (r'\bcgmp\b|\bgmp\b', 'cGMP'),
    (r'\bprocess\s+validation\b', 'Process Validation'),
    (r'\btablet\s+manufacturing\b', 'Tablet Manufacturing'),
    (r'\bwet\s+granulation\b', 'Wet Granulation'),
    (r'\bdry\s+granulation\b', 'Dry Granulation'),
    (r'\bcompression\b', 'Compression'),
    (r'\bcoating\b', 'Coating'),
    (r'\boee\b|\boverall\s+equipment\s+efficien(?:cy|t)\b', 'OEE (Overall Equipment Efficiency)'),
    (r'\bequipment\s+calibration\b|\bcalibration\b', 'Equipment Calibration'),
    (r'\bequipment\s+qualification\b', 'Equipment Qualification'),
    (r'\bfda\b', 'FDA Compliance'),
    (r'\bregulatory\s+compliance\b', 'Regulatory Compliance'),
    (r'\bsop\b', 'SOP Documentation'),
    (r'\bbmr\b|\bmfr\b|\bbatch\s+manufacturing\b', 'Batch Manufacturing (BMR/MFR)'),
    (r'\bquality\s+audit\b|\baudits?\b', 'Quality Audits'),
    (r'\bchange\s+control\b', 'Change Control'),
    (r'\bdeviation\s+management\b|\bdeviation\b', 'Deviation Management'),
    (r'\bsap\b.*\bproduction\b|\bproduction\b.*\bsap\b', 'SAP Production Module'),
    (r'\bexcel\b', 'Excel'),
    (r'\bword\b', 'MS Word'),
    (r'\bpower\s*point\b|\bpowerpoint\b', 'PowerPoint'),
]


def infer_context_skills(text, existing_skills=None):
    """Infer technical skills from experience/project text when explicit skill sections are weak."""
    if not text:
        return []

    inferred = []
    seen = {normalize_skill_key(s) for s in (existing_skills or []) if s}
    haystack = normalize_compact_text(text).lower()

    for pattern, skill in INFERRED_SKILL_RULES:
        if re.search(pattern, haystack, re.I):
            key = normalize_skill_key(skill)
            if key and key not in seen and not _is_weak_generic_skill(skill):
                seen.add(key)
                inferred.append(skill)

    # Role-based fallback inference
    if re.search(r'\bquality\s+supervisor\b|\bqa\s+engineer\b|\bquality\s+engineer\b', haystack):
        for skill in ['Quality Assurance', 'Inspection', 'Quality Control']:
            key = normalize_skill_key(skill)
            if key not in seen:
                seen.add(key)
                inferred.append(skill)

    if re.search(r'\bproduction\b', haystack):
        for skill in ['Production Planning', 'Process Control']:
            key = normalize_skill_key(skill)
            if key not in seen:
                seen.add(key)
                inferred.append(skill)

    return inferred


def cleanup_extracted_skills(text, extracted_skills):
    """Normalize, deduplicate, remove weak tokens, and prefer multi-word ATS skills."""
    if not extracted_skills:
        return []

    alias_map = {
        'gmp': 'cGMP',
        'cgmp': 'cGMP',
        'react': 'ReactJS',
        'reactjs': 'ReactJS',
        'node': 'NodeJS',
        'nodejs': 'NodeJS',
        'css3': 'CSS',
        'vscode': 'Visual Studio Code',
        'visualstudiocode': 'Visual Studio Code',
        'pycharm': 'PyCharm',
        'word': 'MS Word',
        'msword': 'MS Word',
        'microsoftword': 'MS Word',
        'processvalidation': 'Process Validation',
        'tabletmanufacturing': 'Tablet Manufacturing',
        'wetgranulation': 'Wet Granulation',
        'drygranulation': 'Dry Granulation',
        'compression': 'Compression',
        'coating': 'Coating',
        'equipmentcalibration': 'Equipment Calibration',
        'equipmentqualification': 'Equipment Qualification',
        'sop': 'SOP Documentation',
        'bmr': 'Batch Manufacturing (BMR/MFR)',
        'mfr': 'Batch Manufacturing (BMR/MFR)',
        'oee': 'OEE (Overall Equipment Efficiency)',
    }
    weak_exact = {'manufacturing', 'materials', 'balance', 'routing', 'budgeting', 'pharmacy', 'portfolio'}

    normalized = []
    seen = set()

    for raw in extracted_skills:
        if not raw:
            continue
        key = normalize_skill_key(raw)
        if not key:
            continue

        skill = alias_map.get(key, raw)
        skill_key = normalize_skill_key(skill)
        if not skill_key or skill_key in seen:
            continue

        if skill_key in weak_exact:
            continue
        if _is_weak_generic_skill(skill):
            continue

        seen.add(skill_key)
        normalized.append(skill)

    # Prefer multi-word skills over single generic tokens.
    token_sets = [
        set(re.findall(r'[a-z0-9+#]+', s.lower()))
        for s in normalized
        if len(re.findall(r'[a-z0-9+#]+', s.lower())) > 1
    ]

    final_skills = []
    for skill in normalized:
        words = re.findall(r'[a-z0-9+#]+', skill.lower())
        if len(words) == 1:
            token = words[0]
            if any(token in ts for ts in token_sets):
                continue
        final_skills.append(skill)

    return final_skills


def extract_skills_from_resume(text, skills_list, compiled_skill_matchers=None):
    """
    Return every skill from skills_list that appears in the resume text.
    Uses whole-word / alphanumeric-boundary matching (case-insensitive).
    """
    if not text or not skills_list:
        return []

    section_text, has_section = _extract_skill_section_text(text)
    # Fallback to compact full text when resume has no explicit skills section.
    normalized_text = section_text if has_section else normalize_compact_text(text)
    # Make common tech variants equivalent for matching (Node.JS -> NodeJS, VS Code -> VSCode).
    normalized_text = re.sub(r'(?i)\bnode\s*[\./-]?\s*js\b', 'nodejs', normalized_text)
    normalized_text = re.sub(r'(?i)\breact\s*[\./-]?\s*js\b', 'reactjs', normalized_text)
    normalized_text = re.sub(r'(?i)\bvs\s*code\b', 'vscode', normalized_text)
    normalized_text = re.sub(r'(?i)\bms\.?\s*word\b|\bmicrosoft\s+word\b', 'msword', normalized_text)
    matched_skills = []
    seen = set()

    if compiled_skill_matchers:
        for key, skill, pattern in compiled_skill_matchers:
            if key in seen:
                continue
            if pattern.search(normalized_text):
                seen.add(key)
                matched_skills.append(skill)
    else:
        for skill in skills_list:
            if not skill:
                continue
            if _is_weak_generic_skill(skill):
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

    # Remove single-token skills that are subsets of a longer matched phrase.
    multi_token_sets = [
        frozenset(re.findall(r'[a-z0-9+#]+', s.lower()))
        for s in matched_skills
        if len(re.findall(r'[a-z0-9+#]+', s.lower())) > 1
    ]
    filtered = []
    for skill in matched_skills:
        tokens = re.findall(r'[a-z0-9+#]+', skill.lower())
        if len(tokens) <= 1:
            tok_set = frozenset(tokens)
            if any(tok_set.issubset(ms) for ms in multi_token_sets):
                continue
        filtered.append(skill)
    return filtered


def _extract_skill_text_from_skillner_item(item):
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return None

    for key in ('doc_node_value', 'skill_name', 'skill', 'name', 'matched_text'):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    doc_node = item.get('doc_node')
    if isinstance(doc_node, str) and doc_node.strip():
        return doc_node.strip()

    return None


def _normalize_header_candidate(line):
    """Normalize extracted PDF lines before section-header checks."""
    if not line:
        return ''
    line = re.sub(r'\s+', ' ', line).strip()
    line = re.sub(r'^[\W_]+', '', line)
    line = re.sub(r'[\W_]+$', '', line)
    return line.strip()


def _is_probable_skill_header(line):
    """Heuristic: detect true skill section headers, avoid body-line false positives."""
    candidate = _normalize_header_candidate(line)
    if not candidate:
        return False

    lower = candidate.lower()
    if not SKILL_SECTION_HEADER_RE.search(lower):
        return False

    # Ignore noisy lines that usually come from body prose or contact blocks.
    if re.search(r'[@]|https?://|\b(?:email|phone|mobile|contact)\b', lower):
        return False

    strong_header_phrases = re.compile(
        r'(?i)\b(?:'
        r'technical\s+skills?|skills?\s*&\s*technolog(?:y|ies)|skills?\s*&\s*tools?|'
        r'core\s+competenc(?:y|ies)|areas?\s+of\s+(?:expertise|excellence)|'
        r'technical\s+specifications?'
        r')\b'
    )
    if strong_header_phrases.search(lower):
        return True

    words = re.findall(r'[A-Za-z0-9+#&/.-]+', candidate)
    if len(words) <= 8 and (candidate.endswith(':') or candidate.isupper()):
        return True

    # Accept short title-like headers such as "Skills" or "Technologies".
    if len(words) <= 4:
        return True

    return False


def _is_probable_non_skill_header(line):
    """Heuristic: detect section transitions out of skills areas."""
    candidate = _normalize_header_candidate(line)
    if not candidate:
        return False

    lower = candidate.lower()
    if _is_probable_skill_header(candidate):
        return False

    if NON_SKILL_SECTION_HEADER_RE.search(lower):
        words = re.findall(r'[A-Za-z0-9+#&/.-]+', candidate)
        return len(words) <= 10 or candidate.endswith(':')

    return False


def _extract_skill_section_text(text):
    """Extract only skill-section content when a skills header exists."""
    if not text:
        return '', False

    normalized = normalize_compact_text(text)
    lines = [re.sub(r'\s+', ' ', ln).strip() for ln in normalized.splitlines() if ln.strip()]
    if not lines:
        return '', False

    selected = []
    in_skill_block = False
    block_budget = 0
    found_header = False
    max_lines_per_block = 140

    for line in lines:
        lower = line.lower()

        if _is_probable_skill_header(line):
            in_skill_block = True
            found_header = True
            block_budget = max_lines_per_block
            selected.append(line)
            continue

        if in_skill_block:
            if _is_probable_non_skill_header(line):
                in_skill_block = False
                block_budget = 0
                continue

            if re.search(r'[@]|https?://|\b(?:phone|mobile|email|contact)\b', lower):
                continue

            selected.append(line)
            block_budget -= 1
            if block_budget <= 0:
                in_skill_block = False

    return ('\n'.join(selected), found_header and len(selected) > 1)


def _build_fast_skillner_text(text):
    """Return a reduced text focused on skill-heavy sections for faster SkillNer runs."""
    if not text:
        return ''

    section_text, has_section = _extract_skill_section_text(text)
    if has_section:
        return section_text[:SKILLNER_MAX_TEXT_CHARS]

    normalized = normalize_compact_text(text)

    # Fallback: keep top part if no explicit skill section was detected.
    return normalized[:SKILLNER_MAX_TEXT_CHARS]


def extract_skills_from_dataset(text):
    """Extract skills using SkillNer dataset pipeline."""
    if not text:
        return []
    
    # Lazy-load SkillNer on first use
    if not _ensure_skillner_loaded():
        return []

    # Use section text when available; otherwise use reduced full text fallback.
    section_text, has_section = _extract_skill_section_text(text)
    text_for_skillner = section_text if has_section else _build_fast_skillner_text(text)
    if not text_for_skillner:
        return []

    try:
        result = skill_extractor.annotate(text_for_skillner)
    except Exception:
        return []

    results = result.get('results', {}) if isinstance(result, dict) else {}
    candidates = []
    seen = set()

    for bucket in ('full_matches', 'ngram_scored'):
        for item in results.get(bucket, []) or []:
            skill_text = _extract_skill_text_from_skillner_item(item)
            if not skill_text:
                continue
            skill_text = re.sub(r'\s+', ' ', skill_text).strip(" \t\r\n\"'")
            if not skill_text:
                continue
            if _is_weak_generic_skill(skill_text):
                continue
            key = normalize_skill_key(skill_text)
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append(skill_text)

    return candidates


def _extract_resume_record(fname, process_folder, skill_source, skills_list, compiled_skill_matchers=None, fast_response=False):
    """Extract all fields for a single resume file."""
    path = os.path.join(process_folder, fname)
    try:
        text = extract_text(path)
        name = extract_name(text)
        contact_number = extract_contact_number(text)
        email = extract_email_from_resume(text)
        if fast_response:
            gender = None
            address = None
        else:
            gender = extract_gender(text, name=name)
            address = extract_address(text)

        if skill_source == 'dataset':
            matched_skills = extract_skills_from_dataset(text)
        elif skill_source == 'csv':
            matched_skills = extract_skills_from_resume(text, skills_list, compiled_skill_matchers)
        else:
            # CSV matching is much faster; use it first, then fallback to dataset extraction.
            matched_skills = extract_skills_from_resume(text, skills_list, compiled_skill_matchers)
            if not matched_skills:
                matched_skills = extract_skills_from_dataset(text)

        inferred_skills = infer_context_skills(text, matched_skills)
        if inferred_skills:
            matched_skills.extend(inferred_skills)

        matched_skills = cleanup_extracted_skills(text, matched_skills)

        return {
            'file': fname,
            'name': name,
            'contact_number': contact_number,
            'email': email,
            'gender': gender,
            'address': address,
            'skills': matched_skills,
        }
    except Exception as exc:
        return {
            'file': fname,
            'name': None,
            'contact_number': None,
            'email': None,
            'gender': None,
            'address': None,
            'skills': [],
            'error': str(exc),
        }


# ══════════════════════════════════════════════════════════════
#  BATCH RUNNER
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#  BATCH RUNNER with Validation & Logging
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':

    (
        PROCESS_FOLDER,
        disable_validation,
        skill_source,
        max_workers,
        max_files,
        random_order,
        random_seed,
        fast_response_mode,
    ) = _resolve_process_folder()
    runtime_validation_enabled = ENABLE_VALIDATION and not disable_validation
    if fast_response_mode:
        runtime_validation_enabled = False

    # ── Import validation module ──────────────────────────────
    try:
        if runtime_validation_enabled:
            from validation import ResumeValidator, print_validation_report
            validator = ResumeValidator()
        else:
            validator = None
    except ImportError:
        print("[!] validation module not found. Running without accuracy checking.")
        validator = None
    
    # ── Setup logging ─────────────────────────────────────────
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log_messages = []
    
    _stdout_buffer = getattr(sys.stdout, 'buffer', None)
    def log_message(msg):
        try:
            print(msg)
        except UnicodeEncodeError:
            _stdout_buffer.write(msg.encode('utf-8') + b'\n')
        log_messages.append(msg)
    
    # ── Load skills (optional CSV path) ───────────────────────
    skills_list = []
    if skill_source in {'csv', 'auto'}:
        skills_list = load_skills_from_csv(SKILLS_CSV)
    compiled_skill_matchers = build_skill_matchers(skills_list)

    # Pre-load heavy models only when they are likely to be used.
    if skill_source == 'dataset' or (skill_source == 'auto' and not compiled_skill_matchers):
        _ensure_skillner_loaded()
    if not fast_response_mode:
        _ensure_names_dataset_loaded()

    if fast_response_mode and skill_source == 'auto' and compiled_skill_matchers:
        skill_source = 'csv'
    results = []

    # ── Discover resume files ─────────────────────────────────
    if not os.path.isdir(PROCESS_FOLDER):
        log_message(f"❌ Resume folder not found: {PROCESS_FOLDER}")
        raise SystemExit(1)

    resume_files = sorted(
        [f for f in os.listdir(PROCESS_FOLDER)
         if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS],
        key=natural_file_sort_key
    )

    if max_files > 0 and len(resume_files) > max_files:
        if random_order:
            rng = random.Random(random_seed)
            resume_files = rng.sample(resume_files, max_files)
        else:
            resume_files = resume_files[:max_files]

    if not resume_files:
        log_message(f"❌ No supported files (.pdf, .doc, .docx) found in: {PROCESS_FOLDER}")
        raise SystemExit(1)

    if skill_source == 'dataset':
        log_message(f"[*] Skill source: dataset (SkillNer) - available={SKILLNER_AVAILABLE}")
    elif skill_source == 'csv':
        log_message(f"[*] Skill source: csv ({len(skills_list)} loaded from {SKILLS_CSV})")
    else:
        log_message(
            f"[*] Skill source: auto (dataset first, csv fallback={len(skills_list)} from {SKILLS_CSV})"
        )
    log_message(f"[*] Processing {len(resume_files)} resume file(s) from: {PROCESS_FOLDER}")
    log_message(f"[*] Workers: {max_workers}\n")
    if max_files > 0:
        mode = "random sample" if random_order else "first files"
        log_message(f"[*] Limit enabled: {len(resume_files)} file(s), mode={mode}, seed={random_seed}")
    if fast_response_mode:
        log_message("[*] Fast-response mode: ON (validation off, gender/address skipped, csv-preferred in auto)")
    if disable_validation:
        log_message("[INFO] Validation disabled via --no-validation")

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

    def _log_record(i, record):
        fname = record.get('file', '')
        name = record.get('name')
        contact_number = record.get('contact_number')
        gender = record.get('gender')
        email = record.get('email')
        address = record.get('address')
        matched_skills = record.get('skills') or []

        name_col = (name or '❌ NOT FOUND')[:col_w['name'] - 1]
        phone_col = (contact_number or '❌ NOT FOUND')[:col_w['phone'] - 1]
        gender_col = (gender or '❌ N/A')[:col_w['gender'] - 1]
        email_col = email or '❌ NOT FOUND'

        log_message(
            f"  {i:<{col_w['#']}} "
            f"{fname:<{col_w['file']}} "
            f"{name_col:<{col_w['name']}} "
            f"{phone_col:<{col_w['phone']}} "
            f"{gender_col:<{col_w['gender']}} "
            f"{email_col}"
        )

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

    indexed_files = list(enumerate(resume_files, 1))
    if max_workers <= 1:
        for i, fname in indexed_files:
            record = _extract_resume_record(
                fname,
                PROCESS_FOLDER,
                skill_source,
                skills_list,
                compiled_skill_matchers,
                fast_response_mode,
            )
            results.append(record)
            if record.get('error'):
                stats['errors'] += 1
                log_message(f"  {i:<{col_w['#']}} {fname:<{col_w['file']}} ❌ Error: {record['error']}")
                continue

            stats['successful'] += 1
            if not record.get('name'):
                stats['missing_name'] += 1
            if not record.get('email'):
                stats['missing_email'] += 1
            if not record.get('contact_number'):
                stats['missing_phone'] += 1
            if record.get('skills'):
                stats['skills_found'] += 1
            _log_record(i, record)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_meta = {
                executor.submit(
                    _extract_resume_record,
                    fname,
                    PROCESS_FOLDER,
                    skill_source,
                    skills_list,
                    compiled_skill_matchers,
                    fast_response_mode,
                ): (i, fname)
                for i, fname in indexed_files
            }
            for future in as_completed(future_to_meta):
                i, fname = future_to_meta[future]
                try:
                    record = future.result()
                except Exception as exc:
                    record = {
                        'file': fname,
                        'name': None,
                        'contact_number': None,
                        'email': None,
                        'gender': None,
                        'address': None,
                        'skills': [],
                        'error': str(exc),
                    }

                results.append(record)
                if record.get('error'):
                    stats['errors'] += 1
                    log_message(f"  {i:<{col_w['#']}} {fname:<{col_w['file']}} ❌ Error: {record['error']}")
                    continue

                stats['successful'] += 1
                if not record.get('name'):
                    stats['missing_name'] += 1
                if not record.get('email'):
                    stats['missing_email'] += 1
                if not record.get('contact_number'):
                    stats['missing_phone'] += 1
                if record.get('skills'):
                    stats['skills_found'] += 1
                _log_record(i, record)

    # ── Validation & Reports ──────────────────────────────────
    validation_summary = None
    if validator and results:
        validation_summary = validator.validate_batch(results)
        log_message("\n" + "="*120)
        # print_validation_report(validation_summary)  # Disabled - unicode error in validation
        
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