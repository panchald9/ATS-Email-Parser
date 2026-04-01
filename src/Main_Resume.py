import re
import os
import csv
import json
import sys
import importlib
import argparse
import random
import threading
from datetime import date
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

# ── Lazy-loaded NLP libs ────────────────────────────────────────
nlp = None
skill_extractor = None
SPACY_AVAILABLE = False
SKILLNER_AVAILABLE = False

def _ensure_spacy_loaded():
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
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════
RESUME_FOLDER  = r"D:\Project\ATS\ATS Email Parser\Bulk_Resumes_1775020050"
SKILLS_CSV     = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Skill.csv')
OUTPUT_JSON    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'resume_parsed.json')
VALIDATION_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'validation_report.json')
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

SKILL_SOURCE = 'auto'
FAST_SKILLNER_MODE = True
SKILLNER_MAX_TEXT_CHARS = 2200
ENABLE_VALIDATION = True
ENABLE_DETAILED_LOGGING = True
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'parser.log')
DEFAULT_MAX_WORKERS = min(8, (os.cpu_count() or 4))


# ══════════════════════════════════════════════════════════════
#  BLACKLISTS & CONSTANTS
#  FIX: Removed 'will', 'may', 'june', 'april' — these are
#       also common first names and caused name extraction misses.
# ══════════════════════════════════════════════════════════════
BLACKLIST = {
    # address / geography
    'gate','road','street','nagar','colony','flat','floor','block','near','post',
    'dist','area','city','town','village','sector','plot','phase','tehsil','taluka',
    'apartment','society','building','chowk','lane','bypass','main','cross',
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
    'hereby','declare','january','february','march','august','september',
    'october','november','december',
    # NOTE: 'april','june','july','may','will' REMOVED — valid first names
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
    'languages','certifications','certifications','training','top skills',
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

# ── Precompiled patterns ────────────────────────────────────────
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

GENDER_LABEL_RE = re.compile(r'(?i)\b(?:gender|sex)\b\s*[:\-]?\s*(male|female|m|f|man|woman|boy|girl)\b')
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
    r'\d+\s*-\s*\d+|'
    r'(?:to|–)\s*\d{4}|'
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|aug)\s*\d{4}'
    r')'
)

COMPANY_HINTS = {
    'pvt','ltd','limited','llp','inc','corp','private','industries',
    'university','college','school','institute','vidyalaya','society',
    'apartment','apt','road','nagar','colony','park',
}

COMMON_SURNAMES = {
    'kumar','singh','patel','yadav','khan','sharma','gupta','verma',
    'pal','tandel','desai','patil','vasava','jogal','shah','mehta',
    'joshi','trivedi','pandya','bhatt','nair','pillai','menon','iyer',
    'reddy','naidu','rao','mishra','dubey','tiwari','srivastava','chauhan','chaubey',
    'rajput','thakur','bose','chatterjee','mukherjee','banerjee','das',
    'sen','ghosh','kapoor','malhotra','khanna','chopra','ahuja','arora',
    'bhatia','sethi','anand','chawla','mehra','suri','walia','gill',
    'sidhu','dhillon','grewal','sandhu','randhawa','brar',
}

NON_NAME_WORDS = {
    'team','global','job','responsibilities','responsibility','output',
    'maintaining','excellent','while','hile','submitted','request',
    'achievements','core','competencies','competency','citizen','citizenship',
    'styrene','acryl','acrylonitrile',
    'previous','employers','then','call','me','cisco','finance',
}

# Header-like words/phrases that should not be accepted as person names.
NAME_HEADER_TOKENS = {
    'carrier', 'career', 'objective', 'objectives', 'portfolio', 'governance',
    'discipline', 'scjp', 'summary', 'profile', 'professional', 'declaration',
    'contacts', 'contact', 'email', 'mail', 'id', 'e',
    'languages', 'language', 'english', 'hindi',
    'hobbies', 'hobby', 'listening', 'music',
}

NAME_HEADER_PHRASES = {
    'career objective', 'carrier objective', 'carrier objectives',
    'portfolio governance', 'professional summary', 'career summary',
    'email id', 'e-mail id',
}

NAME_TECHNICAL_TOKENS = {
    'machine', 'learning', 'java', 'programmer', 'waterfall', 'model',
    'message', 'biotechnology', 'mscbiotechnology', 'gulp', 'server',
    'self', 'motivated',
}

EMAIL_LOCAL_NON_PERSON_TOKENS = {
    'admin', 'administrator', 'admission', 'career', 'careers', 'contact', 'cv', 'enquiry',
    'enquiries', 'hello', 'help', 'hr', 'hrd', 'info', 'mail', 'naukri', 'no', 'noreply',
    'office', 'recruitment', 'reply', 'resume', 'sales', 'service', 'support', 'team', 'user',
}

# ── EXPANDED name lists covering Indian subcontinent diversity ──
# FIX: Added ~60 Gujarati/Hindi/South Indian/Bengali/Punjabi names per gender
COMMON_MALE_FIRST_NAMES = {
    # Original
    'aarav','abhishek','aditya','ajay','akash','alok','amit','anil','ankit','arjun',
    'ashish','ashok','bhavesh','deepak','dhruv','gaurav','hardik','harsh','jay','jatin',
    'kiran','mahesh','manish','mayur','mohit','mukesh','nikhil','nilesh','paresh',
    'pradeep','pranav','rahul','rajesh','rakesh','rohan','sachin','sagar','sanjay',
    'saurabh','shubham','siddharth','sumit','sunil','tarun','uday','vijay','vikas',
    'vivek','vamshi','yash',
    # Gujarati additions
    'bhavin','chirag','darshan','dhaval','dhruvin','dilan','dipesh','farhan',
    'fenil','harshal','hemant','hitesh','jalp','janak','jayesh','jignesh',
    'jigar','kalpesh','kamlesh','keyur','krunal','kuldeep','lalit','lokesh',
    'madhav','meet','mihir','milan','mitesh','mitul','neel','niren','nirav',
    'nishant','omkar','parth','piyush','prakash','prasad','purav','raj',
    'rajan','ramesh','ravi','rinkal','rishi','ritesh','romil','rupesh',
    'rushabh','sahil','sameer','samir','sandip','sanket','shyam','smit',
    'sujal','suresh','swarup','tej','tejas','utsav','varun','vimal',
    'viral','vishal','yogesh','jogesh','zeal','chetan','krupal',
    # Hindi/North Indian
    'abhinav','akhil','amitabh','anand','ankur','anurag','arvind','ashwin',
    'ayush','bharat','deependra','devendra','dheeraj','gaurav','girish',
    'govind','himanshu','jagdish','kapil','kartik','krishna','lokesh',
    'manan','narendra','naveen','pankaj','prashant','puneet','pushkar',
    'raghav','rajiv','rakshit','ramesh','ranbir','rishabh','rohit','rupesh',
    'sandeep','shailesh','shekhar','shivam','sourabh','subhash','surendra',
    'tushar','umesh','vinay','vinit','vinod','vivaan','yuvraj',
    # South Indian
    'arun','balaji','ganesh','harish','karthik','kumaran','madhavan','manoj',
    'murugan','naresh','naveen','prakash','prathap','raju','ramesh','ravi',
    'saravanan','sathish','senthil','shiva','suresh','venkat','vijayakumar',
    # Bengali/East Indian
    'arnab','bikash','debashish','indrajit','kaushik','niloy','partha',
    'pritam','ranjit','samrat','souvik','subhrajit','tanmoy',
    # Punjabi/Sikh
    'amarjit','balwinder','gurpreet','gurjot','harjot','jaspreet','lakhvir',
    'manpreet','navjot','parminder','rajvir','simranpreet','sukhjinder',
    # Western/English common in India
    'alan','alex','andrew','ben','chris','daniel','david','james','john',
    'kevin','mark','michael','paul','peter','richard','robert','ryan',
    'samuel','steven','thomas','william','saiteja',
}

COMMON_FEMALE_FIRST_NAMES = {
    # Original
    'aarti','aishwarya','akanksha','anita','anjali','anusha','bhavika','bhumi','divya',
    'gauri','heena','hetal','janvi','jinal','kajal','karishma','khushi','kirti',
    'komal','manisha','megha','monika','muskan','neha','nidhi','nikita','payal',
    'pooja','priya','riddhi','ritu','sakshi','shreya','shruti','sonal','swati','teresa',
    'trisha','ujvala','vaishali','vijetha','vidhi',
    # Gujarati additions
    'alpesh','ami','amisha','amita','ankita','archana','arthi','asmita',
    'bansari','bhavna','chhaya','deepika','dhara','disha','drashti','foram',
    'gargi','hansa','himani','ishita','jalpa','jasmin','jigisha',
    'jyotsna','kalpana','kavita','khyati','kinjal','lata','lopa',
    'madhuri','mamta','manali','meena','meera','minal','mira','mitali',
    'naina','namrata','nandini','neeta','nilam','nisha','nitu','parul',
    'pinal','pinki','poorvi','prachi','pratibha','preeti','priyanka',
    'purvi','rachana','radhika','rekha','renuka','rima','rinki','rupa',
    'sangita','sangeeta','sapna','seema','sejal','sheetal',
    'shilpa','shital','smita','sneha','soni','sujata','sunita',
    'sushma','tanvi','taruna','tejal','urvashi','varsha','vina','vrunda',
    'yogita','zarna',
    # Hindi/North Indian
    'aditi','akansha','alka','amrita','ananya','arpita','asha','bharati',
    'chanchal','chandni','deepa','deepthi','dimple','ekta','garima',
    'gunjan','harsha','indu','jaya','jyoti','kamla','kavya','kumkum',
    'laxmi','leena','madhavi','mala','mamta','meghna','mishti','mona',
    'nandita','neelam','nutan','padma','pallavi','poonam','pratima',
    'pushpa','radha','rama','rani','rashmi','ratna','romita','roshni',
    'ruhi','rupa','sadhana','saloni','savita','shobha','shweta','sita',
    'smriti','sonali','sonam','sonu','sudha','supriya','surabhi',
    'swapna','tanu','tara','tulsi','twinkle','usha','vandana','veena',
    'vibha','vijayalakshmi','vineeta','yamini',
    # South Indian
    'abitha','amala','amitha','chitra','deepthi','geetha','indira',
    'kavitha','keerthana','lakshmi','lalitha','meenakshi','nithya',
    'padmaja','parvathi','preethi','priyamvada','radhamani','revathi',
    'saraswathi','savithri','shanthi','shobhana','sreedevi','subha',
    'sudha','suganya','suhasini','sumitha','sunitha','vani','vasantha',
    # Bengali
    'arpita','barnali','chandrima','debanjali','indrani','jhumpa',
    'kaberi','kakali','madhurima','mithu','mousumi','paramita','piyali',
    'pritha','purba','riya','rumki','sampurna','sharmistha','shreosi',
    'subhasree','tanushree','tiyasa',
    # Western/English common in India
    'alice','amy','anna','carol','claire','diana','emily','emma','grace',
    'helen','jessica','julia','karen','kate','laura','linda','lisa',
    'mary','michelle','natalie','olivia','rachel','rebecca','sandra',
    'sarah','sharon','sophie','stephanie','victoria',
    # Also valid female names previously blocked
    'april','june','may',
}


