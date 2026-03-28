import pdfplumber
import re
import json
import os
import spacy
from datetime import datetime

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

resume_file = "resume.pdf"


# ----------------------------
# Extract text from PDF
# ----------------------------
def extract_text(pdf_path):

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text


# ----------------------------
# Extract name using NLP
# ----------------------------
def extract_name(text):

    doc = nlp(text[:1000])

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text

    return None


# ----------------------------
# Extract email
# ----------------------------
def extract_email(text):

    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)

    return match.group(0) if match else None


# ----------------------------
# Extract phone
# ----------------------------
def extract_phone(text):

    match = re.search(r"(\+?\d[\d -]{8,}\d)", text)

    return match.group(0) if match else None


# ----------------------------
# Extract links
# ----------------------------
def extract_links(text):

    linkedin = re.search(r"(linkedin\.com\/[^\s]+)", text)

    github = re.search(r"(github\.com\/[^\s]+)", text)

    return {
        "LinkedIn": linkedin.group(0) if linkedin else None,
        "GitHub": github.group(0) if github else None
    }


# ----------------------------
# Extract skills
# ----------------------------
def extract_skills(text):

    skills_db = [
        "Python","Java","C","C++","JavaScript","React","Angular","Vue",
        "Node.js","Django","Flask",".NET","Spring Boot",
        "MySQL","PostgreSQL","MongoDB",
        "AWS","Docker","Kubernetes",
        "Git","Linux","Firebase","Flutter",
        "TensorFlow","PyTorch","Machine Learning","AI",
        "REST API","GraphQL","Microservices"
    ]

    found = []

    for skill in skills_db:

        if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
            found.append(skill)

    return sorted(set(found))


# ----------------------------
# Extract section
# ----------------------------
def extract_section(text, start, end):

    pattern = rf"{start}(.*?){end}"

    match = re.search(pattern, text, re.S | re.I)

    if match:
        return match.group(1).strip()

    return None


# ----------------------------
# Parse experience
# ----------------------------
def parse_experience(text):

    exp_text = extract_section(text,"EXPERIENCE","PROJECTS")

    if not exp_text:
        return []

    lines = [l.strip() for l in exp_text.split("\n") if l.strip()]

    experiences = []

    current = None

    for line in lines:

        if "India" in line:

            if current:
                experiences.append(current)

            current = {
                "Company": line,
                "Role": None,
                "Duration": None,
                "Responsibilities": []
            }

        elif re.search(r"\d{4}", line):

            if current:
                current["Duration"] = line

        elif "Developer" in line or "Engineer" in line or "Lecturer" in line:

            if current:
                current["Role"] = line

        elif "•" in line:

            if current:
                current["Responsibilities"].append(
                    line.replace("•","").strip()
                )

    if current:
        experiences.append(current)

    return experiences


# ----------------------------
# Calculate experience
# ----------------------------
def calculate_experience(experiences):

    total_months = 0

    for exp in experiences:

        duration = exp.get("Duration")

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

        total_months += months

    return round(total_months/12,1)


# ----------------------------
# Parse education
# ----------------------------
def parse_education(text):

    edu_text = extract_section(text,"EDUCATION","SKILLS")

    if not edu_text:
        return []

    lines = [l.strip() for l in edu_text.split("\n") if l.strip()]

    education = []

    current = {}

    for line in lines:

        if "University" in line:

            current["University"] = line

        elif "Master" in line or "Bachelor" in line:

            current["Degree"] = line

        elif re.search(r"\d{4}", line):

            current["Year"] = line

    if current:
        education.append(current)

    return education


# ----------------------------
# Extract projects
# ----------------------------
def extract_projects(text):

    proj_text = extract_section(text,"PROJECTS","CERTIFICATIONS")

    if not proj_text:
        return []

    lines = [l.strip() for l in proj_text.split("\n") if l.strip()]

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


# ----------------------------
# Main parser
# ----------------------------
def parse_resume(pdf_path):

    text = extract_text(pdf_path)

    links = extract_links(text)

    experiences = parse_experience(text)

    resume_data = {

        "Complete_Name": extract_name(text),

        "Primary_Email": extract_email(text),

        "Primary_Contact_Number": extract_phone(text),

        "LinkedIn_URL": links["LinkedIn"],

        "GitHub_URL": links["GitHub"],

        "Key_Skills": extract_skills(text),

        "Experience": experiences,

        "Total_Experience": calculate_experience(experiences),

        "Education": parse_education(text),

        "Projects": extract_projects(text),

        "Professional_Summary": extract_section(text,"PROFILE","EDUCATION")

    }

    return resume_data


# ----------------------------
# Run parser
# ----------------------------
data = parse_resume(resume_file)

json_file = os.path.splitext(resume_file)[0] + ".json"

with open(json_file,"w",encoding="utf-8") as f:
    json.dump(data,f,indent=4)

print("Resume parsed successfully ->", json_file)