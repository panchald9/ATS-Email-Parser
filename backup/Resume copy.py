import os
import re
import json
import spacy
from pdfminer.high_level import extract_text

# Load spaCy model
nlp = spacy.load('en_core_web_sm')


# -------------------- PDF TEXT EXTRACTION --------------------
def extract_text_from_pdf(pdf_path):
    try:
        return extract_text(pdf_path)
    except:
        return ""


# -------------------- CONTACT NUMBER --------------------
def extract_contact_number(text):
    pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\d{10}\b"
    match = re.search(pattern, text)
    return match.group() if match else None


# -------------------- EMAIL --------------------
def extract_email(text):
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    match = re.search(pattern, text)
    return match.group() if match else None


# -------------------- SKILLS --------------------
def extract_skills(text, skills_list):
    found_skills = []
    for skill in skills_list:
        if re.search(r"\b{}\b".format(re.escape(skill)), text, re.IGNORECASE):
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
    
    matches = re.findall(pattern, text)
    return list(set(matches))


# -------------------- DATA SCIENCE EDUCATION --------------------
def extract_data_science_education(text):
    doc = nlp(text)
    return [ent.text for ent in doc.ents if ent.label_ == 'ORG' and 'Data Science' in ent.text]


# -------------------- COLLEGE NAME --------------------
def extract_college_name(text):
    for line in text.split('\n'):
        if re.search(r"(?i)(college|university)", line):
            return line.strip()
    return None


# -------------------- PROCESS SINGLE RESUME --------------------
def process_resume(pdf_path, skills_list):
    text = extract_text_from_pdf(pdf_path)

    return {
        "file_name": os.path.basename(pdf_path),
        "contact": extract_contact_number(text),
        "email": extract_email(text),
        "skills": extract_skills(text, skills_list),
        "education": extract_education(text),
        "data_science_education": extract_data_science_education(text),
        "college": extract_college_name(text)
    }


# -------------------- MAIN --------------------
if __name__ == '__main__':

    folder_path = r"D:\Ktas Project\ATS\ATS Email Parser\Resume"
    output_json = r"D:\Ktas Project\ATS\ATS Email Parser\output.json"

    # Skills list
    skills_list = [
    # Programming Languages
    'Python', 'Java', 'C', 'C++', 'C#', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'Kotlin', 'Swift', 'R', 'MATLAB', 'PHP',

    # Data Science & AI
    'Data Analysis', 'Machine Learning', 'Deep Learning', 'Natural Language Processing', 'Computer Vision',
    'Data Visualization', 'Statistical Analysis', 'Predictive Modeling', 'Big Data',

    # Libraries & Frameworks
    'Pandas', 'NumPy', 'Scikit-learn', 'TensorFlow', 'Keras', 'PyTorch', 'OpenCV', 'NLTK', 'SpaCy',

    # Databases
    'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'SQLite', 'Oracle', 'Redis',

    # Tools & Platforms
    'Git', 'GitHub', 'Docker', 'Kubernetes', 'Jenkins', 'CI/CD', 'Linux', 'AWS', 'Azure', 'Google Cloud',

    # Web Development
    'HTML', 'CSS', 'React', 'Angular', 'Vue.js', 'Node.js', 'Django', 'Flask', 'Spring Boot',

    # BI & Visualization Tools
    'Tableau', 'Power BI', 'Excel', 'Looker',

    # Software Engineering Concepts
    'Object-Oriented Programming', 'Data Structures', 'Algorithms', 'System Design', 'REST APIs', 'Microservices',

    # Soft Skills
    'Communication', 'Leadership', 'Teamwork', 'Problem Solving', 'Time Management', 'Project Management',
    'Critical Thinking', 'Adaptability'
]


    all_results = []

    # Loop through all PDFs
    for file in os.listdir(folder_path):
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, file)
            print(f"Processing: {file}")

            data = process_resume(pdf_path, skills_list)
            all_results.append(data)

    # Save to JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4)

    print("\n✅ All resumes processed and saved to JSON!")