# ══════════════════════════════════════════════════════════════
#  DOB EXTRACTION  (NEW — complete implementation)
# ══════════════════════════════════════════════════════════════
DOB_LABEL_RE = re.compile(
    r'(?i)\b(?:date\s+of\s+birth|d\.?\s*o\.?\s*b\.?|birth\s+date|born\s+on|born|dob)\b'
    r'\s*[:\-–]?\s*'
    r'('
    r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}'           # DD/MM/YYYY  DD-MM-YY
    r'|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}'             # YYYY-MM-DD
    r'|\d{1,2}[\/\-](?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\/\-]\d{2,4}'  # 12-Jan-1998
    r'|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+\d{2,4}'  # 12 Jan 1998
    r'|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+\d{1,2},?\s+\d{2,4}'  # Jan 12, 1998
    r'|\d{1,2}\s+(?:january|february|march|april|june|july|august|september|october|november|december)\s+\d{2,4}'
    r'|(?:january|february|march|april|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{2,4}'
    r')',
    re.I
)

# Age pattern: "Age: 25" or "Age: 25 years"
AGE_LABEL_RE = re.compile(
    r'(?i)\b(?:age|years?\s+old)\b\s*[:\-–]?\s*(\d{1,2})\b'
)

# Bare date that looks like a birth year range (1970–2005)
DOB_BARE_RE = re.compile(
    r'(?i)(?:dob|d\.o\.b|birth|born)[^\n]{0,40}?'
    r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.](?:19|20)\d{2})'
)

# Personal info header detection
PERSONAL_START_RE = re.compile(
    r'(?i)\b(?:personal\s+(?:details?|information|bio(?:graphy)?)|about\s+me|bio)\b'
)

PERSONAL_END_RE = re.compile(
    r'(?i)\b(?:education|experience|skills?|projects?|objective|employment|work|technical|professional|core\s+competencies|achievements?|certifications?|languages?|hobbies?|interests?|declaration|references?|publications?)\b'
)

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'june': 6, 'july': 7, 'august': 8, 'september': 9,
    'october': 10, 'november': 11, 'december': 12,
}


def _parse_dob_value(raw):
    """
    Normalise any recognised date string to DD/MM/YYYY.
    Returns the normalised string or None if the value cannot be validated.
    Also validates the age (should not be negative or over 120).
    """
    if not raw:
        return None
    raw = re.sub(r'\s+', ' ', raw).strip()

    parsed_date = None
    
    # ── Numeric: DD/MM/YYYY  DD-MM-YYYY  DD.MM.YY etc. ──────────
    m = re.match(r'^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})$', raw)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = c if c > 100 else (2000 + c if c < 30 else 1900 + c)
        # Prefer DD/MM interpretation for Indian documents
        if 1 <= b <= 12 and 1 <= a <= 31 and 1900 <= year <= 2025:
            parsed_date = (a, b, year)
        elif 1 <= a <= 12 and 1 <= b <= 31 and 1900 <= year <= 2025:
            parsed_date = (b, a, year)

    # ── Numeric: YYYY-MM-DD ──────────────────────────────────────
    if not parsed_date:
        m = re.match(r'^(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})$', raw)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1900 <= year <= 2025 and 1 <= month <= 12 and 1 <= day <= 31:
                parsed_date = (day, month, year)

    # ── Text month with slash: "12-Jan-1998" / "12/Jan/1990" ───
    if not parsed_date:
        m = re.match(
            r'^(\d{1,2})[\/\-](jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\/\-](\d{2,4})$',
            raw, re.I
        )
        if m:
            day   = int(m.group(1))
            month = MONTH_MAP.get(m.group(2).lower()[:3])
            if month:
                year  = int(m.group(3))
                year  = year if year > 100 else (2000 + year if year < 30 else 1900 + year)
                if 1900 <= year <= 2025 and 1 <= day <= 31:
                    parsed_date = (day, month, year)

    # ── Text month: "12 January 1998" / "12 Jan 1998" ───────────
    if not parsed_date:
        m = re.match(
            r'^(\d{1,2})\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|'
            r'may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|'
            r'nov(?:ember)?|dec(?:ember)?)\w*\.?\s+(\d{2,4})$',
            raw, re.I
        )
        if m:
            day   = int(m.group(1))
            month = MONTH_MAP.get(m.group(2).lower()[:3])
            if month:
                year  = int(m.group(3))
                year  = year if year > 100 else (2000 + year if year < 30 else 1900 + year)
                if 1900 <= year <= 2025 and 1 <= day <= 31:
                    parsed_date = (day, month, year)

    # ── Text month: "January 12, 1998" / "Jan 12 1998" ──────────
    if not parsed_date:
        m = re.match(
            r'^(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|'
            r'may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|'
            r'nov(?:ember)?|dec(?:ember)?)\w*\.?\s+(\d{1,2}),?\s+(\d{2,4})$',
            raw, re.I
        )
        if m:
            month = MONTH_MAP.get(m.group(1).lower()[:3])
            if month:
                day   = int(m.group(2))
                year  = int(m.group(3))
                year  = year if year > 100 else (2000 + year if year < 30 else 1900 + year)
                if 1900 <= year <= 2025 and 1 <= day <= 31:
                    parsed_date = (day, month, year)

    if parsed_date:
        day, month, year = parsed_date
        # Validate age is reasonable (1-120 years old)
        try:
            import datetime
            birth_date = datetime.date(year, month, day)
            age = (datetime.date.today() - birth_date).days // 365
            if 1 <= age <= 120:
                return f"{day:02d}/{month:02d}/{year}"
        except (ValueError, OverflowError):
            pass
    
    return None


def _infer_dob_from_age(age_str):
    """
    Infer DOB from age string like '25' or '40'.
    Returns estimated DD/MM/YYYY or None.
    """
    if not age_str:
        return None
    try:
        age = int(age_str.strip())
        if 1 <= age <= 120:
            import datetime
            birth_year = datetime.date.today().year - age
            # Use Jan 1 as placeholder since exact date unknown
            return f"01/01/{birth_year}"
    except (ValueError, TypeError):
        pass
    return None


def extract_dob(text):
    """
    Extract Date of Birth from resume text.
    Comprehensive 5-pass strategy:
      Pass 1 – Labeled DOB pattern (most reliable): 'DOB: 12/05/1995'
      Pass 2 – Age inference: 'Age: 25' or '25 years old'
      Pass 3 – Personal-info section: bare date adjacent to dob/birth keyword
      Pass 4 – Contextual search: DOB keyword + any date token on same line
      Pass 5 – Biographical section: dates in contact/about sections
    Returns DD/MM/YYYY string or None.
    """
    if not text:
        return None

    t = normalize_compact_text(text)
    lines = [re.sub(r'\s+', ' ', ln).strip() for ln in t.splitlines() if ln.strip()]
    if not lines:
        return None

    # ── Pass 1: explicit labeled DOB pattern ────────────────────
    for line in lines[:120]:
        m = DOB_LABEL_RE.search(line)
        if m:
            parsed = _parse_dob_value(m.group(1))
            if parsed:
                return parsed

    # ── Pass 2: age-based inference ────────────────────────────
    #    Extract from patterns like "Age: 25" or "25 years old"
    for line in lines[:100]:
        m = AGE_LABEL_RE.search(line)
        if m:
            age_str = m.group(1)
            dob = _infer_dob_from_age(age_str)
            if dob:
                return dob

    # ── Pass 3: bare date in personal-info section ──────────────
    #    Uses better section detection to avoid employment dates.
    personal_section = []
    in_personal = False
    for line in lines:
        lower = line.lower()
        if PERSONAL_START_RE.search(lower):
            in_personal = True
        if in_personal and PERSONAL_END_RE.search(lower):
            break
        if in_personal:
            personal_section.append(line)

    for line in personal_section[:50]:
        m = DOB_BARE_RE.search(line)
        if m:
            parsed = _parse_dob_value(m.group(1))
            if parsed:
                return parsed

    # ── Pass 4: contextual DOB keyword + any date token ────────
    any_date_re = re.compile(
        r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}'
        r'|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}'
        r'|\d{1,2}\s+\w+\s+\d{4}'
        r'|\d{1,2}\s*\-\s*\w+\s*\-\s*\d{4}'
        r'|\w+\s+\d{1,2},?\s+\d{4})',
        re.I
    )
    for line in lines[:100]:
        lower = line.lower()
        if not re.search(
            r'\b(?:d\.?o\.?b\.?|date\s+of\s+birth|birth\s+date|born|birthdate)\b', lower
        ):
            continue
        for date_m in any_date_re.finditer(line):
            parsed = _parse_dob_value(date_m.group(1))
            if parsed:
                return parsed

    # ── Pass 5: biographical/contact section ───────────────────
    #    Look for dates in dedicated contact or bio sections
    bio_section = []
    for line in lines[:60]:
        lower = line.lower()
        if re.search(
            r'\b(?:contact|biography|bio|about|personal\s+brief|introduction)\b', lower
        ):
            bio_section.append(line)

    for line in bio_section:
        m = DOB_BARE_RE.search(line)
        if m:
            parsed = _parse_dob_value(m.group(1))
            if parsed:
                return parsed

    return None


# ══════════════════════════════════════════════════════════════
#  TEXT EXTRACTION
# ══════════════════════════════════════════════════════════════
def natural_file_sort_key(filename):
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
    digits  = re.sub(r'\D', '', cleaned)
    if not (7 <= len(digits) <= 15):
        return None
    if not cleaned.startswith('+') and len(digits) > 12:
        return None
    if len(set(digits)) == 1:
        return None
    if re.match(r'^(19|20)\d{2}$', digits):
        return None
    if len(digits) == 12 and digits.startswith('0'):
        year_hits = re.findall(r'(?:19|20)\d{2}', digits)
        if year_hits and len(year_hits) >= 2:
            return None
    return f'+{digits}' if cleaned.startswith('+') else digits


