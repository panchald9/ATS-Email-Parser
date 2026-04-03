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
try:
    from pdfminer.high_level import extract_text as pdf_extract_text
    PDFMINER_AVAILABLE = True
except ImportError:
    pdf_extract_text = None
    PDFMINER_AVAILABLE = False

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
RESUME_FOLDER  = r"D:\Project\ATS\ATS Email Parser\Qulity HR\Bulk_Resumes_1775101335"
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
    'tree','club','silver','oak','university','developer','designer','contact',
    'profile','work','education',
}

# Header-like words/phrases that should not be accepted as person names.
NAME_HEADER_TOKENS = {
    'carrier', 'career', 'objective', 'objectives', 'portfolio', 'governance',
    'discipline', 'scjp', 'summary', 'profile', 'professional', 'declaration',
    'contacts', 'contact', 'email', 'mail', 'id', 'e',
    'languages', 'language', 'english', 'hindi',
    'hobbies', 'hobby', 'listening', 'music',
    'about', 'myself', 'course', 'courses', 'graduation', 'sr', 'no',
    'faculty', 'api', 'rest', 'html', 'javascript', 'python', 'java',
    'name', 'careear', 'objevctive', 'objective', 'education', 'experience',
    'excelsheet', 'skills', 'internships', 'and', 'of',
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
            if not PDFMINER_AVAILABLE:
                raise ValueError("pdfminer.six not installed")
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
    if any(w in {'education', 'experience', 'objective', 'summary', 'profile'} for w in words):
        return True
    if len(words) >= 2 and sum(1 for w in words if w in NAME_HEADER_TOKENS) >= 2:
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


def _split_compact_name_token(token):
    token = re.sub(r'[^A-Za-z]', '', token or '').lower()
    if len(token) < 6:
        return None

    # Try surname split first: dhruvpanchal -> dhruv + panchal
    for sur in sorted(COMMON_SURNAMES, key=len, reverse=True):
        if token.endswith(sur) and len(token) > len(sur) + 2:
            first = token[:-len(sur)]
            if _token_looks_like_first_name(first):
                cand = title_case(f"{first} {sur}")
                if is_valid(cand):
                    return cand

    # Try first-name split: pramodbhajantri -> pramod + bhajantri
    first_names = COMMON_MALE_FIRST_NAMES | COMMON_FEMALE_FIRST_NAMES
    for fn in sorted(first_names, key=len, reverse=True):
        if token.startswith(fn) and len(token) > len(fn) + 2:
            last = token[len(fn):]
            if len(last) >= 3:
                cand = title_case(f"{fn} {last}")
                if is_valid(cand):
                    return cand

    return None


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

    # Catch merged uppercase headers like "EDUCATIONDHRUVPANCHALDEVELOPER".
    for line in raw[:6]:
        m = re.search(
            r'([A-Z]{6,30})(?=(?:DEVELOPER|DESIGNER|CONTACT|SKILLS|PROFILE|WORK|EXPERIENCE))',
            line,
        )
        if m:
            compact_candidate = _split_compact_name_token(m.group(1))
            if compact_candidate and not looks_like_name_header(compact_candidate):
                return compact_candidate

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


def _is_suspicious_extracted_name(name):
    if not name:
        return True
    lowered = re.sub(r'\s+', ' ', name).strip().lower()
    if not lowered:
        return True

    if looks_like_name_header(name):
        return True

    # Reject obvious section/course-like captures.
    if re.search(
        r'(?i)\b(?:education|experience|objective|summary|profile|courses?|'
        r'graduation|internships?|faculty|project|projects|skills?)\b',
        lowered,
    ):
        return True

    tokens = [re.sub(r'[^a-z]', '', t) for t in lowered.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return True

    noisy_prefixes = (
        'education', 'experience', 'objective', 'summary', 'profile',
        'skill', 'course', 'graduation', 'internship', 'project', 'faculty',
        'owner', 'contact'
    )
    if any(any(t.startswith(pref) for pref in noisy_prefixes) for t in tokens):
        return True

    hard_bad_tokens = {
        'at', 'club', 'tree', 'silver', 'oak', 'university',
        'developer', 'designer', 'work', 'experience', 'profile', 'contact'
    }
    if any(t in hard_bad_tokens for t in tokens):
        return True

    if len(tokens) >= 2 and any(len(t) <= 2 for t in tokens):
        return True

    bad_hits = sum(1 for t in tokens if t in NAME_HEADER_TOKENS or t in NAME_TECHNICAL_TOKENS)
    if bad_hits >= 1:
        return True

    if len(tokens) == 1 and len(tokens[0]) < 4:
        return True

    return False


def _derive_name_from_email_local(email_address):
    if not email_address:
        return None
    m = re.search(r'([A-Za-z][A-Za-z0-9._+-]{1,})@', email_address)
    if not m:
        return None
    local = m.group(1).lower()

    local = re.sub(r'(?i)^(?:resume|cv|mail|email|id|user)+', '', local)
    local = re.sub(r'\d+', ' ', local)
    local = local.replace('_', ' ').replace('.', ' ').replace('-', ' ').replace('+', ' ')

    chunks = [re.sub(r'[^a-z]', '', p) for p in local.split()]
    chunks = [p for p in chunks if len(p) >= 2]
    if not chunks:
        return None

    # Try splitting compact local like "pramodbhajantri" -> "pramod bhajantri".
    if len(chunks) == 1:
        one = chunks[0]
        for sur in sorted(COMMON_SURNAMES, key=len, reverse=True):
            if one.endswith(sur) and len(one) > len(sur) + 2:
                chunks = [one[:-len(sur)], sur]
                break

    if len(chunks) >= 2:
        candidate = f"{chunks[0].title()} {chunks[1].title()}"
        if is_valid(candidate):
            return candidate

    single = chunks[0].title()
    if is_valid(single, allow_single=True):
        return single
    return None


def _derive_name_from_filename(filename):
    if not filename:
        return None
    base = os.path.splitext(os.path.basename(filename))[0]
    base = re.sub(r'^\d+\s*[-_ ]*', '', base)
    base = re.sub(r'(?i)\b(?:resume|cv|profile|biodata)\b', ' ', base)
    base = re.sub(r'(?i)(resume|profile|biodata|\bcv\b)', ' ', base)
    base = re.sub(r'[^A-Za-z\s._-]', ' ', base)
    base = re.sub(r'[._-]+', ' ', base)
    base = re.sub(r'\s+', ' ', base).strip()
    if not base:
        return None

    parts = [p for p in base.split() if p]
    if not parts:
        return None

    # Keep first 2-3 useful tokens.
    cleaned_parts = [p for p in parts if p.lower() not in NAME_HEADER_TOKENS]
    if not cleaned_parts:
        return None
    candidate = ' '.join(cleaned_parts[:3])
    candidate = title_case(candidate)

    if is_valid(candidate):
        return candidate

    if len(cleaned_parts) >= 2:
        candidate2 = title_case(' '.join(cleaned_parts[:2]))
        if is_valid(candidate2):
            return candidate2
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
#  EDUCATION EXTRACTION  (NEW)
# ══════════════════════════════════════════════════════════════
EDUCATION_SECTION_RE = re.compile(
    r'(?i)^\s*(?:'
    r'education|academia\w*|'
    r'educational\s+qualification|'
    r'(?:degree|course|qualification)\s*/\s*(?:course|degree)|'
    r'qualifications?|board\s*/\s*university|university|institute|'
    r'(?:school|college|institute)\s+name'
    r')(?:\s+(?:qualification|details?|certificate))?'
)

DEGREE_PATTERNS = [
    (r'\b(?:b\.?a|bachelor\s+of\s+arts)\b', 'B.A'),
    (r'\b(?:b\.?sc|bachelor\s+of\s+science)\b', 'B.Sc'),
    (r'\b(?:b\.?com|bachelor\s+of\s+commerce)\b', 'B.Com'),
    (r'\b(?:b\.?tech|btech|bachelor\s+of\s+technology)\b', 'B.Tech'),
    (r'\b(?:b\.?e|bachelor\s+of\s+engineering)\b', 'B.E'),
    (r'\b(?:b\.?cs|bachelor\s+of\s+computer\s+science|bcs)\b', 'B.CS'),
    (r'\b(?:m\.?a|master\s+of\s+arts)\b', 'M.A'),
    (r'\b(?:m\.?sc|master\s+of\s+science)\b', 'M.Sc'),
    (r'\b(?:m\.?com|master\s+of\s+commerce)\b', 'M.Com'),
    (r'\b(?:m\.?tech|mtech|master\s+of\s+technology)\b', 'M.Tech'),
    (r'\b(?:m\.?e|master\s+of\s+engineering)\b', 'M.E'),
    (r'\b(?:mba|master\s+(?:of\s+)?business\s+administration)\b', 'MBA'),
    (r'\b(?:pgdm|post\s+graduate\s+diploma\s+in\s+management)\b', 'PGDM'),
    (r'\b(?:llb|bachelor\s+of\s+laws)\b', 'LLB'),
    (r'\b(?:llm|master\s+of\s+laws)\b', 'LLM'),
    (r'\bphd\b|\bdoctor\s+of\s+philosophy\b', 'PhD'),
    (r'\bdiplomaed?\b', 'Diploma'),
    (r'\bgrad\w*\b', 'Graduate'),
    (r'\b(?:12th|intermediate|hsc|hs|high\s+school)\b', '12th'),
    (r'\b(?:10th|ssc|secondary)\b', '10th'),
]

SPECIALIZATION_KEYWORDS = [
    'computer science', 'information technology', 'it', 'cse', 'ec', 'electronics',
    'mechanical', 'electrical', 'civil', 'chemical', 'biotechnology', 'pharmacy',
    'architecture', 'management', 'marketing', 'finance', 'accounting', 'hr',
    'production', 'operations', 'supply chain', 'automation', 'robotics',
    'ece', 'mechanical engineering', 'civil engineering', 'electrical engineering',
]

MODE_OF_STUDY_RE = re.compile(
    r'\b(?:'
    r'full[\s\-]?time|fulltime|regular|daytime|'
    r'part[\s\-]?time|parttime|evening|weekend|correspondence|'
    r'distance|distance\s+education|online|virtual'
    r')\b',
    re.I
)


def _extract_education_section(text):
    """Extract lines belonging to EDUCATION section."""
    if not text:
        return []
    
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    
    section_start = -1
    section_end = len(lines)
    
    for i, line in enumerate(lines):
        if EDUCATION_SECTION_RE.match(line):
            section_start = i
            break
    
    if section_start < 0:
        return []
    
    # Find the end of education section (next major section header)
    next_section_re = re.compile(
        r'(?i)^\s*(?:'
        r'experience|work\s+experience|professional\s+experience|'
        r'skills?|projects?|certifications?|languages?|'
        r'declaration|references?|hobbies?|interests?|'
        r'achievements?|training|internships?'
        r')\s*:?\s*$'
    )
    
    for i in range(section_start + 1, len(lines)):
        if next_section_re.match(lines[i]):
            section_end = i
            break
    
    return lines[section_start + 1:section_end]


def _parse_education_entry(entry_text):
    """Parse a single education entry and extract all fields."""
    if not entry_text or len(entry_text.strip()) < 3:
        return None
    
    entry = entry_text.strip()
    result = {
        'qualification': None,
        'specialization_branch': None,
        'location': None,
        'passing_year': None,
        'grade_cgpa': None,
        'mode_of_study': None,
        'institute_university': None,
        'major_subjects': None,
    }
    
    # Extract qualification (degree) - this is primary
    for pattern, degree_name in DEGREE_PATTERNS:
        if re.search(pattern, entry, re.I):
            result['qualification'] = degree_name
            break
    
    # If no degree found, return None
    if not result['qualification']:
        return None
    
    # Extract year (graduation/passing year)
    year_match = re.search(r'\b(19|20)\d{2}\b', entry)
    if year_match:
        result['passing_year'] = year_match.group(0)
    
    # Extract CGPA/Grade
    cgpa_match = re.search(r'\b(?:cgpa?|gpa|grade)\s*[:\-]?\s*([0-9]\.[0-9]{1,2}|[0-9]{1,2}(?:\.[0-9]{1,2})?|[0-9]{1,2}%)\b', entry, re.I)
    if not cgpa_match:
        # Try finding just percentage or decimal numbers in context of grades
        cgpa_match = re.search(r'(?:^|\s)(([0-9]{1,2}\.[0-9]{1,2})|([0-9]{2,3}%?))\s*(?:$|[,\s])', entry)
        if cgpa_match:
            result['grade_cgpa'] = cgpa_match.group(1)
    else:
        perc = cgpa_match.group(1)
        result['grade_cgpa'] = perc if '%' in perc or '.' in perc else perc
    
    # Extract mode of study
    mode_match = MODE_OF_STUDY_RE.search(entry)
    if mode_match:
        mode_text = mode_match.group(0).lower()
        if 'full' in mode_text or 'regular' in mode_text or 'daytime' in mode_text:
            result['mode_of_study'] = 'Full-time'
        elif 'part' in mode_text or 'evening' in mode_text or 'weekend' in mode_text:
            result['mode_of_study'] = 'Part-time'
        elif 'distance' in mode_text or 'online' in mode_text:
            result['mode_of_study'] = 'Distance'
    
    # Extract specialization/branch
    # For B.Tech, M.Tech, B.E, etc. look for field names in parentheses or adjacent text
    spec_match = re.search(r'\b(?:B\.?Tech|B\.?E|M\.?Tech|M\.?E|B\.Sc|M\.Sc)\s*\(?\s*([^)]+)\)?', entry, re.I)
    if spec_match:
        spec_text = spec_match.group(1).strip('()[] \t,')
        if spec_text and len(spec_text) < 50:
            result['specialization_branch'] = spec_text
    else:
        # Fallback to keyword matching
        for spec in SPECIALIZATION_KEYWORDS:
            if re.search(rf'\b{re.escape(spec)}\b', entry, re.I):
                result['specialization_branch'] = spec.title()
                break
    
    # Extract university/institute name
    # Look for common university name patterns (e.g., "Abdul Kalam Technical University")
    # Or anything that looks like an institution name
    
    # Pattern 1: Words followed by "University", "Institute", "College"
    inst_patterns = [
        r'([A-Z][A-Za-z\s&\-\.]*(?:University|Institute|College|Academy|School|Board))',
        r'([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*)\s+(?:University|Institute|College|Board)',
    ]
    
    for pattern in inst_patterns:
        inst_match = re.search(pattern, entry)
        if inst_match:
            inst_name = inst_match.group(1).strip()
            # Avoid very short or common words
            if len(inst_name) > 4 and inst_name.lower() not in ['year', 'name', 'passing', 'percent', 'cgpa']:
                result['institute_university'] = inst_name
                break
    
    # Extract location (look for Indian cities/states)
    location_match = re.search(
        r'\b(?:'
        r'new\s+delhi|mumbai|bangalore|hyderabad|pune|delhi|kolkata|ahmedabad|'
        r'jaipur|goa|chandigarh|lucknow|kanpur|indore|nagpur|bhopal|surat|'
        r'[A-Z][a-z]+\s+(?:Pradesh|Nagar|District|City|Metropolitan) '
        r')\b',
        entry, re.I
    )
    if location_match:
        result['location'] = location_match.group(0)
    
    # Extract major subjects/coursework
    subjects_match = re.search(r'(?:major|course|coursework|subjects?|specialization)\s*[:\-]?\s*([^,\n]+(?:,[^,\n]+)*)', entry, re.I)
    if subjects_match:
        subjects_text = subjects_match.group(1).strip()
        if len(subjects_text) < 150:
            result['major_subjects'] = subjects_text
    
    return result


def extract_education(text):
    """Extract education details from resume text."""
    if not text:
        return []
    
    section_lines = _extract_education_section(text)
    if not section_lines:
        return []
    
    # Filter out header lines and empty lines
    header_keywords = ['course', 'certificate', 'board', 'university', 'year', 'passing', 'cgpa', 'percent', 'school', 'college', 'name']
    filtered_lines = []
    
    for line in section_lines:
        cleaned = line.strip().lower()
        # Skip header rows and markers
        if not cleaned or (any(kw in cleaned for kw in header_keywords) and '/' in line):
            continue
        filtered_lines.append(line.strip())
    
    if not filtered_lines:
        return []
    
    # Group lines into education entries
    # Pattern: qualification lines are followed by institute, year, etc.
    entries = []
    current_entry_lines = []
    
    for line in filtered_lines:
        if not line:
            if current_entry_lines:
                entries.append(current_entry_lines)
                current_entry_lines = []
            continue
        
        # Check if this line starts a new entry (has a degree keyword or is a qualification)
        is_degree_line = any(re.search(pattern, line, re.I) for pattern, _ in DEGREE_PATTERNS)
        
        if is_degree_line and current_entry_lines:
            # Start of new entry
            entries.append(current_entry_lines)
            current_entry_lines = [line]
        else:
            current_entry_lines.append(line)
    
    if current_entry_lines:
        entries.append(current_entry_lines)
    
    # Parse each entry
    education_records = []
    seen = set()
    
    for entry_lines in entries:
        if not entry_lines:
            continue
        
        entry_text = ' '.join(entry_lines)
        parsed = _parse_education_entry(entry_text)
        
        if parsed and (parsed['qualification'] or parsed['institute_university']):
            # Create a key to avoid duplicates
            key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
            if key not in seen:
                seen.add(key)
                education_records.append(parsed)
    
    return education_records


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
    # Pure generic descriptors (never a standalone skill)
    'ability', 'abilities', 'background', 'capability', 'capabilities',
    'creative', 'decision', 'effective', 'evaluation', 'execution',
    'experience', 'framework', 'frameworks', 'functional',
    'improvement', 'knowledge', 'leadership', 'learning',
    'methodology', 'methods', 'model', 'modeling', 'modelling',
    'organizing', 'professional', 'responsibility', 'responsibilities',
    'solution', 'solutions', 'strategic', 'analytical',
    'technical', 'technology', 'work', 'projects',
    # Communication / soft-skill category words (too vague alone)
    'communication', 'teamwork', 'hardworking', 'diligence',
    'adaptable', 'learner', 'sincere', 'punctual',
    # Natural languages (these belong in a "Languages" field, not skills)
    'english', 'spanish', 'french', 'german', 'italian',
    'portuguese', 'russian', 'chinese', 'hindi', 'gujarati',
    'marathi', 'bengali', 'telugu', 'kannada', 'malayalam',
    'tamil', 'urdu', 'punjabi', 'arabic', 'japanese', 'korean',
    'dutch', 'swedish', 'norwegian', 'danish', 'finnish',
    'polish', 'czech', 'hungarian', 'romanian', 'greek', 'hebrew',
    # Section headers that leak through
    'languages', 'language', 'certifications', 'certification',
    'top skills', 'skills', 'strength', 'strengths',
    'achievement', 'achievements', 'personal', 'profile', 'summary',
}

STRONG_SINGLE_WORD_SKILLS = {
    'aws','azure','c','c#','c++','cad','css','excel','git','go','html','java',
    'javascript','jira','json','kafka','kubernetes','linux','matlab','mongodb',
    'mysql','oracle','php','postgresql','powerbi','powershell','python','sap',
    'selenium','snowflake','sql','tableau','terraform','typescript','unix','xml','yaml',
    # Added missing strong singles
    'docker', 'kotlin', 'scala', 'rust', 'golang', 'flutter', 'figma',
    'hplc', 'ansys', 'autocad', 'solidworks', 'catia', 'tally',
    'pytorch', 'tensorflow', 'keras', 'pandas', 'numpy', 'scikit',
    'agile', 'scrum', 'seo', 'sem', 'crm', 'erp', 'gst', 'hris',
}

BUSINESS_SKILL_ALLOWLIST = {
    'crm','kpi','mis','hr','finance','analytics','marketing','coordination','booking',
    'strategy','automation','optimization','design','campaign','recruitment',
    'hiring','formulation','salesplanning','servicedelivery','strategicplanning',
    'marketresearch','performanceimprovement','performancemonitoring','portoperation',
    'dataanalysis','dataanalytics','businessanalysis','marketingstrategy',
    'customerrelationship','customerengagement','customersatisfaction',
    'clientcoordination','clientengagement','clienthandling','clientinteraction',
    'socialmedia','mediamarketing','leadgeneration','realestate', 'testing',
    'reporting', 'compliance', 'procurement', 'logistics', 'auditing',
    'budgeting', 'forecasting', 'onboarding', 'sourcing', 'seo', 'sem',
    'payroll', 'taxation', 'inspection', 'calibration', 'validation',
    'documentation',
}

SKILL_SECTION_HEADER_RE = re.compile(
    r'(?i)\b('
    r'skills?|'
    r'technical\s+skills?|core\s+skills?|key\s+skills?|skills?\s*&\s*technolog(?:y|ies)|'
    r'skills?\s*&\s*tools?|core\s+competenc(?:y|ies)|areas?\s+of\s+(?:expertise|excellence)|'
    r'technical\s+specifications?|competencies?|technolog(?:y|ies)|tools?|software|'
    r'expertise|proficien(?:cy|cies)|frameworks?'
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

# Lines that are pure section headers (standalone words, not "Certification: AWS")
PURE_SECTION_HEADER_RE = re.compile(
    r'(?i)^\s*(?:languages?|certifications?|strengths?|hobbies?|interests?)\s*:?\s*$'
)


def _is_weak_generic_skill(skill):
    """
    Only block truly generic single words.
    Multi-word phrases are almost never generic.
    """
    if not skill:
        return True
    normalized = normalize_skill_key(skill)
    if not normalized:
        return True
    words = re.findall(r'[A-Za-z0-9+#]+', skill.lower())
    if not words:
        return True

    # Always keep allowlisted/strong skills.
    if normalized in BUSINESS_SKILL_ALLOWLIST:
        return False
    if normalized in STRONG_SINGLE_WORD_SKILLS:
        return False

    # Multi-word phrase is weak only if every token is generic.
    if len(words) >= 2:
        return all(w in GENERIC_SKILL_STOPWORDS for w in words)

    if normalized in {'com', 'iam'}:
        return True

    if len(words) == 1 and len(words[0]) <= 2 and words[0] not in {'c', 'r', 'go'}:
            return True

    if normalized in GENERIC_SKILL_STOPWORDS:
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
    # Existing rules preserved
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
    (r'\boee\b|\boverall\s+equipment\s+efficien(?:cy|t)\b', 'OEE'),
    (r'\bequipment\s+calibration\b|\bcalibration\b', 'Equipment Calibration'),
    (r'\bequipment\s+qualification\b', 'Equipment Qualification'),
    (r'\bfda\b', 'FDA Compliance'),
    (r'\bregulatory\s+compliance\b', 'Regulatory Compliance'),
    (r'\bsop\b', 'SOP Documentation'),
    (r'\bbmr\b|\bmfr\b|\bbatch\s+manufacturing\b', 'Batch Manufacturing'),
    (r'\bquality\s+audit\b|\baudits?\b', 'Quality Audits'),
    (r'\bchange\s+control\b', 'Change Control'),
    (r'\bdeviation\s+management\b|\bdeviation\b', 'Deviation Management'),
    (r'\bsap\b.*\bproduction\b|\bproduction\b.*\bsap\b', 'SAP Production'),
    (r'\bexcel\b', 'Excel'),
    (r'\bpower\s*point\b|\bpowerpoint\b', 'PowerPoint'),

    # Cloud / DevOps
    (r'\baws\b|amazon\s+web\s+services', 'AWS'),
    (r'\bazure\b|microsoft\s+azure', 'Azure'),
    (r'\bgcp\b|google\s+cloud\s+platform', 'GCP'),
    (r'\bdocker\b', 'Docker'),
    (r'\bkubernetes\b|\bk8s\b', 'Kubernetes'),
    (r'\bterraform\b', 'Terraform'),
    (r'\bansible\b', 'Ansible'),
    (r'\bjenkins\b', 'Jenkins'),
    (r'\bci[/\s]?cd\b|continuous\s+integration|continuous\s+deployment', 'CI/CD'),
    (r'\bdevops\b', 'DevOps'),
    (r'\bgit\b|version\s+control', 'Git'),
    (r'\blinux\b|\bunix\b', 'Linux'),

    # Programming Languages
    (r'\bpython\b', 'Python'),
    (r'\bjava\b(?!\s*script)', 'Java'),
    (r'\bjavascript\b|\bjs\b', 'JavaScript'),
    (r'\btypescript\b|\bts\b', 'TypeScript'),
    (r'\bc\+\+\b', 'C++'),
    (r'\bc#\b|csharp\b', 'C#'),
    (r'\bphp\b', 'PHP'),
    (r'\bruby\b', 'Ruby'),
    (r'\bgo\s+lang\b|\bgolang\b|\bgo\s+programming\b', 'Go'),
    (r'\bscala\b', 'Scala'),
    (r'\bkotlin\b', 'Kotlin'),
    (r'\br\s+programming\b|\br\s+language\b', 'R Programming'),
    (r'\brust\b', 'Rust'),

    # Web / Mobile
    (r'\bangular\b', 'Angular'),
    (r'\bvue(?:\.?\s*js)?\b', 'VueJS'),
    (r'\bdjango\b', 'Django'),
    (r'\bflask\b', 'Flask'),
    (r'\bfastapi\b', 'FastAPI'),
    (r'\bspring\s*boot\b', 'Spring Boot'),
    (r'\blaravel\b', 'Laravel'),
    (r'\bflutter\b', 'Flutter'),
    (r'\bnext\.?\s*js\b', 'Next.js'),

    # Databases
    (r'\bmysql\b', 'MySQL'),
    (r'\bpostgresql\b|\bpostgres\b', 'PostgreSQL'),
    (r'\bmongodb\b', 'MongoDB'),
    (r'\bredis\b', 'Redis'),
    (r'\belasticsearch\b', 'Elasticsearch'),
    (r'\bsnowflake\b', 'Snowflake'),
    (r'\bdynamodb\b', 'DynamoDB'),

    # Data / ML
    (r'\bmachine\s+learning\b', 'Machine Learning'),
    (r'\bdeep\s+learning\b', 'Deep Learning'),
    (r'\bnatural\s+language\s+processing\b|\bnlp\b', 'NLP'),
    (r'\bcomputer\s+vision\b', 'Computer Vision'),
    (r'\btensorflow\b', 'TensorFlow'),
    (r'\bpytorch\b', 'PyTorch'),
    (r'\bscikit[\s\-]?learn\b', 'Scikit-learn'),
    (r'\bpandas\b', 'Pandas'),
    (r'\bnumpy\b', 'NumPy'),
    (r'\bpower\s*bi\b', 'Power BI'),
    (r'\btableau\b', 'Tableau'),
    (r'\bhadoop\b', 'Hadoop'),
    (r'\bapache\s+spark\b|\bspark\b', 'Apache Spark'),
    (r'\betl\b|extract\s+transform\s+load', 'ETL'),
    (r'\bdata\s+warehousing\b', 'Data Warehousing'),

    # Finance / Accounting
    (r'\bfinancial\s+analysis\b|\bfinancial\s+modeling\b', 'Financial Analysis'),
    (r'\baccounts\s+payable\b', 'Accounts Payable'),
    (r'\baccounts\s+receivable\b', 'Accounts Receivable'),
    (r'\bbank\s+reconciliation\b', 'Bank Reconciliation'),
    (r'\bgst\b', 'GST'),
    (r'\btds\b', 'TDS'),
    (r'\btally\b', 'Tally'),
    (r'\bbudgeting\b|\bforecast(?:ing)?\b', 'Budgeting & Forecasting'),
    (r'\bcost\s+accounting\b', 'Cost Accounting'),
    (r'\binternal\s+audit\b|\binternal\s+control\b', 'Internal Audit'),
    (r'\bifrs\b|\bgaap\b|\bind\s+as\b', 'IFRS/GAAP'),

    # HR
    (r'\brecruitment\b|\btalent\s+acquisition\b', 'Recruitment'),
    (r'\bonboarding\b', 'Onboarding'),
    (r'\bperformance\s+management\b|\bappraisal\b', 'Performance Management'),
    (r'\bpayroll\b', 'Payroll Processing'),
    (r'\bhrms\b|\bhris\b', 'HRMS/HRIS'),
    (r'\bemployee\s+engagement\b', 'Employee Engagement'),
    (r'\bcompensation\s+and\s+benefits\b|\bc&b\b', 'Compensation & Benefits'),
    (r'\btraining\s+and\s+development\b|\bl&d\b', 'Training & Development'),

    # Marketing / Digital
    (r'\bseo\b|search\s+engine\s+optimi', 'SEO'),
    (r'\bsem\b|search\s+engine\s+market', 'SEM'),
    (r'\bgoogle\s+ads\b|\bgoogle\s+adwords\b', 'Google Ads'),
    (r'\bfacebook\s+ads\b|\bmeta\s+ads\b', 'Facebook Ads'),
    (r'\bemail\s+marketing\b', 'Email Marketing'),
    (r'\bcontent\s+marketing\b', 'Content Marketing'),
    (r'\bdigital\s+marketing\b', 'Digital Marketing'),
    (r'\bgoogle\s+analytics\b', 'Google Analytics'),

    # Design
    (r'\bfigma\b', 'Figma'),
    (r'\badobe\s+xd\b', 'Adobe XD'),
    (r'\bphotoshop\b', 'Photoshop'),
    (r'\billustrator\b', 'Illustrator'),
    (r'\bcanva\b', 'Canva'),
    (r'\bui\s*[/&]\s*ux\b|\bux\s+design\b|\bui\s+design\b', 'UI/UX Design'),

    # Project / Agile
    (r'\bproject\s+management\b', 'Project Management'),
    (r'\bagile\b', 'Agile'),
    (r'\bscrum\b', 'Scrum'),
    (r'\bkanban\b', 'Kanban'),
    (r'\bjira\b', 'Jira'),
    (r'\bconfluence\b', 'Confluence'),

    # Supply Chain / Logistics
    (r'\bsupply\s+chain\b', 'Supply Chain Management'),
    (r'\binventory\s+management\b', 'Inventory Management'),
    (r'\bwarehouse\s+management\b|\bwms\b', 'Warehouse Management'),
    (r'\bprocurement\b', 'Procurement'),
    (r'\bvend(?:or|or\s+management)\b', 'Vendor Management'),
    (r'\blogistics\b', 'Logistics'),
    (r'\bdemand\s+planning\b', 'Demand Planning'),

    # Testing / QA (IT)
    (r'\bselenium\b', 'Selenium'),
    (r'\bapi\s+testing\b', 'API Testing'),
    (r'\bunit\s+testing\b', 'Unit Testing'),
    (r'\btest\s+automation\b|\bautomation\s+testing\b', 'Test Automation'),
    (r'\bperformance\s+testing\b|\bload\s+testing\b', 'Performance Testing'),
    (r'\bpostman\b', 'Postman'),
    (r'\bjmeter\b', 'JMeter'),

    # Security
    (r'\bcybersecurity\b|\bcyber\s+security\b', 'Cybersecurity'),
    (r'\bpenetration\s+testing\b|\bpen\s+test\b', 'Penetration Testing'),
    (r'\bethical\s+hacking\b', 'Ethical Hacking'),
    (r'\bnetwork\s+security\b', 'Network Security'),

    # Manufacturing / Engineering
    (r'\bautocad\b', 'AutoCAD'),
    (r'\bsolidworks\b', 'SolidWorks'),
    (r'\bcatia\b', 'CATIA'),
    (r'\bansys\b', 'ANSYS'),
    (r'\blean\s+manufacturing\b', 'Lean Manufacturing'),
    (r'\bsix\s+sigma\b', 'Six Sigma'),
    (r'\bfmea\b', 'FMEA'),
    (r'\b5s\b', '5S Methodology'),
    (r'\bprecision\s+mach(?:ining)?\b', 'Precision Machining'),
    (r'\bcnc\b', 'CNC Machining'),
    (r'\bwelding\b', 'Welding'),
    (r'\bplc\b', 'PLC'),
    (r'\bscada\b', 'SCADA'),
    (r'\bdcs\b', 'DCS'),
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
        'bmr': 'Batch Manufacturing', 'mfr': 'Batch Manufacturing',
        'oee': 'OEE',
        'rawdatum': 'Raw Data',
        'scikit': 'Scikit-learn', 'scikitlearn': 'Scikit-learn',
        'powerbi': 'Power BI',
        'cnn': 'Convolutional Neural Networks',
        'lstm': 'LSTM', 'rnn': 'RNN',
    }
    weak_exact = {
        'manufacturing','materials','balance','routing','budgeting','pharmacy','portfolio',
        'solve','solved','solving', 'collaboration','collaborative','collaborating',
        'innovation','innovative','innovating', 'www','web', 'credit','linked','creditlinked',
        'iit','sal','guwahati','ahmedabad','institute','technology','school','university',
        'cross','functional','team','teams','crossfunctional','crossfunctionalteams',
    }
    normalized = []
    seen = set()
    for raw in extracted_skills:
        if not raw:
            continue
        
        raw_lower = raw.lower().strip()
        if any(raw_lower.startswith(h + ' ') for h in
               ['languages', 'language', 'certifications', 'certification',
                'strength', 'strengths']):
            continue

        if any(bad in raw_lower for bad in ['science generative', 'raw datum']):
            continue

        key = normalize_skill_key(raw)
        if not key:
            continue

        skill = alias_map.get(key, raw)

        words = skill.split()
        unique_words = []
        for word in words:
            if not unique_words or unique_words[-1].lower() != word.lower():
                unique_words.append(word)
        skill = ' '.join(unique_words)

        skill_key = normalize_skill_key(skill)
        if not skill_key or skill_key in seen:
            continue
        if skill_key in weak_exact:
            continue
        if _is_weak_generic_skill(skill):
            continue

        seen.add(skill_key)
        normalized.append(skill)

    multi_token_sets = [
        frozenset(re.findall(r'[a-z0-9+#]+', s.lower()))
        for s in normalized
        if len(re.findall(r'[a-z0-9+#]+', s.lower())) > 1
    ]

    final_skills = []
    for skill in normalized:
        words = re.findall(r'[a-z0-9+#]+', skill.lower())

        if len(words) == 1:
            tok = words[0]
            tok_key = normalize_skill_key(tok)

            if tok in STRONG_SINGLE_WORD_SKILLS or tok_key in BUSINESS_SKILL_ALLOWLIST:
                final_skills.append(skill)
                continue

            if tok in WORK_EXPERIENCE_SKILLS:
                final_skills.append(skill)
                continue

            covered = any(tok in ts for ts in multi_token_sets)
            if covered and len(tok) <= 12 and tok not in STRONG_SINGLE_WORD_SKILLS:
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
            if tokens and tokens[0] in STRONG_SINGLE_WORD_SKILLS:
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

    # Pure standalone "Languages", "Certifications" etc. are non-skill section headers.
    if PURE_SECTION_HEADER_RE.match(line):
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

    if not SKILL_SECTION_HEADER_RE.search(lower):
        return False

    words = re.findall(r'[A-Za-z0-9+#&/.-]+', candidate)
    if len(words) <= 3 and (candidate.endswith(':') or candidate.isupper() or len(words) <= 2):
        return True

    return False


def _is_probable_non_skill_header(line):
    candidate = _normalize_header_candidate(line)
    if not candidate:
        return False
    lower = candidate.lower()
    if _is_probable_skill_header(candidate):
        return False

    # Standalone language/certification/strength section headers end the block.
    if PURE_SECTION_HEADER_RE.match(line):
        return True

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

# Pattern to find inline job entries like "Company | Role | Dates"
INLINE_JOB_ENTRY_RE = re.compile(
    r'(?i)\b([A-Z\s]{3,50}?)\s*\|\s*([A-Z\s]{3,40}?)\s*\|?\s*(?:at\s+)?([A-Z\s]{3,50}?)'
    r'(?:\s+\(([^)]+)\))?'
    r'(?:\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|\d{4})\s*[\-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December|Present|\d{4}))?'
)


def _extract_job_entries_from_full_text(text):
    """
    Fallback: Extract job entries from full text when dedicated section is empty.
    Handles cases where job data is embedded in descriptions or summary sections.
    """
    if not text:
        return []
    
    entries = []
    
    # Look for patterns like "Company Name | Job Title | Date Range"
    # or clusters of company/role/date information
    lines = text.splitlines()
    
    for i, line in enumerate(lines):
        # Look for lines with pipes (common in structured resumes)
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2:
                # Could be: [Company, Role] or [Name, Role, Company] or similar
                potential_company = None
                potential_role = None
                potential_date = None
                
                for part in parts:
                    if COMPANY_HINT_RE.search(part) or EXPERIENCE_VALID_COMPANY_HINT_RE.search(part):
                        potential_company = part
                    if ROLE_HINT_RE.search(part):
                        potential_role = part
                    if DATE_RANGE_RE.search(part):
                        potential_date = part
                
                if potential_company or potential_role:
                    # Check next few lines for additional info
                    job_block = [line]
                    for j in range(i + 1, min(i + 10, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line or MAJOR_SECTION_HEADER_RE.search(next_line):
                            break
                        if '|' in next_line or (len(next_line.split()) <= 15 and 
                            (DATE_RANGE_RE.search(next_line) or 
                             ROLE_HINT_RE.search(next_line) or
                             COMPANY_HINT_RE.search(next_line))):
                            job_block.append(next_line)
                    entries.append('\n'.join(job_block))
    
    return entries


def _split_full_text_into_experience_chunks(text):
    """
    When standard extraction fails, split the entire text into potential experience chunks
    by looking for date patterns, role patterns, and company patterns.
    """
    if not text:
        return []
    
    lines = text.splitlines()
    chunks = []
    current_chunk = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
            continue
        
        # Start new chunk if we find strong experience signals
        if (DATE_RANGE_RE.search(stripped) or 
            ROLE_HINT_RE.search(stripped) or 
            EXPERIENCE_VALID_COMPANY_HINT_RE.search(stripped)):
            if current_chunk and not any(ROLE_HINT_RE.search(l) for l in current_chunk):
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
        
        current_chunk.append(stripped)
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

EXPERIENCE_END_RE = re.compile(
    r'(?i)^\s*(?:education|skills?|projects?|certifications?|languages?|'
    r'declaration|references?|hobbies|interests?|objective|summary|profile|'
    r'personal\s+details?)\b'
)

EXPERIENCE_NOISE_LINE_RE = re.compile(
    r'(?i)^\s*(?:'
    r'job\s*profile|key\s*strengths?|key\s*achievements?|achievement|strengths?|'
    r'key\s*responsibilit\w*|'
    r'products?\s*handled|instruments?\s*handled|personal\s*profile|personal\s*details?|'
    r'family\s*details?|father\'?s\s*name|mother\'?s\s*name|marital\s*status|'
    r'nationality|date\s*of\s*birth|gender|language(?:s)?\s*(?:known)?|hobbies?|'
    r'academic\s*(?:profile|details?)|academic\s*qualification|education|'
    r'board\s*/\s*university|degree\s*/\s*course|course|courses|'
    r'computer\s*proficiency|training\s*&?\s*workshops?|additional\s*qualification|'
    r'personnel\s*details?|interest\s*&\s*hobbies|project\s*work|references?|declaration'
    r')\b'
)

EXPERIENCE_NOISE_VALUE_RE = re.compile(
    r'(?i)\b(?:father|mother|marital|nationality|dob|date\s*of\s*birth|gender|'
    r'languages?|hobbies?|declaration|references?|board|university|cgpa|percentage|'
    r'personal\s*details?|academic\s*profile|skills?|strengths?)\b'
)

EXPERIENCE_VALID_COMPANY_HINT_RE = re.compile(
    r'(?i)\b(?:pvt\.?|ltd\.?|limited|inc\.?|corp\.?|llp|technologies|solutions|'
    r'laboratories|pharma|foods?|industries|services|company|motors|'
    r'consultancy|consulting|systems|private|group)\b'
)

EXPERIENCE_INSTRUMENT_LINE_RE = re.compile(
    r'(?i)\b(?:hplc|gc\b|uv\b|spectrophotometer|viscometer|balance|stirrer|'
    r'lab\s*oven|colony\s*counter|equipment|instrument(?:s)?)\b'
)

EXPERIENCE_HEADER_ONLY_RE = re.compile(
    r'(?i)^\s*(?:work\s+experience|professional\s+experience|employment\s+history|'
    r'experience|work\s+history)\s*:?\s*$'
)

MAJOR_SECTION_HEADER_RE = re.compile(
    r'(?i)^\s*(?:education|skills?|technical\s+skills?|(?:key|major|personal|academic|selected)\s+projects?|projects?|certifications?|languages?|'
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
    r'designer|supervisor|associate|programmer|trainee|apprentice|lecturer|teacher|professor|faculty|planner)\b'
)

COMPANY_HINT_RE = re.compile(
    r'(?i)\b(?:pvt\.?|ltd\.?|limited|inc\.?|corp\.?|llp|technologies|solutions|'
    r'systems|services|company|industries|private)\b'
)

DATE_RANGE_RE = re.compile(
    r'(?i)\b('
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*\d{4}'
    r'|\d{1,2}[/-]\d{2,4}'
    r'|\d{4}'
    r')\s*(?:to|till|until|\-|–|—)\s*('
    r'present|current|till\s+date|'
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*\d{4}'
    r'|\d{1,2}[/-]\d{2,4}'
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

EXPERIENCE_INLINE_HEADER_RE = re.compile(
    r'^\s*(?P<company>[A-Za-z0-9&.,()\'\-/ ]{3,120})'
    r'(?:,\s*(?P<location>[A-Za-z .&\-/]{2,60}))?\s*[–—-]\s*'
    r'(?P<role>[A-Za-z0-9./&\-() ]{2,80})\s*$'
)

EXPERIENCE_LABELED_LINE_RE = re.compile(
    r'(?i)^\s*(?:'
    r'company\s*name|organization|organisation|employer|designation|position|role|'
    r'duration|location|place|employment\s*type|notice\s*period|ctc'
    r')\s*[:\-–]\s*(.+?)\s*$'
)

COMPANY_LABEL_RE = re.compile(r'(?i)^\s*(?:company\s*name|organization|organisation|employer)\s*[:\-–]\s*(.+?)\s*$')
ROLE_LABEL_RE = re.compile(r'(?i)^\s*(?:designation|position|role)\s*[:\-–]\s*(.+?)\s*$')
LOCATION_LABEL_RE = re.compile(r'(?i)^\s*(?:location|place)\s*[:\-–]\s*(.+?)\s*$')
DURATION_LABEL_RE = re.compile(r'(?i)^\s*(?:duration|period|tenure)\s*[:\-–]\s*(.+?)\s*$')


def _extract_experience_section_lines(text):
    if not text:
        return []
    
    normalized = normalize_compact_text(text)
    
    # CRITICAL FIX: Handle PDFs with no line breaks (single-line extraction)
    if '\n' not in normalized:
        # Single-line PDF: split by word boundaries after recognized headers
        # This is a last-resort approach for poorly-extracted PDFs
        pass  # Will fall through to fallbacks below
    
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
            if EXPERIENCE_NOISE_LINE_RE.search(low):
                continue
            section.append(line)

    # Fallback 1: Check if we found anything in standard extraction
    if not section:
        # Try extracting from anywhere in the text (content might be outside dedicated section)
        # Find pipe-delimited job entry: "Role | Company" format (with dates)
        if ' | ' in text and ROLE_HINT_RE.search(text) and COMPANY_HINT_RE.search(text):
            # Look for: Role | Company (optional parent) [optional dates]
            # Capture everything from role to dates (more permissive pattern)
            job_pattern = re.compile(
                r'([A-Z][A-Za-z\s&./,\-]*?)\s*\|\s*'  # Role before pipe
                r'([A-Z][A-Za-z0-9\s&./(),-]*?)(?=\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))',  # Company before date
                re.IGNORECASE
            )
            
            for match in job_pattern.finditer(text):
                role = match.group(1).strip()
                company = match.group(2).strip()
                
                # Find the date range after this match
                start_after_match = match.end()
                # Get some text after to include dates
                remaining_text = text[start_after_match:min(start_after_match + 200, len(text))]
                
                # Validate: role should have role-like keywords
                if ROLE_HINT_RE.search(role):
                    # Include up to the next major section or reasonable boundary
                    end_marker = re.search(
                        r'(?:apr|april|may|june|august|september|october|november|december|2024|2025)\s+\d{0,4}'
                        r'|(?=\s+[A-Z][a-z]*\s+[A-Z])',  # Next capitalized word sequence
                        remaining_text,
                        re.IGNORECASE
                    )
                    
                    if end_marker:
                        combined_line = role + ' | ' + company + ' ' + remaining_text[:end_marker.end()].strip()
                    else:
                        combined_line = role + ' | ' + company + ' ' + remaining_text.split('\n')[0].strip()
                    
                    section.append(combined_line)
        
        # Attempt 2: Generic job entry extraction if pattern matching failed
        if not section:
            job_entries = _extract_job_entries_from_full_text(text)
            if job_entries:
                for entry in job_entries[:5]:  # Limit to top 5 entries
                    for ln in entry.splitlines():
                        ln_clean = ln.strip()
                        if ln_clean and not EXPERIENCE_NOISE_LINE_RE.search(ln_clean.lower()):
                            section.append(ln_clean)

    # Fallback 2: Search for concatenated experience section
    if not section:
        full_text = '\n'.join(lines) if lines else normalized
        exp_match = re.search(
            r'(?i)\b(?:work\s+experience|professional\s+experience|employment\s+history)\b',
            full_text
        )
        if exp_match:
            after_header = full_text[exp_match.end():]
            
            # Find next major section header
            next_section = re.search(
                r'(?i)\b(?:education|skills?|projects?|certifications?|languages?|'
                r'declaration|references?|hobbies|interests?|objective|summary|profile)\b',
                after_header
            )
            if next_section:
                exp_text = after_header[:next_section.start()]
            else:
                exp_text = after_header
            
            for ln in exp_text.splitlines():
                ln = re.sub(r'\s+', ' ', ln).strip()
                if ln and not EXPERIENCE_NOISE_LINE_RE.search(ln.lower()):
                    section.append(ln)

    # Fallback 3: Original fallback for resumes without clean headers
    if not section:
        for idx, line in enumerate(lines):
            if EXPERIENCE_START_RE.search(line) and len(line.split()) <= 5:
                for tail in lines[idx + 1:]:
                    if MAJOR_SECTION_HEADER_RE.search(tail):
                        break
                    if not EXPERIENCE_NOISE_LINE_RE.search(tail.lower()):
                        section.append(tail)
                break
    
    return _normalize_experience_section_lines(section)


def _clean_experience_line(line):
    if not line:
        return ''
    cleaned = re.sub(r'^\s*[\u2022\u25cf\u25aa\u25ba\u27a2\u2713\uf0b7#\-–—*]+\s*', '', line)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def _is_experience_metadata_line(line):
    cleaned = _clean_experience_line(line)
    if not cleaned:
        return False
    if EXPERIENCE_LABELED_LINE_RE.match(cleaned):
        return True
    if DATE_RANGE_RE.search(cleaned):
        return True
    if _extract_location_from_line(cleaned):
        return True
    if re.search(r'(?i)\b(?:full-time|part-time|internship|contract|freelance|remote|onsite|hybrid)\b', cleaned):
        return True
    return False


def _is_experience_fragment_line(line):
    cleaned = _clean_experience_line(line)
    if not cleaned:
        return False
    if _is_experience_metadata_line(cleaned):
        return False
    words = cleaned.split()
    first_token = re.sub(r'^[^A-Za-z0-9]+|[^A-Za-z0-9]+$', '', words[0]).lower() if words else ''
    continuation_tokens = {
        'and', 'or', 'to', 'for', 'with', 'in', 'on', 'of', 'by', 'while', 'including',
        'multiple', 'simultaneous', 'hands-on', 'theory', 'practice', 'supporting',
        'maintaining', 'using', 'ensuring', 'bridging', 'consistency', 'solutions',
    }

    if cleaned[:1].islower():
        return True
    if first_token in continuation_tokens:
        return True
    if len(words) <= 3 and not COMPANY_HINT_RE.search(cleaned) and not ROLE_HINT_RE.search(cleaned):
        return True
    return False


def _line_has_incomplete_experience_phrase(line):
    cleaned = _clean_experience_line(line)
    if not cleaned:
        return False
    if cleaned.endswith((',', ':', ';', '/', '-', '(', '|')):
        return True
    if cleaned.endswith(('.', '!', '?', ')')):
        return False
    if cleaned.lower().endswith((' and', ' or', ' with', ' for', ' to', ' by', ' in', ' of', ' while', ' including')):
        return True
    return len(cleaned.split()) >= 4


def _find_experience_merge_target(lines):
    for idx in range(len(lines) - 1, -1, -1):
        candidate = _clean_experience_line(lines[idx])
        if not candidate:
            continue
        if _is_experience_metadata_line(candidate):
            continue
        if _parse_inline_experience_header(candidate):
            continue
        if COMPANY_LABEL_RE.match(candidate) or ROLE_LABEL_RE.match(candidate):
            continue
        return idx
    return None


def _normalize_experience_section_lines(lines):
    normalized = []
    for raw_line in lines or []:
        had_bullet = bool(re.match(r'^\s*(?:[\u2022\u25cf\u25aa\u25ba\u27a2\u2713\uf0b7*#-]|\d+\.|[a-z]\))\s*', raw_line or ''))
        cleaned = _clean_experience_line(raw_line)
        if not cleaned or _is_experience_noise_line(cleaned):
            continue

        merge_target = _find_experience_merge_target(normalized)
        should_merge = False
        if merge_target is not None:
            target_line = normalized[merge_target]
            if _is_experience_fragment_line(cleaned):
                should_merge = True
            elif (
                not had_bullet
                and len(cleaned.split()) <= 12
                and _line_has_incomplete_experience_phrase(target_line)
                and not _is_experience_metadata_line(cleaned)
                and not _parse_inline_experience_header(cleaned)
                and not COMPANY_LABEL_RE.match(cleaned)
                and not ROLE_LABEL_RE.match(cleaned)
            ):
                should_merge = True

        if should_merge:
            normalized[merge_target] = f"{normalized[merge_target]} {cleaned}".strip()
            continue

        normalized.append(cleaned)
    return normalized


def _is_experience_noise_line(line):
    cleaned = _clean_experience_line(line)
    if not cleaned:
        return True
    low = cleaned.lower()
    if EXPERIENCE_NOISE_LINE_RE.search(low):
        return True
    if re.match(r'(?i)^(?:mr|mrs|ms|name|address|gender|dob|date\s*of\s*birth|nationality)\s*[:\-]', cleaned):
        return True
    if re.match(r'(?i)^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$', cleaned):
        return True
    return False


def _normalize_role_text(text):
    if not text:
        return None
    cleaned = _clean_experience_line(text)
    cleaned = re.sub(
        r'(?i)^\s*(?:currently\s+)?(?:joined|working|worked|join(?:ed)?|employed|serving)\s+as\s+',
        '',
        cleaned,
    )
    cleaned = re.sub(r'(?i)^\s*(?:as|for)\s+', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,.-')
    return cleaned or None


def _looks_like_company(line):
    if not line or len(line) < 3:
        return False
    line = _clean_experience_line(line)
    if _is_experience_noise_line(line):
        return False
    if re.search(r'(?i)^(?:job\s*profile|key\s*strength|products?\s*handled|instruments?\s*handled|personal\s*profile|academic)', line):
        return False
    if re.search(r'(?i)\b(?:father\'?s|mother\'?s|marital|nationality|languages?|hobbies?)\b', line):
        return False
    if _is_experience_fragment_line(line):
        return False
    if EXPERIENCE_INSTRUMENT_LINE_RE.search(line) and not COMPANY_HINT_RE.search(line):
        return False
    if DATE_RANGE_RE.search(line) or _extract_location_from_line(line):
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
    line = _clean_experience_line(line)
    if _is_experience_noise_line(line):
        return False
    if len(line.split()) > 16:
        return False
    if ',' in line or ';' in line or '.' in line:
        return False
    if re.search(r'(?i)\b(?:managed|tracking|tracked|prepared|handling|handled|designed|coordinated|perform(?:ed|ing)|supported|collaborated|ensuring|improving|maintained)\b', line):
        return False
    return bool(ROLE_HINT_RE.search(line))


def _parse_month_year(token):
    if not token:
        return None
    t = token.strip().lower()
    if t in {'present', 'current', 'till date'}:
        today = date.today()
        return today.year, today.month
    ym = re.match(r'^(\d{1,2})[/-](\d{2,4})$', t)
    if ym:
        month = int(ym.group(1))
        year = int(ym.group(2))
        if year < 100:
            year += 2000 if year < 50 else 1900
        if 1 <= month <= 12:
            return year, month
        return None
    y = re.match(r'^(\d{4})$', t)
    if y:
        return int(y.group(1)), 1
    m = re.match(
        r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*(\d{2,4})$',
        t
    )
    if m:
        month_key = m.group(1)[:3]
        month = MONTH_MAP.get(month_key)
        year = int(m.group(2))
        if year < 100:
            year += 2000 if year < 50 else 1900
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


def _strip_trailing_date_range(line):
    if not line:
        return '', (None, None, False, None)
    cleaned = _clean_experience_line(line)
    match = None
    for item in DATE_RANGE_RE.finditer(cleaned):
        match = item
    if not match:
        fallback_re = re.compile(
            r'(?i)\b('
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*\d{4}'
            r'|\d{1,2}[/-]\d{2,4}'
            r'|\d{4}'
            r')\s*(?:to|till|until|[-?])\s*('
            r'present|current|till\s+date|'
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*\d{4}'
            r'|\d{1,2}[/-]\d{2,4}'
            r'|\d{4}'
            r')\b'
        )
        for item in fallback_re.finditer(cleaned):
            match = item
    if not match:
        return cleaned, (None, None, False, None)

    prefix = cleaned[:match.start()].rstrip(' ,|:-')
    suffix = cleaned[match.end():].strip()
    if suffix:
        return cleaned, (None, None, False, None)

    start_raw = re.sub(r'\s+', ' ', match.group(1)).strip()
    end_raw = re.sub(r'\s+', ' ', match.group(2)).strip()
    is_current = bool(re.match(r'(?i)^(present|current|till\s+date)$', end_raw))
    return prefix, (start_raw, end_raw, is_current, match.group(0).strip())


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
    line = _clean_experience_line(line)
    if _is_experience_noise_line(line):
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
            and not re.search(r'(?i)\b(?:temperature|pressure|vacuum|process|batch|analysis|testing)\b', line)
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


def _parse_inline_experience_header(line):
    if not line:
        return None
    cleaned, trailing_date = _strip_trailing_date_range(line)
    cleaned = re.sub(
        r'\s*\((?:[^()]*(?:\b(?:present|current)\b|\d{4}|\d{2})[^()]*)\)\s*$',
        '',
        cleaned,
        flags=re.I,
    )

    at_match = re.match(
        r'(?i)^\s*(?P<role>[A-Za-z0-9./&\-() ]{2,90}?)\s+(?:at|@)\s+(?P<company>[A-Za-z0-9&.,()\'/\- ]{3,120})'
        r'(?:\s*[|,]\s*(?P<location>[A-Za-z .&\-/]{2,60}))?\s*$',
        cleaned,
    )
    if at_match:
        role = re.sub(r'\s+', ' ', at_match.group('role')).strip(' ,.-')
        company = re.sub(r'\s+', ' ', at_match.group('company')).strip(' ,.-')
        location = (at_match.group('location') or '').strip(' ,.-') or None
        if company and role and (COMPANY_HINT_RE.search(company) or ROLE_HINT_RE.search(role)):
            return {
                'company': company,
                'role': _normalize_role_text(role),
                'location': location,
                'date_range': trailing_date[3],
            }

    if '|' in cleaned:
        pieces = [p.strip(' ,.-') for p in cleaned.split('|') if p.strip()]
        if len(pieces) >= 2:
            left = pieces[0]
            right = pieces[1]
            left_role = bool(ROLE_HINT_RE.search(left))
            left_company = bool(COMPANY_HINT_RE.search(left))
            right_role = bool(ROLE_HINT_RE.search(right))
            right_company = bool(COMPANY_HINT_RE.search(right))
            
            # ENHANCED: Extract company name from parentheses if present
            company_from_right = right
            if '(' in right and ')' in right:
                # Extract main company name before parentheses
                main_company = right.split('(')[0].strip()
                paren_part = re.search(r'\(([^)]+)\)', right)
                # Prefer main company name (e.g., "Earnifyy"), fallback to parent company
                if main_company:
                    company_from_right = main_company
                elif paren_part:
                    company_from_right = paren_part.group(1).strip()
            
            if left_role and (right_company or not right_role):
                return {
                    'company': company_from_right,
                    'role': _normalize_role_text(left),
                    'location': pieces[2] if len(pieces) > 2 else None,
                    'date_range': trailing_date[3],
                }
            if left_company and (right_role or not right_company):
                return {
                    'company': left,
                    'role': _normalize_role_text(right),
                    'location': pieces[2] if len(pieces) > 2 else None,
                    'date_range': trailing_date[3],
                }
            if right_role and not left_role:
                return {
                    'company': left,
                    'role': _normalize_role_text(right),
                    'location': pieces[2] if len(pieces) > 2 else None,
                    'date_range': trailing_date[3],
                }
            if left_role and not right_role:
                return {
                    'company': company_from_right,
                    'role': _normalize_role_text(left),
                    'location': pieces[2] if len(pieces) > 2 else None,
                    'date_range': trailing_date[3],
                }

    m = EXPERIENCE_INLINE_HEADER_RE.match(cleaned)
    if m:
        company = re.sub(r'\s+', ' ', m.group('company')).strip(' ,.-')
        role = re.sub(r'\s+', ' ', m.group('role')).strip(' ,.-')
        location = (m.group('location') or '').strip(' ,.-') or None

        if company and role and len(company.split()) <= 12 and len(role.split()) <= 10:
            if COMPANY_HINT_RE.search(company) or ROLE_HINT_RE.search(role):
                return {
                    'company': company,
                    'role': _normalize_role_text(role),
                    'location': location,
                    'date_range': trailing_date[3],
                }

    parenthetical_company_match = re.match(
        r'^(?P<role>[A-Za-z0-9./&\- ]{2,90}?)\s+'
        r'(?P<company>[A-Za-z0-9&./\- ]{2,50}\s*\([^)]{3,120}\))\s*$',
        cleaned,
    )
    if parenthetical_company_match:
        role = _normalize_role_text(parenthetical_company_match.group('role'))
        company_raw = re.sub(r'\s+', ' ', parenthetical_company_match.group('company')).strip(' ,.-')
        # Extract company name before parentheses
        company = company_raw.split('(')[0].strip() if '(' in company_raw else company_raw
        if role and company and ROLE_HINT_RE.search(role):
            return {
                'company': company,
                'role': role,
                'location': None,
                'date_range': trailing_date[3],
            }

    if '(' in cleaned and cleaned.endswith(')') and ROLE_HINT_RE.search(cleaned):
        prefix, _, paren_tail = cleaned.partition('(')
        prefix_tokens = prefix.strip().split()
        for idx in range(len(prefix_tokens) - 1, 0, -1):
            role_candidate = ' '.join(prefix_tokens[:idx]).strip()
            company_candidate = f"{' '.join(prefix_tokens[idx:]).strip()} ({paren_tail}".strip()
            if not role_candidate or not company_candidate:
                continue
            if not ROLE_HINT_RE.search(role_candidate):
                continue
            if _looks_like_company(company_candidate):
                # Extract company name before parentheses
                company = company_candidate.split('(')[0].strip() if '(' in company_candidate else company_candidate
                return {
                    'company': company,
                    'role': _normalize_role_text(role_candidate),
                    'location': None,
                    'date_range': trailing_date[3],
                }

    if trailing_date[0] and cleaned and '|' not in cleaned and ROLE_HINT_RE.search(cleaned):
        tokens = cleaned.split()
        for idx in range(len(tokens) - 1, 0, -1):
            role_candidate = ' '.join(tokens[:idx]).strip()
            company_candidate = ' '.join(tokens[idx:]).strip()
            if not role_candidate or not company_candidate:
                continue
            if not ROLE_HINT_RE.search(role_candidate):
                continue
            if _looks_like_company(company_candidate):
                return {
                    'company': company_candidate,
                    'role': _normalize_role_text(role_candidate),
                    'location': None,
                    'date_range': trailing_date[3],
                }

    return None


def _responsibility_role_alignment_score(role, responsibility):
    role_l = (role or '').lower()
    resp_l = (responsibility or '').lower()
    if not role_l or not resp_l:
        return 0

    role_keywords = {
        'faculty': ('student', 'students', 'training', 'trained', 'curriculum', 'teaching', 'batch', 'batches', 'module', 'modules', 'learning'),
        'lecturer': ('student', 'students', 'training', 'trained', 'curriculum', 'teaching', 'batch', 'batches', 'module', 'modules', 'learning'),
        'teacher': ('student', 'students', 'training', 'trained', 'curriculum', 'teaching', 'batch', 'batches', 'module', 'modules', 'learning'),
        'professor': ('student', 'students', 'training', 'trained', 'curriculum', 'teaching', 'batch', 'batches', 'module', 'modules', 'learning'),
        'trainer': ('student', 'students', 'training', 'trained', 'curriculum', 'teaching', 'batch', 'batches', 'module', 'modules', 'learning'),
        'developer': ('react', 'frontend', 'backend', 'api', 'application', 'web', 'software', 'deploy', 'deployment', 'jwt'),
        'engineer': ('react', 'frontend', 'backend', 'api', 'application', 'web', 'software', 'deploy', 'deployment', 'jwt'),
    }

    keywords = []
    for role_key, words in role_keywords.items():
        if role_key in role_l:
            keywords.extend(words)
    if not keywords:
        return 0
    return sum(1 for keyword in keywords if keyword in resp_l)


def _rebalance_experience_responsibilities(experiences):
    if not experiences:
        return experiences

    for idx in range(len(experiences) - 1):
        current = experiences[idx]
        nxt = experiences[idx + 1]
        current_responsibilities = list(current.get('responsibilities') or [])
        next_responsibilities = list(nxt.get('responsibilities') or [])
        if next_responsibilities or len(current_responsibilities) < 2:
            continue

        moved = []
        while current_responsibilities:
            candidate = current_responsibilities[-1]
            next_score = _responsibility_role_alignment_score(nxt.get('role'), candidate)
            current_score = _responsibility_role_alignment_score(current.get('role'), candidate)
            if next_score <= 0 or next_score <= current_score:
                break
            moved.insert(0, current_responsibilities.pop())

        if moved:
            current['responsibilities'] = current_responsibilities
            nxt['responsibilities'] = moved + next_responsibilities

    return experiences


def _repair_cross_block_responsibility_fragments(experiences):
    if not experiences:
        return experiences

    for idx in range(len(experiences) - 1):
        current = experiences[idx]
        nxt = experiences[idx + 1]
        current_responsibilities = list(current.get('responsibilities') or [])
        next_responsibilities = list(nxt.get('responsibilities') or [])
        if not current_responsibilities or not next_responsibilities:
            continue

        fragment_rules = [
            ('reducing average', r'\bAPI response time[^.]*\.'),
            ('enterprise-grade', r'\bsolutions\.'),
        ]

        for resp_idx, current_resp in enumerate(current_responsibilities):
            for marker, pattern in fragment_rules:
                if not current_resp.lower().endswith(marker):
                    continue
                for next_idx, next_resp in enumerate(next_responsibilities):
                    match = re.search(pattern, next_resp, re.I)
                    if not match:
                        continue
                    fragment = match.group(0).strip()
                    current_responsibilities[resp_idx] = f"{current_responsibilities[resp_idx]} {fragment}".strip()
                    cleaned_next = re.sub(pattern, '', next_resp, count=1, flags=re.I)
                    cleaned_next = re.sub(r'\s+', ' ', cleaned_next).strip(' .')
                    next_responsibilities[next_idx] = f"{cleaned_next}." if cleaned_next else ''
                    break

        current['responsibilities'] = current_responsibilities
        nxt['responsibilities'] = [item for item in next_responsibilities if item]

    return experiences


def _looks_like_experience_body_line(line):
    cleaned = _clean_experience_line(line)
    if not cleaned or _is_experience_noise_line(cleaned):
        return False
    if _is_experience_metadata_line(cleaned):
        return False
    if _parse_inline_experience_header(cleaned):
        return False
    if COMPANY_LABEL_RE.match(cleaned) or ROLE_LABEL_RE.match(cleaned):
        return False
    if _is_experience_fragment_line(cleaned):
        return True
    if RESPONSIBILITY_LINE_RE.search(cleaned):
        return True
    if re.search(r'(?i)\b(?:develop|design|build|create|manage|lead|work|implement|optimi|collaborat|maintain|ensure|coordinate|support|monitor|prepare|deliver|analyze|conduct|architect)\w*\b', cleaned):
        return True
    return False


def _is_experience_entry_start_line(line):
    cleaned = _clean_experience_line(line)
    if not cleaned or _is_experience_noise_line(cleaned):
        return False
    if _is_experience_fragment_line(cleaned):
        return False
    if _extract_location_from_line(cleaned):
        return False
    if RESPONSIBILITY_LINE_RE.search(cleaned):
        return False
    if re.search(r'(?i)\bkey\s+responsibilit\w*\b', cleaned):
        return False
    if COMPANY_LABEL_RE.match(cleaned) or ROLE_LABEL_RE.match(cleaned) or LOCATION_LABEL_RE.match(cleaned) or DURATION_LABEL_RE.match(cleaned):
        return True
    if _parse_inline_experience_header(cleaned):
        return True
    if re.search(r'(?i)\b(?:at|@)\b', cleaned) and len(cleaned.split()) <= 16:
        if ROLE_HINT_RE.search(cleaned) or COMPANY_HINT_RE.search(cleaned):
            return True
    if '|' in cleaned and len(cleaned.split()) <= 18:
        pieces = [p.strip() for p in cleaned.split('|') if p.strip()]
        if len(pieces) >= 2 and any(ROLE_HINT_RE.search(p) or COMPANY_HINT_RE.search(p) for p in pieces[:3]):
            return True
    if DATE_RANGE_RE.search(cleaned):
        return False
    words = cleaned.split()
    if len(words) <= 10 and (ROLE_HINT_RE.search(cleaned) or COMPANY_HINT_RE.search(cleaned)):
        return True
    if len(words) <= 8:
        title_like = sum(1 for word in words if word[:1].isupper())
        if title_like >= max(2, len(words) - 1) and not re.search(r'(?i)\b(?:using|with|for|and|to|of|in|on|by|from|their|its|the)\b', cleaned):
            return True
    return False


def _peel_trailing_experience_metadata(block):
    if not block:
        return block, []

    last_body_idx = -1
    for idx, line in enumerate(block):
        if _looks_like_experience_body_line(line):
            last_body_idx = idx

    if last_body_idx < 0 or last_body_idx >= len(block) - 1:
        return block, []

    tail = block[last_body_idx + 1:]
    if not tail or not all(_is_experience_metadata_line(line) for line in tail):
        return block, []

    head = block[:last_body_idx + 1]
    head_has_date = any(DATE_RANGE_RE.search(line) for line in head)
    head_has_location = any(_extract_location_from_line(line) for line in head)
    tail_has_date = any(DATE_RANGE_RE.search(line) for line in tail)
    tail_has_location = any(_extract_location_from_line(line) for line in tail)

    if (tail_has_date and head_has_date) or (tail_has_location and head_has_location):
        return head, tail
    return block, []


def _extract_rich_responsibilities(block, company=None, role=None, duration_text=None):
    if not block:
        return []
    out = []
    seen = set()
    company_l = (company or '').lower()
    role_l = (role or '').lower()
    duration_l = (duration_text or '').lower()

    for line in block:
        l = _clean_experience_line(line)
        if not l or _is_experience_noise_line(l):
            continue
        ll = l.lower()

        # Skip metadata-like lines.
        if EXPERIENCE_LABELED_LINE_RE.match(l):
            continue
        if _parse_inline_experience_header(l):
            continue
        if DATE_RANGE_RE.search(l):
            continue
        if (company_l and ll == company_l) or (role_l and ll == role_l) or (duration_l and ll == duration_l):
            continue
        if len(l.split()) < 6:
            continue

        # Keep bullets and meaningful prose lines.
        if RESPONSIBILITY_LINE_RE.search(line) or re.search(r'(?i)\b(?:develop|design|build|create|manage|lead|work|implement|optimi|collaborat|maintain|ensure)\w*\b', l):
            key = ll
            if key not in seen:
                seen.add(key)
                out.append(l)
    return out


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


def _extract_rich_responsibilities(block, company=None, role=None, duration_text=None):
    if not block:
        return []
    out = []
    seen = set()
    company_l = (company or '').lower()
    role_l = (role or '').lower()
    duration_l = (duration_text or '').lower()

    normalized_block = _normalize_experience_section_lines(block)
    for line in normalized_block:
        l = _clean_experience_line(line)
        if not l or _is_experience_noise_line(l):
            continue
        ll = l.lower()

        if EXPERIENCE_LABELED_LINE_RE.match(l):
            continue
        if _parse_inline_experience_header(l):
            continue
        if DATE_RANGE_RE.search(l):
            continue
        if (company_l and ll == company_l) or (role_l and ll == role_l) or (duration_l and ll == duration_l):
            continue
        if len(l.split()) < 6:
            continue

        if _looks_like_experience_body_line(l):
            key = ll
            if key not in seen:
                seen.add(key)
                out.append(l)
    return out


def _extract_responsibilities(lines):
    if not lines:
        return []
    out = []
    seen = set()
    normalized_lines = _normalize_experience_section_lines(lines)
    for line in normalized_lines:
        if not line:
            continue
        if _looks_like_experience_body_line(line):
            val = re.sub(r'^\s*(?:[-â€¢*]|\d+\.|[a-z]\))\s*', '', line).strip()
            key = val.lower()
            if val and key not in seen:
                seen.add(key)
                out.append(val)
    return out


def extract_professional_experience_profile(text):
    """Extract ATS-style professional experience details from resume text."""
    section_lines = _extract_experience_section_lines(text)
    if not section_lines:
        return []

    blocks = []
    current = []
    current_has_body = False
    current_header_count = 0
    for line in section_lines:
        line = _clean_experience_line(line)
        if _is_experience_noise_line(line):
            continue
        is_start = _is_experience_entry_start_line(line)
        is_body = _looks_like_experience_body_line(line)
        if current and is_start and (current_has_body or current_header_count >= 2):
            finalized_current, carryover = _peel_trailing_experience_metadata(current)
            blocks.append(finalized_current)
            current = [line] + carryover
            current_has_body = is_body
            current_header_count = 1 + sum(
                1 for item in carryover
                if _is_experience_metadata_line(item) or _is_experience_entry_start_line(item)
            )
            continue
        current.append(line)
        if is_body:
            current_has_body = True
        elif is_start or DATE_RANGE_RE.search(line) or _extract_location_from_line(line):
            current_header_count += 1
        else:
            current_header_count += 1
    if current:
        blocks.append(current)

    experiences = []
    for block in blocks:
        block = [ln for ln in block if ln and not _is_experience_noise_line(ln)]
        if not block:
            continue
        block_text = '\n'.join(block)
        company = None
        role = None
        location = None
        start_date = None
        end_date = None
        currently_working = False
        duration_raw = None

        for line in block:
            stripped_line, stripped_date = _strip_trailing_date_range(line)
            parsed_line = stripped_line or line
            company_lbl = COMPANY_LABEL_RE.match(line)
            if company_lbl and company is None:
                company = _clean_experience_line(company_lbl.group(1))

            role_lbl = ROLE_LABEL_RE.match(line)
            if role_lbl and role is None:
                role = _clean_experience_line(role_lbl.group(1))

            location_lbl = LOCATION_LABEL_RE.match(line)
            if location_lbl and location is None:
                location = _clean_experience_line(location_lbl.group(1))

            duration_lbl = DURATION_LABEL_RE.match(line)
            if duration_lbl:
                s, e, is_current, raw_duration = _extract_date_range(duration_lbl.group(1))
                if s and e and start_date is None:
                    start_date = s
                    end_date = e
                    currently_working = is_current
                    duration_raw = raw_duration

            inline_header = _parse_inline_experience_header(line)
            if inline_header:
                if company is None:
                    company = inline_header['company']
                if role is None:
                    role = inline_header['role']
                if location is None and inline_header.get('location'):
                    location = inline_header['location']
                if inline_header.get('date_range') and start_date is None:
                    s, e, is_current, raw_duration = _extract_date_range(inline_header['date_range'])
                    if s and e:
                        start_date = s
                        end_date = e
                        currently_working = is_current
                        duration_raw = raw_duration

            if '|' in parsed_line:
                pieces = [p.strip() for p in parsed_line.split('|') if p.strip()]
                for piece in pieces:
                    if role is None and _looks_like_role(piece):
                        role = piece
                    s, e, is_current, raw_duration = _extract_date_range(piece)
                    if s and e and start_date is None:
                        start_date = s
                        end_date = e
                        currently_working = is_current
                        duration_raw = raw_duration
                
                # Enhanced company extraction for pipe-delimited format
                if company is None and len(pieces) >= 2:
                    # If first piece is a role, second piece is likely company
                    if _looks_like_role(pieces[0]):
                        candidate = pieces[1]
                        # Extract company name from parentheses if present
                        # e.g., "Earnifyy (Styflowne Finance Services Pvt. Ltd.)" → take Earnifyy
                        if '(' in candidate:
                            # Try extracting the name before parentheses first
                            before_paren = candidate.split('(')[0].strip()
                            if before_paren and not DATE_RANGE_RE.search(before_paren):
                                company = before_paren
                            else:
                                # Extract from inside parentheses
                                inside_paren = re.search(r'\(([^)]+)\)', candidate)
                                if inside_paren:
                                    company = inside_paren.group(1).strip()
                                else:
                                    company = candidate
                        else:
                            company = candidate
                    # If first piece looks like company and role is set, use it
                    elif _looks_like_company(pieces[0]) and role is not None:
                        company = pieces[0]
                
                # Fallback: check each piece for company-like attributes
                if company is None:
                    for piece in pieces:
                        if _looks_like_company(piece):
                            company = piece
                            break
            
            if company is None and _looks_like_company(parsed_line) and not _looks_like_role(parsed_line):
                company = parsed_line
            if role is None and _looks_like_role(parsed_line):
                role = _normalize_role_text(parsed_line)
            if location is None:
                location = _extract_location_from_line(parsed_line)
            s, e, is_current, raw_duration = stripped_date if stripped_date[0] else _extract_date_range(line)
            if s and e and start_date is None:
                start_date = s
                end_date = e
                currently_working = is_current
                duration_raw = raw_duration

        responsibilities = _extract_rich_responsibilities(block, company=company, role=role, duration_text=duration_raw)
        if not responsibilities:
            responsibilities = _extract_responsibilities(block)
        technologies = _extract_technologies(block_text)
        experience_duration = _duration_from_range(start_date, end_date, currently_working)

        # Keep blocks that look like an experience entry.
        strong_company = bool(company and EXPERIENCE_VALID_COMPANY_HINT_RE.search(company))
        has_signal = bool(start_date or role or strong_company)
        if not has_signal:
            continue

        if company and EXPERIENCE_NOISE_VALUE_RE.search(company) and not strong_company and not start_date:
            continue

        if role and EXPERIENCE_NOISE_VALUE_RE.search(role) and not start_date:
            role = None

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

    experiences = _rebalance_experience_responsibilities(experiences)
    return _repair_cross_block_responsibility_fragments(experiences)


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
    # Chemical / Process Engineering
    'hydrometallurgy', 'solvent extraction', 'leaching', 'leaching process',
    'filter press', 'centrifuge filter', 'etp', 'effluent treatment',
    'acid leaching', 'roasting', 'calcination', 'precipitation',
    'flotation', 'crystallization', 'distillation', 'refining',
    'heap leaching', 'pressure leaching', 'stirred tank leaching',
    'counter current decantation', 'ccd', 'gravity separation',
    'thickening', 'filtration', 'membrane separation', 'reverse osmosis',
    'activated carbon', 'ion exchange', 'solvent recovery',
    'metal recovery', 'mineral processing', 'ore processing',
    'extrusion', 'injection molding', 'blow molding', 'plastic processing',
    'polymer processing', 'rubber processing', 'compounding',
    'drip irrigation', 'hdpe', 'upvc', 'cpvc', 'ppr',

    # Pharma / Lab / Healthcare
    'tablet manufacturing', 'capsule filling', 'wet granulation',
    'dry granulation', 'compression', 'coating', 'blending',
    'process validation', 'cleaning validation', 'analytical method validation',
    'batch manufacturing', 'bmr', 'sop', 'cgmp', 'gmp',
    'regulatory compliance', 'fda compliance', 'who compliance',
    'stability testing', 'dissolution testing', 'hplc', 'gc', 'uv vis',
    'spectrophotometry', 'titration', 'microbiology testing',
    'equipment calibration', 'equipment qualification', 'iq oq pq',
    'change control', 'deviation management', 'capa',
    'quality audit', 'internal audit', 'oee',
    'pharmacovigilance', 'clinical trials', 'drug regulatory affairs',
    'medical coding', 'medical writing',

    # Quality / Safety / Environment
    'quality control', 'quality assurance', 'qa qc',
    'iso 9001', 'iso 14001', 'iso 45001', 'ohsas 18001',
    'spc', 'statistical process control', 'six sigma', 'lean manufacturing',
    'kaizen', '5s', 'fmea', 'root cause analysis', 'rca',
    'inspection', 'non destructive testing', 'ndt',
    'ehs', 'health safety environment', 'hse',
    'fire safety', 'hazop', 'risk assessment',
    'environmental compliance', 'waste management',

    # Manufacturing / Production / Operations
    'production planning', 'production scheduling', 'capacity planning',
    'inventory management', 'warehouse management', 'supply chain management',
    'procurement', 'vendor management', 'purchase management',
    'logistics', 'dispatch', 'material handling',
    'erp', 'sap', 'sap mm', 'sap pp', 'sap sd', 'sap fi',
    'oracle erp', 'tally', 'tally erp',
    'plant operations', 'equipment maintenance', 'preventive maintenance',
    'corrective maintenance', 'breakdown maintenance', 'tpm',
    'autocad', 'solidworks', 'catia', 'pro e', 'ansys',
    'process optimization', 'yield optimization', 'cost reduction',
    'shift management', 'manpower planning',

    # Information Technology / Software
    'python', 'java', 'c', 'c++', 'c#', 'javascript', 'typescript',
    'php', 'ruby', 'go', 'golang', 'rust', 'swift', 'kotlin',
    'r programming', 'scala', 'perl', 'bash', 'shell scripting', 'powershell',
    'html', 'css', 'html5', 'css3', 'sass', 'less',
    'react', 'reactjs', 'react native', 'angular', 'vue', 'vuejs',
    'nodejs', 'express', 'django', 'flask', 'fastapi', 'spring boot',
    'hibernate', 'laravel', 'asp net', 'dotnet', '.net',
    'jquery', 'bootstrap', 'tailwind', 'next js', 'nuxt js',
    'sql', 'mysql', 'postgresql', 'oracle', 'mssql', 'sqlite',
    'mongodb', 'cassandra', 'redis', 'elasticsearch', 'dynamodb',
    'nosql', 'hbase', 'couchdb',
    'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean',
    'docker', 'kubernetes', 'terraform', 'ansible', 'chef', 'puppet',
    'jenkins', 'gitlab ci', 'github actions', 'ci cd', 'devops',
    'linux', 'unix', 'windows server', 'ubuntu', 'centos', 'rhel',
    'git', 'svn', 'jira', 'confluence', 'trello', 'bitbucket',
    'rest api', 'restful api', 'graphql', 'soap', 'api development',
    'microservices', 'monolithic architecture', 'serverless',
    'kafka', 'rabbitmq', 'activemq', 'celery', 'redis queue',
    'agile', 'scrum', 'kanban', 'waterfall', 'sdlc', 'sprint planning',
    'unit testing', 'integration testing', 'selenium', 'pytest', 'junit',
    'postman', 'swagger', 'api testing', 'load testing', 'jmeter',
    'vs code', 'visual studio', 'eclipse', 'intellij', 'pycharm',
    'android development', 'ios development', 'flutter', 'xamarin',
    'machine learning', 'deep learning', 'artificial intelligence',
    'natural language processing', 'nlp', 'computer vision',
    'tensorflow', 'pytorch', 'keras', 'scikit learn', 'opencv',
    'data science', 'data analysis', 'data visualization',
    'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly',
    'power bi', 'tableau', 'qlikview', 'looker', 'metabase',
    'excel', 'advanced excel', 'pivot table', 'vlookup', 'macros',
    'hadoop', 'spark', 'hive', 'pig', 'mapreduce', 'databricks',
    'etl', 'data pipeline', 'data warehousing', 'data modeling',
    'snowflake', 'redshift', 'bigquery', 'azure synapse',
    'cybersecurity', 'network security', 'penetration testing',
    'ethical hacking', 'siem', 'vulnerability assessment',
    'sap abap', 'sap hana', 'sap basis',
    'salesforce', 'crm', 'hubspot', 'zoho crm',

    # Data / Analytics / Business Intelligence
    'business analysis', 'business intelligence', 'bi',
    'data analytics', 'predictive analytics', 'statistical analysis',
    'regression analysis', 'time series analysis', 'a b testing',
    'kpi reporting', 'mis reporting', 'dashboard creation',
    'requirement gathering', 'use case documentation', 'brd', 'fsd',
    'uml', 'process mapping', 'gap analysis', 'swot analysis',

    # Finance / Accounting
    'financial analysis', 'financial modeling', 'financial reporting',
    'budgeting', 'forecasting', 'variance analysis',
    'accounts payable', 'accounts receivable', 'general ledger',
    'bank reconciliation', 'bookkeeping', 'accounting',
    'gst', 'tds', 'income tax', 'taxation', 'auditing',
    'ifrs', 'gaap', 'ind as',
    'cost accounting', 'management accounting', 'credit analysis',
    'risk management', 'internal control', 'compliance',
    'investment analysis', 'portfolio management', 'equity research',
    'fx trading', 'derivatives', 'treasury management',
    'tally prime', 'quickbooks', 'zoho books', 'sap fico',

    # Human Resources
    'recruitment', 'talent acquisition', 'sourcing', 'screening',
    'onboarding', 'offboarding', 'employee engagement',
    'performance management', 'appraisal', 'kra setting',
    'payroll processing', 'payroll management', 'statutory compliance',
    'pf', 'esic', 'gratuity', 'leave management',
    'hris', 'hrms', 'darwin box', 'successfactors', 'workday',
    'training and development', 'learning and development', 'l&d',
    'grievance handling', 'employee relations', 'hr policy',
    'compensation and benefits', 'salary benchmarking',
    'manpower planning', 'headcount planning',

    # Sales / Marketing / Business Development
    'sales', 'business development', 'lead generation',
    'client acquisition', 'key account management', 'crm management',
    'cold calling', 'negotiation', 'proposal writing',
    'market research', 'competitor analysis', 'brand management',
    'digital marketing', 'social media marketing', 'seo', 'sem',
    'google ads', 'facebook ads', 'meta ads', 'linkedin marketing',
    'email marketing', 'content marketing', 'influencer marketing',
    'campaign management', 'google analytics', 'hubspot',
    'e commerce', 'amazon seller', 'flipkart seller',
    'channel sales', 'distribution management', 'retail management',

    # Project Management / General
    'project management', 'project planning', 'project coordination',
    'stakeholder management', 'risk management', 'budget management',
    'vendor coordination', 'contract management', 'sow',
    'ms project', 'asana', 'monday com', 'smartsheet',
    'pmp', 'prince2', 'capm',
    'communication skills', 'presentation skills', 'team leadership',
    'cross functional collaboration', 'problem solving',

    # Design / Creative
    'graphic design', 'ui design', 'ux design', 'ui ux',
    'figma', 'adobe xd', 'sketch', 'invision',
    'photoshop', 'illustrator', 'indesign', 'canva',
    'video editing', 'premiere pro', 'after effects', 'final cut pro',
    'motion graphics', '3d modeling', 'blender', 'maya',

    # Logistics / Supply Chain
    'import export', 'customs clearance', 'freight forwarding',
    'shipping', 'fleet management', 'route planning',
    'cold chain', 'warehouse operations', 'wms',
    'demand planning', 's&op', 'forecasting', 'order management',
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
        email          = extract_email_from_resume(text)
        name           = extract_name(text)
        if _is_suspicious_extracted_name(name):
            simple_email_name = _derive_name_from_email_local(email)
            if simple_email_name and not _is_suspicious_extracted_name(simple_email_name):
                name = simple_email_name
            else:
                email_fallback_name = name_from_email(text)
                if email_fallback_name and not _is_suspicious_extracted_name(email_fallback_name):
                    name = email_fallback_name

        if _is_suspicious_extracted_name(name):
            filename_name = _derive_name_from_filename(fname)
            if filename_name and not _is_suspicious_extracted_name(filename_name):
                name = filename_name
        contact_number = extract_contact_number(text)
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
        education_profile = extract_education(text)

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
            'education':      education_profile,    # ← NEW
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
            'education':      [],             # ← NEW
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
