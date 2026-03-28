import pdfplumber
import spacy
import re
import json
import os
from datetime import datetime

nlp = spacy.load("en_core_web_sm")

resume_file = "resume.pdf"


# -----------------------
# Extract text
# -----------------------
def extract_text(pdf):

    text = ""

    with pdfplumber.open(pdf) as doc:
        for page in doc.pages:

            t = page.extract_text()

            if t:
                text += t + "\n"

    return text


# -----------------------
# Extract email
# -----------------------
def extract_email(text):

    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)

    return match.group(0) if match else None


# -----------------------
# Extract phone
# -----------------------
def extract_phone(text):

    match = re.search(r"(\+?\d[\d -]{8,}\d)", text)

    return match.group(0) if match else None


# -----------------------
# Extract name
# -----------------------
def extract_name(text):

    doc = nlp(text[:1000])

    for ent in doc.ents:

        if ent.label_ == "PERSON":
            return ent.text

    return None


# -----------------------
# Extract links
# -----------------------
def extract_links(text):

    linkedin = re.search(r"(linkedin\.com\/[^\s]+)", text)
    github = re.search(r"(github\.com\/[^\s]+)", text)

    return {
        "LinkedIn": linkedin.group(0) if linkedin else None,
        "GitHub": github.group(0) if github else None
    }


# -----------------------
# Skill detection (large list)
# -----------------------
skills_db = [
"Python","Java","C","C++","JavaScript","React","Angular","Vue",
"Node.js","Django","Flask",".NET","Spring Boot","Laravel",
"MySQL","PostgreSQL","MongoDB","Redis",
"AWS","Azure","GCP","Docker","Kubernetes",
"Git","Linux","Firebase","Flutter",
"TensorFlow","PyTorch","Machine Learning","Deep Learning",
"REST API","GraphQL","Microservices","NLP","AI",
"HTML","CSS","Bootstrap","Tailwind"
]


def extract_skills(text):

    found = []

    for skill in skills_db:

        if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
            found.append(skill)

    return sorted(set(found))


# -----------------------
# Section extractor
# -----------------------
def get_section(text, keywords):

    pattern = rf"({'|'.join(keywords)})(.*?)(EDUCATION|SKILLS|PROJECTS|EXPERIENCE|CERTIFICATIONS|$)"

    match = re.search(pattern,text,re.S|re.I)

    if match:
        return match.group(2).strip()

    return None


# -----------------------
# Experience parser
# -----------------------
def parse_experience(text):

    section = get_section(text,["EXPERIENCE","WORK EXPERIENCE"])

    if not section:
        return []

    lines = [l.strip() for l in section.split("\n") if l.strip()]

    exp = []

    current = None

    for line in lines:

        if "India" in line or "Ltd" in line or "Services" in line:

            if current:
                exp.append(current)

            current = {
                "Company": line,
                "Role": None,
                "Duration": None,
                "Responsibilities":[]
            }

        elif re.search(r"\d{4}",line):

            if current:
                current["Duration"] = line

        elif "Developer" in line or "Engineer" in line or "Manager" in line or "Lecturer" in line:

            if current:
                current["Role"] = line

        elif "•" in line:

            if current:
                current["Responsibilities"].append(
                    line.replace("•","").strip()
                )

    if current:
        exp.append(current)

    return exp


# -----------------------
# Experience calculator
# -----------------------
def calculate_experience(exp):

    total = 0

    for job in exp:

        duration = job.get("Duration")

        if not duration:
            continue

        dates = re.findall(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}",
            duration
        )

        if len(dates) == 2:

            start = datetime.strptime(dates[0],"%b %Y")
            end = datetime.strptime(dates[1],"%b %Y")

        elif "Present" in duration:

            start = datetime.strptime(dates[0],"%b %Y")
            end = datetime.today()

        else:
            continue

        months = (end.year-start.year)*12 + end.month-start.month

        total += months

    return round(total/12,1)


# -----------------------
# Education parser
# -----------------------
def parse_education(text):

    section = get_section(text,["EDUCATION"])

    if not section:
        return []

    lines = [l.strip() for l in section.split("\n") if l.strip()]

    edu = []

    current = {}

    for line in lines:

        if "University" in line or "College" in line:

            current["University"] = line

        elif "Bachelor" in line or "Master" in line or "B.Tech" in line or "M.Sc" in line:

            current["Degree"] = line

        elif re.search(r"\d{4}",line):

            current["Year"] = line

    if current:
        edu.append(current)

    return edu


# -----------------------
# Project parser
# -----------------------
def parse_projects(text):

    section = get_section(text,["PROJECTS"])

    if not section:
        return []

    lines = [l.strip() for l in section.split("\n") if l.strip()]

    projects = []

    current = None

    for line in lines:

        if "Project" in line:

            if current:
                projects.append(current)

            current = {"Title": line}

        elif "Skills:" in line:

            if current:
                current["Skills"] = line.replace("Skills:","").strip()

        elif "Description:" in line:

            if current:
                current["Description"] = line.replace("Description:","").strip()

    if current:
        projects.append(current)

    return projects


# -----------------------
# Certification parser
# -----------------------
def parse_certifications(text):

    section = get_section(text,["CERTIFICATIONS"])

    if not section:
        return []

    certs = []

    lines = [l.strip() for l in section.split("\n") if l.strip()]

    for line in lines:

        if "•" in line or "-" in line:

            certs.append(line.replace("•","").strip())

    return certs


# -----------------------
# Main ATS Parser
# -----------------------
def parse_resume(pdf):

    text = extract_text(pdf)

    links = extract_links(text)

    experience = parse_experience(text)

    data = {

        "Complete_Name": extract_name(text),

        "Primary_Email": extract_email(text),

        "Primary_Contact_Number": extract_phone(text),

        "LinkedIn_URL": links["LinkedIn"],

        "GitHub_URL": links["GitHub"],

        "Key_Skills": extract_skills(text),

        "Experience": experience,

        "Total_Experience": calculate_experience(experience),

        "Education": parse_education(text),

        "Projects": parse_projects(text),

        "Certifications": parse_certifications(text)

    }

    return data


# -----------------------
# Run parser
# -----------------------
result = parse_resume(resume_file)

json_file = os.path.splitext(resume_file)[0] + ".json"

with open(json_file,"w",encoding="utf-8") as f:

    json.dump(result,f,indent=4)

print("Resume parsed →",json_file)