def _extract_doc_with_word_com(path):
    word = None
    doc  = None
    try:
        import win32com.client
    except Exception as exc:
        return None, f"pywin32 not available for Word COM fallback: {str(exc)[:120]}"
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc  = word.Documents.Open(path, ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False)
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
    if not text:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\x0b', '\n').replace('\x0c', '\n')
    text = re.sub(r'[\x00-\x08\x0e-\x1f\x7f]', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_text(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Resume file not found: {path}")

    ext   = os.path.splitext(path)[1].lower()
    text  = None
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
                error = "python-docx not installed"
            else:
                try:
                    doc  = Document(path)
                    text = _collect_docx_text(doc)
                    if not text or not text.strip():
                        error = "DOCX extraction returned empty text"
                except Exception as docx_err:
                    error = f"python-docx error: {str(docx_err)[:100]}"

        elif ext == '.doc':
            if TEXTRACT_AVAILABLE:
                try:
                    raw  = textract.process(path)
                    text = raw.decode('utf-8', errors='ignore')
                    if not text or not text.strip():
                        error = "DOC extraction returned empty text"
                except Exception as textract_err:
                    textract_msg = str(textract_err)
                    if 'antiword' in textract_msg.lower():
                        fallback_text, fallback_err = _extract_doc_with_word_com(path)
                        if fallback_text and fallback_text.strip():
                            text  = fallback_text
                            error = None
                        else:
                            error = (
                                "textract error: antiword missing; "
                                + (fallback_err or "Word COM fallback unavailable")
                            )
                    else:
                        error = f"textract error: {textract_msg[:100]}"
            else:
                fallback_text, fallback_err = _extract_doc_with_word_com(path)
                if fallback_text and fallback_text.strip():
                    text  = fallback_text
                    error = None
                else:
                    error = (
                        "textract not installed; "
                        + (fallback_err or "Word COM fallback unavailable")
                    )
        else:
            error = f"Unsupported file extension: {ext}"

        if text:
            text = _clean_extracted_text(text)

        if error and text:
            if ENABLE_DETAILED_LOGGING:
                print(f"    Warning during extraction: {error}")
            return text

        if error:
            raise ValueError(error)

        return text or ""

    except Exception as exc:
        raise ValueError(f"Failed to extract from {os.path.basename(path)}: {str(exc)}")


def normalize_compact_text(text):
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
        if len(alpha) <= 2 and '.' in word:
            return re.sub(r'[a-z]', lambda m: m.group(0).upper(), word)
        chars      = list(word)
        seen_alpha = False
        for i, ch in enumerate(chars):
            if not ch.isalpha():
                continue
            if not seen_alpha:
                chars[i]   = ch.upper()
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
    """
    FIX: Added isupper() guard — don't split ALL-CAPS abbreviations
    like 'MBA', 'HR', 'BCA' which are section headings, not names.
    """
    if not text or len(text) < 5:
        return text
    if text.isupper():
        return text
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
    
    # FIX: Handle names with credentials like "Jamil M, PMP®, PSM"
    # Remove everything after comma if what follows looks like credentials
    if ',' in c:
        parts = c.split(',')
        left = parts[0]
        # Check if remaining parts look like credentials (short uppercase words with symbols)
        rest = ','.join(parts[1:]).strip()
        # If the part after comma is mostly uppercase and has credentials pattern, remove it
        if rest and re.match(r'^[A-Z\s\.\-/®™©]*$', rest):
            c = left
        elif re.fullmatch(r'\s*[A-Z][A-Z0-9\.\-/\s]{1,20}\s*', rest or ''):
            c = left
    
    # Remove credentials at the end (including special characters like ®, ™, ©)
    c = re.sub(r'(?:\s+|,\s*)(?:[A-Z]{2,5}(?:/[A-Z]{2,5})*)(?:\s*[®™©\.]*)*$', '', c)
    # Also catch credentials with special symbols
    c = re.sub(r'(?:\s+|,\s*)(?:[A-Z]{2,5}[®™©]*(?:\s+[A-Z]{2,5}[®™©]*)*)$', '', c)
    
    c = re.sub(r'(?i)^\s*(?:full\s+)?name\s*[:\-]\s*', '', c)
    c = re.sub(r'(?i)^\s*resume\s+of\s*', '', c)
    c = re.sub(r'^[\-–—:\.\)\(\[\]\{\}\|\s]+', '', c)
    c = re.sub(r'[\-–—:\.\)\(\[\]\{\}\|\s]+$', '', c)
    c = re.sub(r'\b([a-z])(?=\.)', lambda m: m.group(1).upper(), c)
    c = re.sub(r'\s+', ' ', c)
    
    # FIX: Handle single letter middle initials at the end (turn "Jamil M" into "Jamil")
    # But keep first name if followed by real surname
    words = c.split()
    if len(words) > 1:
        # If last word is single letter (likely middle initial), check if it should be kept
        if len(words[-1]) == 1 and words[-1].isupper():
            last_word = words[-1]
            # If there are at least 2 words before this, and second-to-last is a full name, remove the initial
            if len(words) >= 3 or (len(words) == 2 and len(words[0]) > 2):
                # Remove single letter middle initial
                c = ' '.join(words[:-1])
    
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
        if looks_like_name_header(c):
            continue
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


def looks_like_name_header(name):
    if not name:
        return True
    lowered = re.sub(r'\s+', ' ', name).strip().lower()
    if lowered in NAME_HEADER_PHRASES:
        return True
    words = [re.sub(r'[^a-z]', '', w) for w in lowered.split()]
    words = [w for w in words if w]
    if not words:
        return True
    if len(words) == 1 and words[0] in NAME_HEADER_TOKENS:
        return True
    if all(w in NAME_HEADER_TOKENS for w in words):
        return True
    return False


def is_valid(name, allow_single=False):
    if not name:
        return False
    name  = sanitize_candidate(name)
    name  = re.sub(r'\s+', ' ', name).strip()
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
    if looks_like_name_header(name):
        return False
    lower_tokens = [re.sub(r'[^a-z]', '', w.lower()) for w in words]
    lower_tokens = [w for w in lower_tokens if w]
    if lower_tokens and any(t in NAME_TECHNICAL_TOKENS for t in lower_tokens):
        return False
    for w in words:
        alpha = re.sub(r'[^A-Za-z]', '', w)
        if not alpha:
            continue
        if len(alpha) == 1:
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
        hit    = bool(result.get('first_name')), bool(result.get('last_name'))
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
        local        = m.group(1).lower()
        chunks       = [p for p in re.split(r'[^a-z0-9]+', local) if p]
        alpha_chunks = [re.sub(r'\d+', '', c) for c in chunks]
        alpha_chunks = [c for c in alpha_chunks if len(c) >= 3]
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
    parser.add_argument('--folder',        dest='folder',       default='')
    parser.add_argument('--no-validation', action='store_true')
    parser.add_argument('--skill-source',  dest='skill_source', default=SKILL_SOURCE)
    parser.add_argument('--workers',       dest='workers',      type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument('--limit',         dest='limit',        type=int, default=0)
    parser.add_argument('--random-order',  action='store_true')
    parser.add_argument('--seed',          dest='seed',         type=int, default=42)
    parser.add_argument('--fast-response', dest='fast_response', action='store_true')
    parser.add_argument('--full-accuracy', dest='fast_response', action='store_false')
    parser.set_defaults(fast_response=False)
    args, _ = parser.parse_known_args()

    cli_folder = (args.folder or '').strip().strip('"')
    chosen_folder = cli_folder or RESUME_FOLDER
    source = (args.skill_source or SKILL_SOURCE).strip().lower()
    if source not in {'dataset', 'csv', 'auto'}:
        source = SKILL_SOURCE
    workers = max(1, int(args.workers or 1))
    limit   = max(0, int(args.limit   or 0))
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
    raw  = [l.strip() for l in text.split('\n') if l.strip()]
    if not raw:
        return None

    compact_text = normalize_compact_text(text)
    norm = [normalize_caps(l) for l in raw]
    full = '\n'.join(norm)

    # FIX: Detect if we're in a "Top Skills" or similar section at the beginning
    # If the first 20 lines contain skill section markers, skip S0.3
    early_section_text ='\n'.join(norm[:20]).lower()
    has_early_skill_section = (
        'top skill' in early_section_text or 
        re.search(r'\b(?:skill|language|certification|strength)\b', early_section_text) and
        any(line.lower().strip() in SKIP_LINES for line in norm[:15])
    )
    
    # Find where the skill section ends (if present)
    start_search_idx = 0
    if has_early_skill_section:
        # Skills section typically occupies lines 4-16 in resumes with top skills
        # Set start_search_idx to skip past it but still catch names that come right after
        start_search_idx = 15  # Start searching from line 15 to catch names like "Om Dave"

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

    # S0.3: Strong top-line candidates (only if not in skill section)
    if not has_early_skill_section:
        for i, line in enumerate(norm[:10]):
            if re.search(r'[@\d]|https?://', line, re.I):
                continue
            line_lower = line.lower().strip('.,- ')
            if line_lower in SKIP_LINES:
                continue
            if line_has_bad_context(line):
                continue
            if not has_name_case_pattern(line):
                continue
            if looks_like_address(line):
                continue
            c = title_case(sanitize_candidate(split_camel(line)))
            if looks_like_name_header(c):
                continue
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

    # S0.1: "Resume of …"  (skip if in early skill section)
    if not has_early_skill_section:
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

        # S0.2: Two-line header  (skip if in early skill section)
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
        m    = re.search(
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
    for i, line in enumerate(norm[start_search_idx:min(start_search_idx + 25, len(norm))], start=start_search_idx):
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
            if looks_like_name_header(c):
                continue
            if accept(c, strict=False):
                return c

        clean = title_case(sanitize_candidate(re.sub(r'\s+', ' ', line).strip()))
        if re.match(r'^[A-Za-z][A-Za-z\s\.\-\']{2,45}$', clean):
            if looks_like_name_header(clean):
                continue
            if accept(clean, strict=False, allow_single=(i < 4)):
                return clean

        if i + 1 < len(norm):
            nxt = norm[i + 1]
            # FIX: Skip two-line combinations if both lines are skill items in early section
            if has_early_skill_section and i < 20:
                # In early skill section area, don't combine skill items
                continue
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
                    if looks_like_name_header(combined):
                        continue
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

    t          = normalize_compact_text(text).replace('\r', '\n')
    candidates = []
    segments   = [seg.strip() for seg in re.split(r'[\n|]+', t) if seg and seg.strip()]
    if not segments:
        segments = [t]

    for seg_idx, seg in enumerate(segments):
        for m in PHONE_LABEL_RE.finditer(seg):
            raw    = m.group(1)
            number = _normalize_phone_candidate(raw)
            if not number:
                continue
            digits_len = len(re.sub(r'\D', '', number))
            len_pref   = 0 if 10 <= digits_len <= 12 else (1 if digits_len == 13 else 2)
            candidates.append((8, len_pref, digits_len, seg_idx, m.start(), number))

        for m in PHONE_GENERIC_RE.finditer(seg):
            raw    = m.group(0)
            number = _normalize_phone_candidate(raw)
            if not number:
                continue
            digits_len = len(re.sub(r'\D', '', number))
            if digits_len < 10:
                continue
            ctx   = seg[max(0, m.start()-35):min(len(seg), m.end()+35)].lower()
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
            cut     = None
            for p in ("emailid","email","mailid","contact","skills","skill",
                      "objective","profile","resume"):
                if lowered.startswith(p) and len(local) > len(p) + 3:
                    cut = len(p)
                    break
            if cut is None:
                break
            local = local[cut:]
        local       = re.sub(r"(?i)^s[^a-z0-9]*k[^a-z0-9]*i[^a-z0-9]*l[^a-z0-9]*l[^a-z0-9]*s", "", local)
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
        ignore       = {"email","mail","id","contact","e","mailid"}
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
        dm          = EMAIL_DOMAIN_PREFIX_RE.search(domain_head)
        if not dm:
            domain_head = ''.join(right_tokens[:8]).strip('.')
            dm          = EMAIL_DOMAIN_PREFIX_RE.search(domain_head)
        if not dm:
            return None
        domain = dm.group(1).lower()
        email  = f"{local.lower()}@{domain}"
        if not EMAIL_STRICT_RE.match(email):
            return None
        if ".." in email or email.endswith("."):
            return None
        return email

    candidates = []
    for m in re.finditer(r"[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9.-]{3,}", text):
        email = build_email(m.group(0))
        if email:
            ctx   = text[max(0,m.start()-35):min(len(text),m.end()+35)].lower()
            score = 2 if re.search(r"email|e-mail|mail\s*id|contact", ctx) else 1
            candidates.append((score, len(email), email))

    for m in re.finditer(r"[A-Za-z0-9._%+\-\s]{2,90}@[A-Za-z0-9.\-\s]{2,120}", text):
        email = build_email(m.group(0))
        if email:
            ctx   = text[max(0,m.start()-35):min(len(text),m.end()+35)].lower()
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
            ctx   = text[max(0,m.start()-35):min(len(text),m.end()+35)].lower()
            score = 2 if re.search(r"email|e-mail|mail\s*id|contact", ctx) else 1
            candidates.append((score, len(email), email))

    if not candidates:
        return None
    candidates = list(set(candidates))
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    return candidates[0][2]


# ══════════════════════════════════════════════════════════════
#  GENDER EXTRACTION  (v2 — higher accuracy)
# ══════════════════════════════════════════════════════════════

# Relation patterns: S/O = son of (Male), D/O = daughter of (Female),
# W/O = wife of (Female), H/O = husband of (Male)
RELATION_CODE_RE = re.compile(
    r'(?i)\b(?:'
    r'(?:s[/\.]?o|son\s+of)\s*[:\-]?\s*(?:mr\.?\s+)?[A-Z]'
    r'|(?:d[/\.]?o|daughter\s+of)\s*[:\-]?\s*(?:mr\.?\s+)?[A-Z]'
    r'|(?:w[/\.]?o|wife\s+of)\s*[:\-]?\s*(?:mr\.?\s+)?[A-Z]'
    r'|(?:h[/\.]?o|husband\s+of)\s*[:\-]?\s*(?:mrs?\.?\s+)?[A-Z]'
    r')'
)

RELATION_MALE_RE   = re.compile(r'(?i)\b(?:s[/\.]?o|son\s+of)\b')
RELATION_FEMALE_RE = re.compile(r'(?i)\b(?:(?:d[/\.]?o|daughter\s+of)|(?:w[/\.]?o|wife\s+of))\b')
RELATION_MALE2_RE  = re.compile(r'(?i)\b(?:h[/\.]?o|husband\s+of)\b')

MARITAL_FEMALE_RE = re.compile(
    r'(?i)\b(?:housewife|married\s+woman|single\s+woman|unmarried\s+woman|'
    r'working\s+woman|business\s+woman|businesswoman)\b'
)
MARITAL_MALE_RE = re.compile(
    r'(?i)\b(?:married\s+man|single\s+man|unmarried\s+man|'
    r'businessman|business\s+man)\b'
)

KAUR_RE  = re.compile(r'(?i)\bkaur\b')

PROFILE_FEMALE_RE = re.compile(
    r'(?i)\b(?:female\s+candidate|female\s+applicant|she\s+is\s+(?:a|an)|'
    r'looking\s+for\s+(?:a\s+)?female|female\s+professional)\b'
)
PROFILE_MALE_RE = re.compile(
    r'(?i)\b(?:male\s+candidate|male\s+applicant|he\s+is\s+(?:a|an)|'
    r'looking\s+for\s+(?:a\s+)?male|male\s+professional)\b'
)


def _infer_gender_from_name(name):
    """
    Infer gender from the candidate's name.
    Returns 'Male', 'Female', or None.
    """
    if not name:
        return None

    tokens = [re.sub(r"[^A-Za-z]", "", t).lower() for t in name.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return None

    male_titles   = {'mr', 'mister', 'sir', 'shri', 'shree'}
    female_titles = {'mrs', 'ms', 'miss', 'madam', 'smt', 'kumari', 'km'}

    first = tokens[0]

    # Honorific titles are definitive
    if first in male_titles:
        return 'Male'
    if first in female_titles:
        return 'Female'

    # Sikh surname "Kaur" is exclusively female
    if 'kaur' in tokens:
        return 'Female'

    # Gujarati/Indian cultural suffixes are highly reliable
    full_joined = ' '.join(tokens)
    if re.search(r'\b\w+(?:ben|bhen|bai)\b', full_joined):
        return 'Female'
    if re.search(r'\b\w+bhai\b', full_joined):
        return 'Male'

    # If first token was a title, check second token as the actual first name
    check = tokens[1] if first in (male_titles | female_titles) and len(tokens) > 1 else first

    # Direct lookup in curated name sets
    if check in COMMON_MALE_FIRST_NAMES:
        return 'Male'
    if check in COMMON_FEMALE_FIRST_NAMES:
        return 'Female'

    # Also check last token (surname can sometimes reveal gender)
    if len(tokens) > 1:
        last = tokens[-1]
        if last in COMMON_MALE_FIRST_NAMES and last not in COMMON_FEMALE_FIRST_NAMES:
            return 'Male'
        if last in COMMON_FEMALE_FIRST_NAMES and last not in COMMON_MALE_FIRST_NAMES:
            return 'Female'

    # Suffix heuristics — ordered from most specific to most general
    if any(check.endswith(s) for s in ('kumar', 'bhai', 'veer', 'vir')):
        return 'Male'
    if check.endswith('ben') or check.endswith('bhen') or check.endswith('bai'):
        return 'Female'
    if any(check.endswith(s) for s in ('ita', 'isha', 'ina', 'ani', 'ika', 'lata', 'rani', 'devi')):
        return 'Female'
    if any(check.endswith(s) for s in ('raj', 'deep', 'esh', 'nath', 'kant', 'dev', 'prakash', 'teja')):
        return 'Male'

    # Dataset lookup
    if DATASET_AVAILABLE:
        is_first, _ = _dataset_first_or_last_hit(check)
        if is_first:
            pass

    return None


def _infer_gender_from_text_context(text):
    """Infer gender from self-identification cues in resume body text."""
    if not text:
        return None

    t = normalize_compact_text(text).lower()
    if not t:
        return None

    # ── Pass A: Explicit relation codes (most reliable in Indian resumes) ──
    if RELATION_MALE_RE.search(t):
        return 'Male'
    if RELATION_FEMALE_RE.search(t):
        return 'Female'
    if RELATION_MALE2_RE.search(t):
        return 'Male'

    # ── Pass B: Marital status phrases ──────────────────────────
    if MARITAL_FEMALE_RE.search(t):
        return 'Female'
    if MARITAL_MALE_RE.search(t):
        return 'Male'

    # ── Pass C: Profile/candidate description phrases ───────────
    if PROFILE_FEMALE_RE.search(t):
        return 'Female'
    if PROFILE_MALE_RE.search(t):
        return 'Male'

    # ── Pass D: Direct self-identification ──────────────────────
    if re.search(r'\b(?:i\s*am|im|i\'m)\s+(?:a\s+)?male\b', t):
        return 'Male'
    if re.search(r'\b(?:i\s*am|im|i\'m)\s+(?:a\s+)?female\b', t):
        return 'Female'

    # ── Pass E: Honorific/title cues (weighted) ─────────────────
    male_score   = 0
    female_score = 0

    male_score   += len(re.findall(r'\b(?:mr\.?|mister|sir|shri|shree)\b', t)) * 3
    female_score += len(re.findall(r'\b(?:mrs\.?|miss|madam|smt|kumari)\b', t)) * 3

    # Pronoun cues (first 4000 chars to reduce noise from job descriptions)
    head = t[:4000]
    male_score   += len(re.findall(r'\b(?:he|him|his)\b', head))
    female_score += len(re.findall(r'\b(?:she|her|hers)\b', head))

    # ── Pass F: Lower threshold — even 1 strong signal counts ───
    if male_score >= 1 and female_score == 0:
        return 'Male'
    if female_score >= 1 and male_score == 0:
        return 'Female'

    # Competing signals: require a margin
    if male_score >= 2 and male_score >= female_score + 2:
        return 'Male'
    if female_score >= 2 and female_score >= male_score + 2:
        return 'Female'

    return None


def extract_gender(text, name=None):
    """
    Full gender extraction pipeline (v2):
      1. Relation codes: S/O (son of) -> Male, D/O/W/O -> Female
      2. Explicit 'Gender: Male/Female' label
      3. Table-style Gender label on separate lines
      4. Gender/sex keyword near Male/Female token
      5. Marital status phrases, profile descriptions
      6. Narrative self-identification / pronoun cues
      7. Sikh surname "Kaur" -> Female
      8. Name-based inference (last resort)
    """
    if not text:
        return _infer_gender_from_name(name)

    t     = normalize_compact_text(text)
    lines = [re.sub(r'\s+', ' ', line).strip() for line in t.splitlines() if line.strip()]

    def _map_gender_token(token):
        token = (token or '').strip().lower().rstrip('.)')
        if token in {'male', 'm', 'man', 'boy'}:
            return 'Male'
        if token in {'female', 'f', 'woman', 'girl'}:
            return 'Female'
        return None

    # Pass 0: Relation codes (S/O, D/O, W/O) — very common in Indian resumes
    # Check first 60 lines only (personal details section)
    early_text_raw = '\n'.join(lines[:60]).lower()
    if RELATION_MALE_RE.search(early_text_raw):
        return 'Male'
    if RELATION_FEMALE_RE.search(early_text_raw):
        return 'Female'
    if RELATION_MALE2_RE.search(early_text_raw):
        return 'Male'

    # Pass 0b: Sikh surname Kaur in the name field
    if name and KAUR_RE.search(name):
        return 'Female'

    # Pass 1: explicit labeled gender field
    for line in lines[:80]:
        m = GENDER_LABEL_RE.search(line)
        if not m:
            continue
        mapped = _map_gender_token(m.group(1))
        if mapped:
            return mapped

    # Pass 1b: table-style rows where value is on the next line
    for i, line in enumerate(lines[:80]):
        if not re.fullmatch(r'(?i)(?:gender|sex)\s*[:\-]?', line):
            continue
        for j in range(i + 1, min(i + 3, len(lines))):
            nxt = lines[j]
            standalone = re.fullmatch(r'(?i)(male|female|m|f|man|woman|boy|girl)\.?', nxt)
            if standalone:
                mapped = _map_gender_token(standalone.group(1))
                if mapped:
                    return mapped
            inline = re.search(r'(?i)\b(male|female|m|f|man|woman|boy|girl)\b', nxt)
            if inline and len(nxt.split()) <= 5:
                mapped = _map_gender_token(inline.group(1))
                if mapped:
                    return mapped

    # Pass 2: gender keyword near Male/Female token
    early = '\n'.join(lines[:35]).lower()
    if GENDER_EARLY_MALE_RE.search(early):
        return 'Male'
    if GENDER_EARLY_FEMALE_RE.search(early):
        return 'Female'

    # Pass 3: marital status + profile phrase cues
    if MARITAL_FEMALE_RE.search(t.lower()):
        return 'Female'
    if MARITAL_MALE_RE.search(t.lower()):
        return 'Male'
    if PROFILE_FEMALE_RE.search(t.lower()):
        return 'Female'
    if PROFILE_MALE_RE.search(t.lower()):
        return 'Male'

    # Pass 4: narrative self-identification + pronouns (improved threshold)
    inferred = _infer_gender_from_text_context(t)
    if inferred:
        return inferred

    # Pass 5: name-based inference (weakest signal)
    return _infer_gender_from_name(name)


# ══════════════════════════════════════════════════════════════
#  ADDRESS EXTRACTION
# ══════════════════════════════════════════════════════════════
def extract_address(text):
    if not text:
        return None

    t     = normalize_compact_text(text)
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
        # Avoid long narrative/experience lines being treated as address.
        if len(value.split()) > 18 and ',' not in value:
            return None
        if value.count(',') > 6:
            return None
        if value.count('.') > 2:
            return None
        lower_value = value.lower()
        non_address_phrases = (
            'working on', 'upgraded the', 'completes day-to-day', 'conduct various conference',
            'analyzing the', 'operating systems', 'inventory control', 'responses to it',
        )
        if any(p in lower_value for p in non_address_phrases):
            return None
        if ADDRESS_CONTACT_RE.search(value):
            return None
        if re.search(
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)[.,\-\s]+\d{4}',
            value, re.I
        ):
            return None
        if re.search(
            r'(?:\d{4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)\s+\d{4})\s*(?:to|–|-|–)\s*(?:\d{4}|present|till|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december))',
            value, re.I
        ):
            return None
        bad_words = len(re.findall(ADDRESS_NON_RE, value))
        if bad_words >= 1:
            return None
        hint_hits  = len(ADDRESS_HINT_RE.findall(value))
        has_postal = bool(re.search(r'\b\d{3,6}\b', value))
        if hint_hits == 0 and not has_postal:
            return None
        return value

    # First preference: explicit address label
    for i, line in enumerate(lines[:80]):
        m = ADDRESS_LABEL_RE.match(line)
        if not m:
            continue
        parts = []
        first = m.group(1).strip()
        if first and not ADDRESS_STOP_RE.match(first) and not ADDRESS_CONTACT_RE.search(first):
            bad_first = len(re.findall(ADDRESS_NON_RE, first))
            if bad_first == 0:
                if not re.search(
                    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)\s+\d{4}',
                    first, re.I
                ):
                    if not re.search(r'\d{4}\s*(?:to|–|-)\s*(?:\d{4}|present)', first, re.I):
                        parts.append(first)
        for j in range(i + 1, min(i + 4, len(lines))):
            nxt = lines[j]
            if ADDRESS_STOP_RE.match(nxt):
                break
            if ADDRESS_CONTACT_RE.search(nxt):
                break
            bad_nxt = len(re.findall(ADDRESS_NON_RE, nxt))
            if bad_nxt >= 1:
                break
            if re.search(
                r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)\s+\d{4}',
                nxt, re.I
            ):
                break
            if re.search(r'\d{4}\s*(?:to|–|-)\s*(?:\d{4}|present)', nxt, re.I):
                break
            if len(nxt.split()) <= 1:
                break
            parts.append(nxt)
        candidate = clean_address(', '.join(parts))
        if candidate:
            return candidate

    # Fallback: scored address-like line block
    best       = None
    best_score = -1
    for i, line in enumerate(lines[:120]):
        if ADDRESS_STOP_RE.match(line) or ADDRESS_CONTACT_RE.search(line):
            continue
        if re.search(
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)\s+\d{4}',
            line, re.I
        ):
            continue
        if re.search(r'\d{4}\s*(?:to|–|-)\s*(?:\d{4}|present)', line, re.I):
            continue
        bad_count = len(re.findall(ADDRESS_NON_RE, line))
        if bad_count >= 1:
            continue
        score      = 0
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
            if len(re.findall(ADDRESS_NON_RE, nxt)) >= 1:
                break
            if len(nxt.split()) <= 1:
                break
            parts.append(nxt)
        candidate = clean_address(', '.join(parts))
        if candidate and score > best_score:
            best       = candidate
            best_score = score

    return best


# ══════════════════════════════════════════════════════════════
#  SKILLS LOADING & MATCHING
# ══════════════════════════════════════════════════════════════
def is_valid_skill(skill):
    if not skill:
        return False
    if len(skill) < 2 or len(skill) > 120:
        return False
    invalid_patterns = [
        r"^i'm unable to extract", r"^unable to extract",
        r"^error", r"^n/a$", r"^none$", r"^unknown$", r"^not applicable",
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
    if not skill:
        return ''
    k = skill.lower().strip()
    k = re.sub(r'\s+', ' ', k)
    k = re.sub(r'[^a-z0-9+#]+', '', k)
    return k


GENERIC_SKILL_STOPWORDS = {
    'ability','abilities','analysis','analytical','application','applications',
    'assurance','background','batch','capability','capabilities','communication',
    'compliance','control','coordination','creative','data','decision','delivery',
    'design','development','documentation','environment','evaluation','execution',
    'experience','framework','frameworks','functional','implementation','improvement',
    'knowledge','leadership','learning','maintenance','management','methodology',
    'methods','model','modeling','modelling','monitoring','operations','optimization',
    'organizing','performance','planning','problem','process','processes','production',
    'professional','project','projects','quality','reporting','research','responsibility',
    'responsibilities','safety','skills','solution','solutions','strategy','support',
    'systems','technical','technology','testing','training','troubleshooting','work',
    'certification','certifications','manufacturing','materials','balance','routing',
    # Languages - NOT skills
    'english','spanish','french','german','italian','portuguese','russian','chinese',
    'hindi','gujarati','marathi','bengali','telugu','kannada','malayalam','tamil',
    'urdu','punjabi','arabic','japanese','korean','dutch','swedish','norwegian',
    'danish','finnish','polish','czech','hungarian','romanian','greek','hebrew',
    # Section headers that shouldn't be skills
    'languages','language','certifications','certification','top skills','skills',
    'strength','strengths','achievement','achievements','personal','profile','summary',
}

STRONG_SINGLE_WORD_SKILLS = {
    'aws','azure','c','c#','c++','cad','css','excel','git','go','html','java',
    'javascript','jira','json','kafka','kubernetes','linux','matlab','mongodb',
    'mysql','oracle','php','postgresql','powerbi','powershell','python','sap',
    'selenium','snowflake','sql','tableau','terraform','typescript','unix','xml','yaml',
}

BUSINESS_SKILL_ALLOWLIST = {
    'crm','kpi','mis','hr','finance','analytics','marketing','coordination','booking',
    'strategy','automation','optimization','design','campaign','recruitment',
    'hiring','formulation','salesplanning','servicedelivery','strategicplanning',
    'marketresearch','performanceimprovement','performancemonitoring','portoperation',
    'dataanalysis','dataanalytics','businessanalysis','marketingstrategy',
    'customerrelationship','customerengagement','customersatisfaction',
    'clientcoordination','clientengagement','clienthandling','clientinteraction',
    'socialmedia','mediamarketing','leadgeneration','realestate',
}

SKILL_SECTION_HEADER_RE = re.compile(
    r'(?i)\b('
    r'technical\s+skills?|core\s+skills?|key\s+skills?|skills?\s*&\s*technolog(?:y|ies)|'
    r'skills?\s*&\s*tools?|core\s+competenc(?:y|ies)|areas?\s+of\s+(?:expertise|excellence)|'
    r'technical\s+specifications?|competencies?|technolog(?:y|ies)|tools?|software|'
    r'expertise|proficien(?:cy|cies)|frameworks?|certifications?'
    r')\b'
)

NON_SKILL_SECTION_HEADER_RE = re.compile(
    r'(?i)^\s*(?:'
    r'professional\s+summary|summary|profile|career\s+objective|objective|'
    r'work\s+experience|professional\s+experience|experience|employment\s+history|'
    r'education|academic\s+qualification(?:s)?|projects?|internships?|'
    r'personal\s+details?|contact|declaration|references?|hobbies|interests?|'
    r'achievements?|awards?|publications?|languages?|certifications?'
    r')\b'
)


def _is_weak_generic_skill(skill):
    if not skill:
        return True
    normalized = normalize_skill_key(skill)
    if not normalized:
        return True
    if normalized in BUSINESS_SKILL_ALLOWLIST:
        return False
    if normalized in STRONG_SINGLE_WORD_SKILLS:
        return False
    if normalized in GENERIC_SKILL_STOPWORDS:
        return True
    words = re.findall(r'[A-Za-z0-9+#]+', skill.lower())
    if not words:
        return True
    if len(words) >= 2 and all(len(w) == 1 for w in words):
        return True
    if normalized in {'com', 'iam'}:
        return True
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
    skills       = []
    seen         = set()
    invalid_count = 0

    if not os.path.exists(csv_path):
        print(f"[!] Skills CSV not found: {csv_path}")
        return skills

    with open(csv_path, mode='r', encoding='utf-8', errors='ignore', newline='') as f:
        reader     = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        has_skill_col  = 'skill'             in [fn.strip().lower() for fn in fieldnames]
        has_norm_col   = 'normalized_skill'  in [fn.strip().lower() for fn in fieldnames]
        has_weight_col = 'resume_match_weight' in [fn.strip().lower() for fn in fieldnames]

        for row in reader:
            if has_skill_col:
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
                    words = re.findall(r'[A-Za-z0-9+#]+', candidate.lower())
                    if has_weight_col and weight <= 2 and len(words) == 1:
                        w = words[0]
                        w_key = normalize_skill_key(w)
                        if (
                            w not in STRONG_SINGLE_WORD_SKILLS
                            and w_key not in BUSINESS_SKILL_ALLOWLIST
                            and len(w) <= 12
                        ):
                            continue
                    key = normalize_skill_key(candidate)
                    if key and key not in seen:
                        seen.add(key)
                        skills.append(candidate)
            else:
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
    matchers = []
    seen     = set()
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
    (r'\bcrm\b|customer\s+relationship\s+management', 'CRM'),
    (r'\bkpi(?:s)?\b|key\s+performance\s+indicator(?:s)?', 'KPI'),
    (r'\bmis\b|management\s+information\s+system(?:s)?', 'MIS'),
    (r'\bmarket\s+research\b', 'Market Research'),
    (r'\bstrateg(?:y|ic\s+planning)\b', 'Strategic Planning'),
    (r'\bclient\s+coordination\b', 'Client Coordination'),
    (r'\bclient\s+engagement\b', 'Client Engagement'),
    (r'\bclient\s+interaction\b', 'Client Interaction'),
    (r'\bclient\s+handling\b', 'Client Handling'),
    (r'\bperformance\s+monitoring\b', 'Performance Monitoring'),
    (r'\bperformance\s+improvement\b', 'Performance Improvement'),
    (r'\bsales\s+planning\b', 'Sales Planning'),
    (r'\bservice\s+delivery\b', 'Service Delivery'),
    (r'\bport\s+operation(?:s)?\b', 'Port Operation'),
    (r'\bcustomer\s+satisfaction\b', 'Customer Satisfaction'),
    (r'\bcustomer\s+engagement\b', 'Customer Engagement'),
    (r'\bcustomer\s+relationship\b', 'Customer Relationship'),
    (r'\bsocial\s+media\b', 'Social Media'),
    (r'\blead\s+generation\b', 'Lead Generation'),
    (r'\bmedia\s+marketing\b', 'Media Marketing'),
    (r'\bmarketing\s+strategy\b', 'Marketing Strategy'),
    (r'\breal\s+estate\b', 'Real Estate'),
    (r'\bbusiness\s+analysis\b', 'Business Analysis'),
    (r'\bdata\s+analytics\b', 'Data Analytics'),
    (r'\bdata\s+analysis\b', 'Data Analysis'),
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
    (r'\bimpact\s*(?:test|testing)\b', 'Impact Testing'),
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
    if not text:
        return []
    inferred = []
    seen     = {normalize_skill_key(s) for s in (existing_skills or []) if s}
    haystack = normalize_compact_text(text).lower()
    for pattern, skill in INFERRED_SKILL_RULES:
        if re.search(pattern, haystack, re.I):
            key = normalize_skill_key(skill)
            if key and key not in seen and not _is_weak_generic_skill(skill):
                seen.add(key)
                inferred.append(skill)
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
    if not extracted_skills:
        return []
    alias_map = {
        'gmp': 'cGMP', 'cgmp': 'cGMP',
        'react': 'ReactJS', 'reactjs': 'ReactJS',
        'node': 'NodeJS', 'nodejs': 'NodeJS',
        'css3': 'CSS', 'vscode': 'Visual Studio Code',
        'visualstudiocode': 'Visual Studio Code', 'pycharm': 'PyCharm',
        'word': 'MS Word', 'msword': 'MS Word', 'microsoftword': 'MS Word',
        'processvalidation': 'Process Validation',
        'tabletmanufacturing': 'Tablet Manufacturing',
        'wetgranulation': 'Wet Granulation', 'drygranulation': 'Dry Granulation',
        'compression': 'Compression', 'coating': 'Coating',
        'equipmentcalibration': 'Equipment Calibration',
        'equipmentqualification': 'Equipment Qualification',
        'sop': 'SOP Documentation',
        'bmr': 'Batch Manufacturing (BMR/MFR)', 'mfr': 'Batch Manufacturing (BMR/MFR)',
        'oee': 'OEE (Overall Equipment Efficiency)',
        'rawdatum': 'Raw Data',
        'scikit': 'Scikit-learn', 'scikitlearn': 'Scikit-learn',
        'powerbi': 'Power BI',
        'cnn': 'Convolutional Neural Networks',
        'lstm': 'LSTM',
        'rnn': 'RNN',
    }
    weak_exact = {
        'manufacturing','materials','balance','routing','budgeting','pharmacy','portfolio',
        'solve','solved','solving', 'collaboration','collaborative','collaborating',
        'innovation','innovative','innovating', 'www','web', 'credit','linked','creditlinked',
        'iit','sal','guwahati','ahmedabad','institute','technology','school','university',
        'cross','functional','team','teams','crossfunctional','crossfunctionalteams',
    }
    normalized = []
    seen       = set()
    for raw in extracted_skills:
        if not raw:
            continue
        
        # FIX: Skip section headers combined with items like "languages english"
        raw_lower = raw.lower().strip()
        if any(header in raw_lower for header in 
               ['languages ', 'language ', 'certifications ', 'certification ', 'strength ', 'strengths ']):
            # Check if it's a section header + item pattern
            if ' ' in raw_lower:
                parts = raw_lower.split()
                if parts[0] in ['languages', 'language', 'certifications', 'certification', 'strength', 'strengths']:
                    # Skip if first word is a section header
                    continue
        
        # FIX: Skip malformed skills like "science generative" or "raw datum" until normalized
        if any(bad in raw_lower for bad in ['science generative', 'raw datum']):
            continue
        
        key   = normalize_skill_key(raw)
        if not key:
            continue
        
        # FIX: Remove duplicate words (python python -> python, data data -> data data)
        skill_base = alias_map.get(key, raw)
        words = skill_base.split()
        if len(words) > 1:
            # Remove duplicate consecutive words
            unique_words = []
            for word in words:
                if not unique_words or unique_words[-1].lower() != word.lower():
                    unique_words.append(word)
            skill_base = ' '.join(unique_words)
        
        skill     = skill_base
        skill_key = normalize_skill_key(skill)
        if not skill_key or skill_key in seen:
            continue
        if skill_key in weak_exact:
            continue
        if _is_weak_generic_skill(skill):
            continue
        seen.add(skill_key)
        normalized.append(skill)
    
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
            if normalize_skill_key(token) in BUSINESS_SKILL_ALLOWLIST:
                final_skills.append(skill)
                continue
            if any(token in ts for ts in token_sets):
                continue
        final_skills.append(skill)
    return final_skills


def extract_skills_from_resume(text, skills_list, compiled_skill_matchers=None):
    if not text or not skills_list:
        return []
    section_text, has_section = _extract_skill_section_text(text)
    normalized_text = section_text if has_section else normalize_compact_text(text)
    normalized_text = re.sub(r'(?i)\bnode\s*[\./-]?\s*js\b', 'nodejs', normalized_text)
    normalized_text = re.sub(r'(?i)\breact\s*[\./-]?\s*js\b', 'reactjs', normalized_text)
    normalized_text = re.sub(r'(?i)\bvs\s*code\b', 'vscode', normalized_text)
    normalized_text = re.sub(r'(?i)\bms\.?\s*word\b|\bmicrosoft\s+word\b', 'msword', normalized_text)
    matched_skills  = []
    seen            = set()
    if compiled_skill_matchers:
        for key, skill, pattern in compiled_skill_matchers:
            if key in seen:
                continue
            if pattern.search(normalized_text):
                seen.add(key)
                matched_skills.append(skill)
    else:
        for skill in skills_list:
            if not skill or _is_weak_generic_skill(skill):
                continue
            escaped = re.escape(skill.strip()).replace(r'\ ', r'\s+')
            pattern = re.compile(rf'(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])', re.IGNORECASE)
            if pattern.search(normalized_text):
                key = normalize_skill_key(skill)
                if key and key not in seen:
                    seen.add(key)
                    matched_skills.append(skill)
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
            if tokens and normalize_skill_key(tokens[0]) in BUSINESS_SKILL_ALLOWLIST:
                filtered.append(skill)
                continue
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
    if not line:
        return ''
    line = re.sub(r'\s+', ' ', line).strip()
    line = re.sub(r'^[\W_]+', '', line)
    line = re.sub(r'[\W_]+$', '', line)
    return line.strip()


def _is_probable_skill_header(line):
    candidate = _normalize_header_candidate(line)
    if not candidate:
        return False
    lower = candidate.lower()
    
    # Explicitly exclude "Languages" and "Certifications" alone
    if lower.strip() in ('languages', 'language', 'certifications', 'certification', 
                          'strengths', 'strength', 'hobbies', 'hobbies', 'interests'):
        return False
    
    if not SKILL_SECTION_HEADER_RE.search(lower):
        return False
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
    if len(words) <= 4:
        return True
    return False


def _is_probable_non_skill_header(line):
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
    if not text:
        return '', False
    normalized = normalize_compact_text(text)
    lines      = [re.sub(r'\s+', ' ', ln).strip() for ln in normalized.splitlines() if ln.strip()]
    if not lines:
        return '', False
    selected         = []
    in_skill_block   = False
    block_budget     = 0
    found_header     = False
    max_lines_per_block = 140
    for line in lines:
        lower = line.lower()
        if _is_probable_skill_header(line):
            in_skill_block = True
            found_header   = True
            block_budget   = max_lines_per_block
            selected.append(line)
            continue
        if in_skill_block:
            if _is_probable_non_skill_header(line):
                in_skill_block = False
                block_budget   = 0
                continue
            if re.search(r'[@]|https?://|\b(?:phone|mobile|email|contact)\b', lower):
                continue
            selected.append(line)
            block_budget -= 1
            if block_budget <= 0:
                in_skill_block = False
    return ('\n'.join(selected), found_header and len(selected) > 1)


def _build_fast_skillner_text(text):
    if not text:
        return ''
    section_text, has_section = _extract_skill_section_text(text)
    if has_section:
        return section_text[:SKILLNER_MAX_TEXT_CHARS]
    normalized = normalize_compact_text(text)
    return normalized[:SKILLNER_MAX_TEXT_CHARS]


# ══════════════════════════════════════════════════════════════
#  PROFESSIONAL EXPERIENCE EXTRACTION (ATS STYLE)
# ══════════════════════════════════════════════════════════════
EXPERIENCE_START_RE = re.compile(
    r'(?i)\b(?:work\s+experience|professional\s+experience|employment\s+history|'
    r'experience|work\s+history)\b'
)

EXPERIENCE_END_RE = re.compile(
    r'(?i)^\s*(?:education|skills?|projects?|certifications?|languages?|'
    r'declaration|references?|hobbies|interests?|objective|summary|profile|'
    r'personal\s+details?)\b'
)

EXPERIENCE_HEADER_ONLY_RE = re.compile(
    r'(?i)^\s*(?:work\s+experience|professional\s+experience|employment\s+history|'
    r'experience|work\s+history)\s*:?\s*$'
)

MAJOR_SECTION_HEADER_RE = re.compile(
    r'(?i)^\s*(?:education|skills?|technical\s+skills?|projects?|certifications?|languages?|'
    r'declaration|references?|hobbies|interests?|objective|summary|profile|personal\s+details?)\s*:?\s*$'
)

EMPLOYMENT_TYPE_RE = {
    'Internship': re.compile(r'(?i)\b(?:intern|internship|trainee)\b'),
    'Contract': re.compile(r'(?i)\b(?:contract|consultant|consulting)\b'),
    'Freelance': re.compile(r'(?i)\b(?:freelance|freelancer)\b'),
}

ROLE_HINT_RE = re.compile(
    r'(?i)\b(?:engineer|developer|manager|analyst|intern|consultant|officer|'
    r'executive|lead|architect|specialist|coordinator|administrator|tester|'
    r'designer|supervisor|associate|programmer)\b'
)

COMPANY_HINT_RE = re.compile(
    r'(?i)\b(?:pvt\.?|ltd\.?|limited|inc\.?|corp\.?|llp|technologies|solutions|'
    r'systems|services|company|industries|private)\b'
)

DATE_RANGE_RE = re.compile(
    r'(?i)\b('
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*\d{4}'
    r'|\d{1,2}[/-]\d{4}'
    r'|\d{4}'
    r')\s*(?:to|till|until|\-|–|—)\s*('
    r'present|current|till\s+date|'
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*\d{4}'
    r'|\d{1,2}[/-]\d{4}'
    r'|\d{4}'
    r')\b'
)

CTC_RE = re.compile(
    r'(?i)\b(?:ctc|current\s+ctc|expected\s+ctc|salary|compensation)\b\s*[:\-]?\s*'
    r'([\u20b9$]?\s*\d+(?:[\.,]\d+)?\s*(?:lpa|lakhs?|lacs?|k|m|per\s+annum|pa)?)'
)

NOTICE_RE = re.compile(
    r'(?i)\bnotice\s+period\b\s*[:\-]?\s*'
    r'(immediate|\d+\s*(?:days?|weeks?|months?))\b'
)

RESPONSIBILITY_LINE_RE = re.compile(
    r'^\s*(?:[-•*]|\d+\.|[a-z]\))\s*\S+'
)

TECH_KEYWORDS = {
    'python', 'java', 'sql', 'mysql', 'postgresql', 'oracle', 'react', 'node',
    'nodejs', 'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git',
    'linux', 'django', 'flask', 'fastapi', 'spring', 'hibernate', 'javascript',
    'typescript', 'html', 'css', 'power bi', 'tableau', 'excel', 'sap', 'erp'
}


def _extract_experience_section_lines(text):
    if not text:
        return []
    normalized = normalize_compact_text(text)
    lines = [re.sub(r'\s+', ' ', ln).strip() for ln in normalized.splitlines() if ln.strip()]
    section = []
    capture = False
    for line in lines:
        low = line.lower()
        if EXPERIENCE_HEADER_ONLY_RE.search(low):
            capture = True
            continue
        if capture and MAJOR_SECTION_HEADER_RE.search(low):
            break
        if capture:
            section.append(line)

    # Fallback for resumes without clean headers.
    if not section:
        for idx, line in enumerate(lines):
            if EXPERIENCE_START_RE.search(line) and len(line.split()) <= 5:
                for tail in lines[idx + 1:]:
                    if MAJOR_SECTION_HEADER_RE.search(tail):
                        break
                    section.append(tail)
                break
    return section


def _looks_like_company(line):
    if not line or len(line) < 3:
        return False
    if COMPANY_HINT_RE.search(line):
        return True
    if '|' in line and DATE_RANGE_RE.search(line):
        return True
    if re.search(r'(?i)\b(?:worked\s+at|employer|organization)\b', line):
        return True
    words = re.findall(r'[A-Za-z&.]+', line)
    if 1 <= len(words) <= 8:
        # Title-heavy compact line often signals employer name.
        title_like = sum(1 for w in words if w[:1].isupper())
        if (
            title_like >= max(2, len(words) - 1)
            and ROLE_HINT_RE.search(line) is None
            and not re.search(r'(?i)\b(?:using|with|for|and|improved|developed|responsible)\b', line)
            and '.' not in line
        ):
            return True
    return False


def _looks_like_role(line):
    if not line:
        return False
    if len(line.split()) > 16:
        return False
    return bool(ROLE_HINT_RE.search(line))


def _parse_month_year(token):
    if not token:
        return None
    t = token.strip().lower()
    if t in {'present', 'current', 'till date'}:
        today = date.today()
        return today.year, today.month
    ym = re.match(r'^(\d{1,2})[/-](\d{4})$', t)
    if ym:
        month = int(ym.group(1))
        year = int(ym.group(2))
        if 1 <= month <= 12:
            return year, month
        return None
    y = re.match(r'^(\d{4})$', t)
    if y:
        return int(y.group(1)), 1
    m = re.match(
        r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*(\d{4})$',
        t
    )
    if m:
        month_key = m.group(1)[:3]
        month = MONTH_MAP.get(month_key)
        year = int(m.group(2))
        if month and 1 <= month <= 12:
            return year, month
    return None


def _extract_date_range(line):
    if not line:
        return (None, None, False, None)
    m = DATE_RANGE_RE.search(line)
    if not m:
        return (None, None, False, None)
    start_raw = re.sub(r'\s+', ' ', m.group(1)).strip()
    end_raw = re.sub(r'\s+', ' ', m.group(2)).strip()
    is_current = bool(re.match(r'(?i)^(present|current|till\s+date)$', end_raw))
    return (start_raw, end_raw, is_current, m.group(0).strip())


def _duration_from_range(start_raw, end_raw, is_current):
    start = _parse_month_year(start_raw)
    end = _parse_month_year(end_raw)
    if not start or not end:
        return None
    start_months = start[0] * 12 + start[1]
    end_months = end[0] * 12 + end[1]
    months = end_months - start_months
    if months < 0:
        return None
    years = months // 12
    rem = months % 12
    if years and rem:
        return f"{years}y {rem}m"
    if years:
        return f"{years}y"
    return f"{rem}m"


def _extract_ctc(text):
    if not text:
        return None
    m = CTC_RE.search(text)
    return m.group(1).strip() if m else None


def _extract_notice_period(text):
    if not text:
        return None
    m = NOTICE_RE.search(text)
    return m.group(1).strip() if m else None


def _extract_location_from_line(line):
    if not line:
        return None
    if re.search(r'(?i)\b(remote|onsite|hybrid)\b', line):
        return re.search(r'(?i)\b(remote|onsite|hybrid)\b', line).group(1).title()
    if ',' in line:
        parts = [p.strip() for p in line.split(',') if p.strip()]
        if (
            2 <= len(parts) <= 3
            and not ROLE_HINT_RE.search(line)
            and not DATE_RANGE_RE.search(line)
            and all(len(p.split()) <= 3 for p in parts)
            and not re.search(r'(?i)\b(?:using|with|for|and|improved|developed|responsible)\b', line)
        ):
            return ', '.join(parts)
    return None


def _extract_technologies(text):
    if not text:
        return []
    low = text.lower()
    found = []
    seen = set()
    for tech in sorted(TECH_KEYWORDS, key=len, reverse=True):
        pattern = r'\b' + re.escape(tech) + r'\b'
        if re.search(pattern, low):
            pretty = ' '.join(w.upper() if len(w) <= 3 else w.capitalize() for w in tech.split())
            key = normalize_skill_key(pretty)
            if key not in seen:
                seen.add(key)
                found.append(pretty)
    return found


def _extract_responsibilities(lines):
    if not lines:
        return []
    out = []
    seen = set()
    for line in lines:
        if not line:
            continue
        if RESPONSIBILITY_LINE_RE.search(line):
            val = re.sub(r'^\s*(?:[-•*]|\d+\.|[a-z]\))\s*', '', line).strip()
            key = val.lower()
            if val and key not in seen:
                seen.add(key)
                out.append(val)
    return out


def _extract_employment_type(text):
    if not text:
        return 'Full-time'
    for label, pattern in EMPLOYMENT_TYPE_RE.items():
        if pattern.search(text):
            return label
    return 'Full-time'


def extract_professional_experience_profile(text):
    """Extract ATS-style professional experience details from resume text."""
    section_lines = _extract_experience_section_lines(text)
    if not section_lines:
        return []

    blocks = []
    current = []
    for line in section_lines:
        has_date = bool(DATE_RANGE_RE.search(line))
        has_company = _looks_like_company(line)
        if current and (has_date or has_company) and len(current) >= 3:
            blocks.append(current)
            current = [line]
            continue
        current.append(line)
    if current:
        blocks.append(current)

    experiences = []
    for block in blocks:
        block_text = '\n'.join(block)
        company = None
        role = None
        location = None
        start_date = None
        end_date = None
        currently_working = False
        duration_raw = None

        for line in block:
            if '|' in line:
                pieces = [p.strip() for p in line.split('|') if p.strip()]
                for piece in pieces:
                    if role is None and _looks_like_role(piece):
                        role = piece
                    s, e, is_current, raw_duration = _extract_date_range(piece)
                    if s and e and start_date is None:
                        start_date = s
                        end_date = e
                        currently_working = is_current
                        duration_raw = raw_duration
                if pieces and company is None:
                    first_piece = pieces[0]
                    if _looks_like_company(first_piece):
                        company = first_piece
            if company is None and _looks_like_company(line):
                company = line
            if role is None and _looks_like_role(line):
                role = line
            if location is None:
                location = _extract_location_from_line(line)
            s, e, is_current, raw_duration = _extract_date_range(line)
            if s and e and start_date is None:
                start_date = s
                end_date = e
                currently_working = is_current
                duration_raw = raw_duration

        responsibilities = _extract_responsibilities(block)
        technologies = _extract_technologies(block_text)
        experience_duration = _duration_from_range(start_date, end_date, currently_working)

        # Keep blocks that look like an experience entry.
        if not any([company, role, start_date, responsibilities]):
            continue

        experiences.append({
            'company_name': company,
            'role': role,
            'employment_type': _extract_employment_type(block_text),
            'location': location,
            'start_date': start_date,
            'end_date': end_date,
            'currently_working': currently_working,
            'experience_duration': experience_duration,
            'duration_text': duration_raw,
            'ctc': _extract_ctc(block_text),
            'notice_period': _extract_notice_period(block_text),
            'technologies': technologies,
            'responsibilities': responsibilities,
        })

    return experiences


# ══════════════════════════════════════════════════════════════
#  WORK EXPERIENCE SKILL EXTRACTION
#  Extract skills from WORK EXPERIENCE section, not just "Skills" section
# ══════════════════════════════════════════════════════════════

def get_work_experience_section(text):
    """
    Extract the WORK EXPERIENCE section from resume.
    Skills are often embedded in experience descriptions, not in a dedicated section.
    """
    return _extract_experience_section_lines(text)


def clean_skill_lines(lines):
    """
    Remove useless lines from work experience section.
    Keep lines that might contain skill terms.
    """
    if not lines:
        return []
    
    cleaned = []
    noisy_patterns = [
        r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # Month/year lines
        r'^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}',  # Dates
        r'^\d+\s*(?:year|month|week|day)s?',     # Duration
        r'\blimited\b|\bcompany\b|\binc\.?\b',   # Company suffixes
    ]
    
    for line in lines:
        if not line or len(line.strip()) < 3:
            continue
        
        line_lower = line.lower()
        skip = False
        
        for pattern in noisy_patterns:
            if re.search(pattern, line_lower, re.IGNORECASE):
                skip = True
                break
        
        if not skip:
            cleaned.append(line)
    
    return cleaned


# Domain-specific skill keywords for various industries
# Dynamically build from CSV, but can be extended domain-by-domain
WORK_EXPERIENCE_SKILLS = {
    # ═══ Chemical/Process Engineering (PRIMARY FOCUS) ═══
    'hydrometallurgy', 'solvent extraction', 'leaching', 'leaching process',
    'filter press', 'centrifuge filter', 'etp', 'effluent treatment',
    'acid leaching', 'roasting', 'calcination', 'precipitation',
    'flotation', 'crystallization', 'distillation', 'refining',
    'heap leaching', 'pressure leaching', 'stirred tank leaching',
    'counter current decantation', 'ccd', 'gravity separation',
    'thickening', 'filtration', 'membrane separation', 'reverse osmosis',
    'activated carbon', 'ion exchange', 'solvent recovery',
    'metal recovery', 'mineral processing', 'ore processing',
    
    # ═══ Equipment & Plant Operations ═══
    'equipment maintenance', 'plant operations', 'equipment operation',
    'reactor operation', 'column operation', 'batch processing',
    'continuous processing', 'process troubleshooting',
    'instrumentation', 'process control', 'automation',
    
    # ═══ Quality & Safety ═══
    'quality control', 'qc', 'quality assurance', 'qa',
    'testing', 'analytical laboratory', 'lab testing',
    'ehs', 'safety management', 'environmental compliance',
    'sop', 'standard operating procedure',
    
    # ═══ Specialized Technical Skills ═══
    'process optimization', 'process improvement', 'yield optimization',
    'capacity planning', 'production planning', 'resource management',
    'troubleshooting', 'root cause analysis', 'failure analysis',
    'data analysis', 'statistical analysis', 'experimental design',
    
    # ═══ Management & Coordination ═══
    'supervision', 'team leadership', 'project management',
    'shift supervision', 'production supervision', 'batch management',
    'documentation', 'compliance management',
    
    # ═══ Software/Tools (Industry-specific) ═══
    'python', 'java', 'c++', 'matlab', 'sql',
    'excel', 'labview', 'pid control', 'siemens', 'plc',
    'aspen', 'chemcad', 'hysys', 'honeywell', 'dcs',
    'scada', 'mis', 'erp', 'sap', 'oracle',
}


def extract_skills_from_work_experience(text):
    """
    Extract skills mentioned in WORK EXPERIENCE section.
    This is more effective for domain-specific skills that appear in job descriptions.
    """
    if not text:
        return []
    
    # Get work experience section
    experience_lines = get_work_experience_section(text)
    if not experience_lines:
        return []
    
    # Clean the lines
    cleaned_lines = clean_skill_lines(experience_lines)
    if not cleaned_lines:
        return []
    
    # Join and normalize
    experience_text = ' '.join(cleaned_lines).lower()
    
    # Extract matching skills
    matched_skills = []
    seen = set()
    
    for skill in WORK_EXPERIENCE_SKILLS:
        # Match whole words/phrases only
        escaped = re.escape(skill)
        pattern = re.compile(rf'\b{escaped}\b', re.IGNORECASE)
        
        if pattern.search(experience_text):
            normalized = skill.title()  # Title case
            key = normalize_skill_key(normalized)
            if key not in seen:
                seen.add(key)
                matched_skills.append(normalized)
    
    return matched_skills


def normalize_and_expand_skills(skills):
    """
    Normalize skill names and expand abbreviations.
    E.g., 'Etp' -> 'Effluent Treatment Plant'
    """
    if not skills:
        return []
    
    # Abbreviation expansion map
    abbreviation_map = {
        'etp': 'Effluent Treatment Plant',
        'ewtp': 'Effluent Water Treatment Plant',
        'qc': 'Quality Control',
        'qa': 'Quality Assurance',
        'sop': 'Standard Operating Procedure',
        'bom': 'Bill Of Materials',
        'erp': 'Enterprise Resource Planning',
        'iot': 'Internet Of Things',
        'ai': 'Artificial Intelligence',
        'ml': 'Machine Learning',
        'dl': 'Deep Learning',
        'nlp': 'Natural Language Processing',
    }
    
    normalized = []
    seen = set()
    
    for skill in skills:
        skill_lower = skill.lower().strip()
        
        # Check if it's an abbreviation that should be expanded
        if skill_lower in abbreviation_map:
            expanded = abbreviation_map[skill_lower]
            key = normalize_skill_key(expanded)
            if key not in seen:
                seen.add(key)
                normalized.append(expanded)
        else:
            # Keep the skill but ensure it's properly cased
            proper_case = ' '.join(word.capitalize() for word in skill_lower.split())
            key = normalize_skill_key(proper_case)
            if key not in seen:
                seen.add(key)
                normalized.append(proper_case)
    
    return normalized


def extract_skills_from_dataset(text):
    if not text:
        return []
    if not _ensure_skillner_loaded():
        return []
    section_text, has_section = _extract_skill_section_text(text)
    text_for_skillner = section_text if has_section else _build_fast_skillner_text(text)
    if not text_for_skillner:
        return []
    try:
        result = skill_extractor.annotate(text_for_skillner)
    except Exception:
        return []
    results    = result.get('results', {}) if isinstance(result, dict) else {}
    candidates = []
    seen       = set()
    for bucket in ('full_matches', 'ngram_scored'):
        for item in results.get(bucket, []) or []:
            skill_text = _extract_skill_text_from_skillner_item(item)
            if not skill_text:
                continue
            skill_text = re.sub(r'\s+', ' ', skill_text).strip(" \t\r\n\"'")
            if not skill_text or _is_weak_generic_skill(skill_text):
                continue
            key = normalize_skill_key(skill_text)
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append(skill_text)
    return candidates


# ══════════════════════════════════════════════════════════════
#  SINGLE-RESUME EXTRACTION  (updated to include DOB)
# ══════════════════════════════════════════════════════════════
def _extract_resume_record(fname, process_folder, skill_source, skills_list,
                            compiled_skill_matchers=None, fast_response=False):
    """Extract all fields for a single resume file."""
    path = os.path.join(process_folder, fname)
    try:
        text           = extract_text(path)
        name           = extract_name(text)
        contact_number = extract_contact_number(text)
        email          = extract_email_from_resume(text)
        dob            = extract_dob(text)           # ← NEW

        if fast_response:
            gender  = None
            address = None
        else:
            gender  = extract_gender(text, name=name)
            address = extract_address(text)

        # ═══ Enhanced skill extraction with work experience priority ═══
        # Strategy: Try work experience extraction first (domain-specific skills)
        # Then supplement with CSV/dataset methods for broader coverage
        matched_skills = []
        
        # Pass 1: Extract from WORK EXPERIENCE section (domain-specific skills)
        work_exp_skills = extract_skills_from_work_experience(text)
        if work_exp_skills:
            work_exp_skills = normalize_and_expand_skills(work_exp_skills)
            matched_skills.extend(work_exp_skills)
        
        # Pass 2: CSV-based matching (comprehensive skill list)
        if skill_source in {'csv', 'auto'}:
            csv_skills = extract_skills_from_resume(text, skills_list, compiled_skill_matchers)
            if csv_skills:
                # Avoid duplicates with normalized keys
                seen = {normalize_skill_key(s) for s in matched_skills}
                for skill in csv_skills:
                    key = normalize_skill_key(skill)
                    if key not in seen:
                        matched_skills.append(skill)
                        seen.add(key)
        
        # Pass 3: Dataset/skillNer extraction (if no CSV or more skills needed)
        if skill_source in {'dataset', 'auto'}:
            dataset_skills = extract_skills_from_dataset(text)
            if dataset_skills:
                seen = {normalize_skill_key(s) for s in matched_skills}
                for skill in dataset_skills:
                    key = normalize_skill_key(skill)
                    if key not in seen:
                        matched_skills.append(skill)
                        seen.add(key)
        
        # If no skills extracted yet, fall back to standard method
        if not matched_skills:
            if skill_source == 'dataset':
                matched_skills = extract_skills_from_dataset(text)
            elif skill_source == 'csv':
                matched_skills = extract_skills_from_resume(text, skills_list, compiled_skill_matchers)
            else:
                matched_skills = extract_skills_from_resume(text, skills_list, compiled_skill_matchers)
                if not matched_skills:
                    matched_skills = extract_skills_from_dataset(text)

        # Infer additional context-based skills
        inferred_skills = infer_context_skills(text, matched_skills)
        if inferred_skills:
            matched_skills.extend(inferred_skills)
        
        # Final cleanup and deduplication
        matched_skills = cleanup_extracted_skills(text, matched_skills)
        experience_profile = extract_professional_experience_profile(text)

        return {
            'file':           fname,
            'name':           name,
            'contact_number': contact_number,
            'email':          email,
            'dob':            dob,            # ← NEW
            'gender':         gender,
            'address':        address,
            'skills':         matched_skills,
            'professional_experience': experience_profile,
        }
    except Exception as exc:
        return {
            'file':           fname,
            'name':           None,
            'contact_number': None,
            'email':          None,
            'dob':            None,           # ← NEW
            'gender':         None,
            'address':        None,
            'skills':         [],
            'professional_experience': [],
            'error':          str(exc),
        }


# ══════════════════════════════════════════════════════════════
#  BATCH RUNNER
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

    try:
        if runtime_validation_enabled:
            from validation import ResumeValidator, print_validation_report
            validator = ResumeValidator()
        else:
            validator = None
    except ImportError:
        print("[!] validation module not found. Running without accuracy checking.")
        validator = None

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log_messages   = []
    _stdout_buffer = getattr(sys.stdout, 'buffer', None)

    def log_message(msg):
        try:
            print(msg)
        except UnicodeEncodeError:
            _stdout_buffer.write(msg.encode('utf-8') + b'\n')
        log_messages.append(msg)

    skills_list = []
    if skill_source in {'csv', 'auto'}:
        skills_list = load_skills_from_csv(SKILLS_CSV)
    compiled_skill_matchers = build_skill_matchers(skills_list)

    if skill_source == 'dataset' or (skill_source == 'auto' and not compiled_skill_matchers):
        _ensure_skillner_loaded()
    if not fast_response_mode:
        _ensure_names_dataset_loaded()

    if fast_response_mode and skill_source == 'auto' and compiled_skill_matchers:
        skill_source = 'csv'
    results = []

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
            rng          = random.Random(random_seed)
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
        log_message(f"[*] Skill source: auto (csv first, dataset fallback | csv={len(skills_list)})")
    log_message(f"[*] Processing {len(resume_files)} resume file(s) from: {PROCESS_FOLDER}")
    log_message(f"[*] Workers: {max_workers}\n")
    if max_files > 0:
        mode = "random sample" if random_order else "first files"
        log_message(f"[*] Limit: {len(resume_files)} file(s), mode={mode}, seed={random_seed}")
    if fast_response_mode:
        log_message("[*] Fast-response mode: ON (validation off, gender/address skipped)")
    if disable_validation:
        log_message("[INFO] Validation disabled via --no-validation")

    col_w  = {'#': 4, 'file': 22, 'name': 30, 'phone': 14, 'gender': 8, 'dob': 14, 'email': 38}
    header = (
        f"{'#':<{col_w['#']}} "
        f"{'File':<{col_w['file']}} "
        f"{'Name':<{col_w['name']}} "
        f"{'Phone':<{col_w['phone']}} "
        f"{'Gender':<{col_w['gender']}} "
        f"{'DOB':<{col_w['dob']}} "
        f"Email"
    )
    log_message(header)
    log_message("─" * 135)

    stats = {
        'total': len(resume_files), 'successful': 0, 'errors': 0,
        'missing_name': 0, 'missing_email': 0, 'missing_phone': 0,
        'missing_dob': 0, 'skills_found': 0,
    }

    def _log_record(i, record):
        fname          = record.get('file', '')
        name           = record.get('name')
        contact_number = record.get('contact_number')
        gender         = record.get('gender')
        dob            = record.get('dob')
        email          = record.get('email')
        address        = record.get('address')
        matched_skills = record.get('skills') or []

        name_col   = (name           or '❌ NOT FOUND')[:col_w['name']   - 1]
        phone_col  = (contact_number or '❌ NOT FOUND')[:col_w['phone']  - 1]
        gender_col = (gender         or '❌ N/A'      )[:col_w['gender'] - 1]
        dob_col    = (dob            or '❌ N/A'      )[:col_w['dob']    - 1]
        email_col  = email or '❌ NOT FOUND'

        log_message(
            f"  {i:<{col_w['#']}} "
            f"{fname:<{col_w['file']}} "
            f"{name_col:<{col_w['name']}} "
            f"{phone_col:<{col_w['phone']}} "
            f"{gender_col:<{col_w['gender']}} "
            f"{dob_col:<{col_w['dob']}} "
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
                fname, PROCESS_FOLDER, skill_source, skills_list,
                compiled_skill_matchers, fast_response_mode,
            )
            results.append(record)
            if record.get('error'):
                stats['errors'] += 1
                log_message(f"  {i:<{col_w['#']}} {fname:<{col_w['file']}} ❌ Error: {record['error']}")
                continue
            stats['successful'] += 1
            if not record.get('name'):            stats['missing_name']  += 1
            if not record.get('email'):           stats['missing_email'] += 1
            if not record.get('contact_number'):  stats['missing_phone'] += 1
            if not record.get('dob'):             stats['missing_dob']   += 1
            if record.get('skills'):              stats['skills_found']  += 1
            _log_record(i, record)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_meta = {
                executor.submit(
                    _extract_resume_record, fname, PROCESS_FOLDER, skill_source,
                    skills_list, compiled_skill_matchers, fast_response_mode,
                ): (i, fname)
                for i, fname in indexed_files
            }
            for future in as_completed(future_to_meta):
                i, fname = future_to_meta[future]
                try:
                    record = future.result()
                except Exception as exc:
                    record = {
                        'file': fname, 'name': None, 'contact_number': None,
                        'email': None, 'dob': None, 'gender': None,
                        'address': None, 'skills': [], 'error': str(exc),
                    }
                results.append(record)
                if record.get('error'):
                    stats['errors'] += 1
                    log_message(f"  {i:<{col_w['#']}} {fname:<{col_w['file']}} ❌ Error: {record['error']}")
                    continue
                stats['successful'] += 1
                if not record.get('name'):            stats['missing_name']  += 1
                if not record.get('email'):           stats['missing_email'] += 1
                if not record.get('contact_number'):  stats['missing_phone'] += 1
                if not record.get('dob'):             stats['missing_dob']   += 1
                if record.get('skills'):              stats['skills_found']  += 1
                _log_record(i, record)

    # ── Validation ─────────────────────────────────────────────
    validation_summary = None
    if validator and results:
        validation_summary = validator.validate_batch(results)
        log_message("\n" + "="*135)
        os.makedirs(os.path.dirname(VALIDATION_JSON), exist_ok=True)
        with open(VALIDATION_JSON, 'w', encoding='utf-8') as vf:
            json.dump(validation_summary, vf, indent=2, ensure_ascii=False)
        log_message(f"💾 Validation report saved → {VALIDATION_JSON}")

    # ── Save JSON ───────────────────────────────────────────────
    results.sort(key=lambda item: natural_file_sort_key(item.get('file', '')))
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as jf:
        json.dump(results, jf, indent=2, ensure_ascii=False)

    # ── Summary ─────────────────────────────────────────────────
    log_message("\n" + "─" * 135)
    log_message("📊 PROCESSING SUMMARY:")
    log_message(f"   Total files processed : {stats['total']}")
    log_message(f"   Successfully parsed   : {stats['successful']} ({stats['successful']/stats['total']*100:.1f}%)")
    log_message(f"   Extraction errors     : {stats['errors']} ({stats['errors']/stats['total']*100:.1f}%)")
    log_message(f"\n📋 EXTRACTION QUALITY:")
    pct = lambda found: f"{found}/{stats['total']} ({found/stats['total']*100:.1f}%)"
    log_message(f"   Names found    : {pct(stats['total'] - stats['missing_name'])}")
    log_message(f"   Emails found   : {pct(stats['total'] - stats['missing_email'])}")
    log_message(f"   Phones found   : {pct(stats['total'] - stats['missing_phone'])}")
    log_message(f"   DOBs found     : {pct(stats['total'] - stats['missing_dob'])}")
    log_message(f"   With skills    : {pct(stats['skills_found'])}")
    log_message(f"\n💾 Results saved → {OUTPUT_JSON}")
    log_message(f"   Log saved      → {LOG_FILE}")
    log_message("✅ Done.\n")

    with open(LOG_FILE, 'w', encoding='utf-8') as lf:
        lf.write('\n'.join(log_messages))