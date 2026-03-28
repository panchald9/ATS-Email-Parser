import pdfplumber
import re
import json
import spacy

nlp = spacy.load("en_core_web_sm")

resume_file = "resume.pdf"


# -----------------------
# Extract text
# -----------------------

def extract_text(pdf_path):

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

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
# Extract name using NLP
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
# Extract skills
# -----------------------

def extract_skills(text):

    skills_db = [
        "Python","Django","Flask","React","Node.js","JavaScript",
        "MySQL","PostgreSQL","MongoDB","AWS","Docker",
        "Linux","Git","Firebase","REST API","Flutter",".NET"
    ]

    skills_found = []

    for skill in skills_db:

        if re.search(rf"\b{skill}\b", text, re.I):
            skills_found.append(skill)

    return skills_found


# -----------------------
# Extract sections
# -----------------------

def extract_section(text, start, end):

    pattern = rf"{start}(.*?){end}"

    match = re.search(pattern, text, re.S | re.I)

    if match:
        return match.group(1).strip()

    return None


# -----------------------
# Parse experience
# -----------------------

def parse_experience(text):

    exp_text = extract_section(text, "EXPERIENCE", "PROJECTS")

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
                current["Responsibilities"].append(line.replace("•","").strip())

    if current:
        experiences.append(current)

    return experiences


# -----------------------
# Main parser
# -----------------------

def parse_resume(pdf_path):

    text = extract_text(pdf_path)

    links = extract_links(text)

    resume_data = {

        "Name": extract_name(text),

        "Email": extract_email(text),

        "Phone": extract_phone(text),

        "LinkedIn": links["LinkedIn"],

        "GitHub": links["GitHub"],

        "Skills": extract_skills(text),

        "Experience": parse_experience(text),

        "Summary": extract_section(text,"PROFILE","EDUCATION")

    }

    return resume_data


# -----------------------
# Run parser
# -----------------------

data = parse_resume(resume_file)

json_file = resume_file.replace(".pdf",".json")

with open(json_file,"w",encoding="utf-8") as f:

    json.dump(data,f,indent=4)

print("Resume parsed:",json_file)