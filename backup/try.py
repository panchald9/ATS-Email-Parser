import re
import json
from pypdf import PdfReader
import os
def extract_text_from_pdf(pdf_path):
    text = []
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)
    return "\n".join(text)

def clean_text(text):
    text = re.sub(r'\r', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n\n', text)
    return text.strip()

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None

def extract_phone(text):
    patterns = [
        r'(\+91[-\s]?\d{10})',
        r'(\d{10})',
        r'(\d{3}[-\s]\d{3}[-\s]\d{4})'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def extract_links(text):
    linkedin = re.search(r'(https?://)?(www\.)?linkedin\.com/[^\s]+', text, re.I)
    github = re.search(r'(https?://)?(www\.)?github\.com/[^\s]+', text, re.I)
    portfolio = re.findall(r'https?://[^\s]+', text)

    return {
        "linkedin": linkedin.group(0) if linkedin else None,
        "github": github.group(0) if github else None,
        "portfolio": portfolio
    }

def extract_name(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # simple assumption: first meaningful line is name
    for line in lines[:5]:
        if len(line.split()) <= 4 and not re.search(r'@|\d|linkedin|github', line, re.I):
            return line
    return None

def extract_skills(text):
    skill_db = [
        "Python", "Java", "C", "C++", "JavaScript", "HTML", "CSS",
        "Flask", "Django", "React", "Node.js", "MySQL", "MongoDB",
        "Firebase", "Android", "Jetpack Compose", "Git", "Tailwind CSS"
    ]
    found = []
    text_lower = text.lower()
    for skill in skill_db:
        if skill.lower() in text_lower:
            found.append(skill)
    return sorted(list(set(found)))

def extract_section(text, start_keywords, end_keywords=None):
    start_pattern = r'(' + '|'.join(start_keywords) + r')'
    end_pattern = r'(' + '|'.join(end_keywords) + r')' if end_keywords else None

    start_match = re.search(start_pattern, text, re.I)
    if not start_match:
        return None

    start_index = start_match.end()

    if end_pattern:
        end_match = re.search(end_pattern, text[start_index:], re.I)
        if end_match:
            return text[start_index:start_index + end_match.start()].strip()

    return text[start_index:].strip()

def parse_resume(pdf_path):
    raw_text = extract_text_from_pdf(pdf_path)
    text = clean_text(raw_text)

    links = extract_links(text)

    data = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "linkedin": links["linkedin"],
        "github": links["github"],
        "portfolio_links": links["portfolio"],
        "skills": extract_skills(text),
        "summary": extract_section(
            text,
            start_keywords=["summary", "profile", "objective"],
            end_keywords=["education", "experience", "skills", "projects"]
        ),
        "education_text": extract_section(
            text,
            start_keywords=["education", "academic"],
            end_keywords=["experience", "skills", "projects", "certifications"]
        ),
        "experience_text": extract_section(
            text,
            start_keywords=["experience", "work experience", "employment"],
            end_keywords=["education", "skills", "projects", "certifications"]
        ),
        "projects_text": extract_section(
            text,
            start_keywords=["projects", "project"],
            end_keywords=["education", "experience", "skills", "certifications"]
        )
    }
    os.makedirs("output", exist_ok=True)
    with open("output/{0}.json".format(os.path.splitext(pdf_file)[0]), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data

if __name__ == "__main__":
    pdf_file = "1.pdf"
    parsed_data = parse_resume(pdf_file)
    print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
