import re
import spacy
from pdfminer.high_level import extract_text
from names_dataset import NameDataset

nd = NameDataset()  # takes time + RAM
# Load spaCy model
nlp = spacy.load('en_core_web_sm')



# -------------------- NAME --------------------
def extract_name_using_dataset(text):
    lines = text.split('\n')

    for line in lines[:10]:
        line = line.strip()

        # Ignore headings
        if any(word in line.lower() for word in ['contact','skills','profile','work']):
            continue

        # ALL CAPS NAME (like your resume)
        if re.match(r'^[A-Z]{3,}\s[A-Z]{3,}$', line):
            return line.title()

    return None
# -------------------- PDF TEXT EXTRACTION --------------------
def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

def clean_text(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text)
    return text
# -------------------- CONTACT NUMBER --------------------
def extract_contact_number(text):
    pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    match = re.search(pattern, text)
    return match.group() if match else None


# -------------------- EMAIL --------------------
def extract_email(text):
    text = clean_text(text)
    emails = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
    return emails[0] if emails else None


# -------------------- SKILLS --------------------
def extract_skills(text, skills_list):
    found_skills = []
    for skill in skills_list:
        pattern = r"\b{}\b".format(re.escape(skill))
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)
    return found_skills


# -------------------- EDUCATION --------------------
def extract_education(text):
    pattern = r"""(?i)\b(
    B\.?Sc|B\.?A|B\.?Com|B\.?Tech|B\.?E|BCA|BBA|
    M\.?Sc|M\.?A|M\.?Com|M\.?Tech|MCA|MBA|
    Ph\.?D|Doctorate|
    Bachelor(?:'s)?|Master(?:'s)?
)\b(?:\s+(?:of|in))?\s+(?:\w+\s*){1,5}"""
    return re.findall(pattern, text)


# -------------------- DATA SCIENCE EDUCATION (SPACY) --------------------
def extract_data_science_education(text):
    doc = nlp(text)
    if doc is None:
        return []
    return [ent.text for ent in doc.ents if ent.label_ == 'ORG' and 'Data Science' in ent.text]


# -------------------- COLLEGE NAME -------------------

def extract_college_name(text):
    lines = text.split('\n')
    college_pattern = r"(?i).*(college|university).*"
    for line in lines:
        if re.match(college_pattern, line):
            return line.strip()
    return None

# -------------------- MAIN --------------------
if __name__ == '__main__':

    pdf_path = r"D:\Ktas Project\ATS\ATS Email Parser\Resume\1.pdf"

    text = extract_text_from_pdf(pdf_path)

    # Skills list
    skills_list = [
    # -------------------- COMMUNICATION --------------------
    'Communication','Verbal Communication','Written Communication','Public Speaking',
    'Active Listening','Presentation Skills','Effective Communication',

    # -------------------- TEAM & LEADERSHIP --------------------
    'Teamwork','Team Collaboration','Leadership','People Management','Mentoring','Coaching',

    # -------------------- THINKING & PROBLEM SOLVING --------------------
    'Problem Solving','Critical Thinking','Analytical Thinking','Decision Making','Creativity',

    # -------------------- WORK ETHIC --------------------
    'Time Management','Adaptability','Flexibility','Self-Motivation','Discipline','Work Ethic',

    # -------------------- INTERPERSONAL --------------------
    'Emotional Intelligence','Conflict Resolution','Negotiation','Interpersonal Skills',
    'Relationship Building',

    # -------------------- MANAGEMENT --------------------
    'Project Management','Task Management','Organizational Skills','Multitasking',
    'Strategic Thinking','Planning',

    # -------------------- PROFESSIONAL --------------------
    'Attention to Detail','Accountability','Responsibility','Professionalism',
    'Customer Service','Client Handling',

    # -------------------- COMMON RESUME SKILLS --------------------
    'Troubleshooting','Technical Reporting','Documentation','Research Skills'


    # -------------------- PROGRAMMING --------------------
    'Python','Java','C','C++','C#','JavaScript','TypeScript','Go','Rust','Kotlin','Swift','R','MATLAB','PHP','Dart',

    # -------------------- DATA SCIENCE & AI --------------------
    'Machine Learning','Deep Learning','Natural Language Processing','Computer Vision','Data Analysis',
    'Data Mining','Big Data','Predictive Modeling','Statistical Analysis','Feature Engineering',

    # -------------------- LIBRARIES & FRAMEWORKS --------------------
    'Pandas','NumPy','Scikit-learn','TensorFlow','Keras','PyTorch','OpenCV','NLTK','SpaCy',
    'Matplotlib','Seaborn','XGBoost','LightGBM',

    # -------------------- DATABASES --------------------
    'SQL','MySQL','PostgreSQL','MongoDB','SQLite','Oracle','Redis','Firebase','Cassandra','DynamoDB',

    # -------------------- CLOUD & DEVOPS --------------------
    'AWS','Azure','Google Cloud','Docker','Kubernetes','Jenkins','CI/CD','Terraform','Ansible',
    'Linux','Unix','Shell Scripting',

    # -------------------- WEB DEVELOPMENT --------------------
    'HTML','CSS','JavaScript','React','Angular','Vue.js','Node.js','Express.js',
    'Django','Flask','Spring Boot','Next.js','REST APIs','GraphQL',

    # -------------------- MOBILE DEVELOPMENT --------------------
    'Android','iOS','Flutter','React Native','Swift','Kotlin','Xamarin',

    # -------------------- TESTING --------------------
    'Selenium','JUnit','TestNG','Cypress','Manual Testing','Automation Testing','Postman','API Testing',

    # -------------------- DATA TOOLS --------------------
    'Excel','Power BI','Tableau','Looker','Google Analytics','Hadoop','Spark','Airflow',
    'ETL','Data Warehousing',

    # -------------------- SOFTWARE ENGINEERING --------------------
    'Object-Oriented Programming','Data Structures','Algorithms','System Design',
    'Microservices','Design Patterns','SOLID Principles','Agile','Scrum','SDLC',

    # -------------------- CYBERSECURITY --------------------
    'Cybersecurity','Ethical Hacking','Penetration Testing','Network Security','Cryptography','OWASP','SIEM',

    # -------------------- NETWORKING --------------------
    'TCP/IP','DNS','HTTP','HTTPS','Firewall','Routing','Switching',

    # -------------------- UI/UX --------------------
    'UI Design','UX Design','Figma','Adobe XD','Wireframing','Prototyping','User Research',

    # -------------------- GENERAL TOOLS --------------------
    'Git','GitHub','GitLab','Bitbucket','VS Code','Jira','Trello','Slack','Notion'
]

    # Extract all data
    name = extract_name_using_dataset(text)
    contact = extract_contact_number(text)
    email = extract_email(text)
    skills = extract_skills(text, skills_list)
    education = extract_education(text)
    ds_education = extract_data_science_education(text)
    college = extract_college_name(text)

    # Print results
    print("\n----- EXTRACTED DATA -----\n")
    print("Name:", name if name else "Not found")
    print("Contact Number:", contact if contact else "Not found")
    print("Email:", email if email else "Not found")
    print("Skills:", skills if skills else "Not found")
    print("Education:", education if education else "Not found")
    print("Data Science Education:", ds_education if ds_education else "Not found")
    print("College:", college if college else "Not found")