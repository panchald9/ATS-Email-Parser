import json
import os
import re
import pdfplumber

resume_file = "resume.pdf"

# -------------------------
# Extract text from PDF
# -------------------------
def extract_pdf_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


text = extract_pdf_text(resume_file)

# -------------------------
# Basic Extractors
# -------------------------
def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None


def extract_phone(text):
    # Supports +91, spaces, dashes
    match = re.search(r'(\+91[\-\s]?)?[6-9]\d{9}', text)
    return match.group(0) if match else None


def extract_name(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return None

    # Assume first non-empty line is candidate name
    first = lines[0]

    # Avoid lines that look like title/contact
    if "@" in first or "linkedin" in first.lower() or "github" in first.lower():
        return None

    # Basic validation: 2 to 4 words, alphabets only
    if re.match(r"^[A-Za-z][A-Za-z\s\.]{2,50}$", first):
        return first.strip()

    return None


def extract_total_experience(text):
    patterns = [
        r'(\d+(?:\.\d+)?)\+?\s+years?\s+of\s+experience',
        r'experience\s+of\s+(\d+(?:\.\d+)?)\+?\s+years?',
        r'(\d+(?:\.\d+)?)\+?\s+yrs?\s+experience'
    ]

    lower_text = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower_text)
        if match:
            return float(match.group(1))
    return None


def extract_links(text):
    linkedin = re.search(r'(https?:\/\/)?(www\.)?linkedin\.com\/[^\s]+', text, re.I)
    github = re.search(r'(https?:\/\/)?(www\.)?github\.com\/[^\s]+', text, re.I)

    urls = re.findall(r'https?:\/\/[^\s]+', text, re.I)

    portfolio = None
    for url in urls:
        low = url.lower()
        if "linkedin.com" not in low and "github.com" not in low:
            portfolio = url
            break

    return {
        "linkedin": linkedin.group(0) if linkedin else None,
        "github": github.group(0) if github else None,
        "portfolio": portfolio
    }


def clean_url(url):
    if not url:
        return None
    return url.rstrip(".,);]")


# -------------------------
# Extract Location
# -------------------------
def extract_location(text):
    patterns = [
        r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z][a-z]+,\s*India)',
        r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*India)',
        r'(Ahmedabad.*?India)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


# -------------------------
# Extract Summary
# -------------------------
def extract_summary(text):
    patterns = [
        r'PROFILE(.*?)EDUCATION',
        r'SUMMARY(.*?)EDUCATION',
        r'PROFESSIONAL SUMMARY(.*?)EDUCATION',
        r'ABOUT ME(.*?)EDUCATION'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.S | re.I)
        if match:
            return re.sub(r'\s+', ' ', match.group(1)).strip()

    return None


# -------------------------
# Extract Role
# -------------------------
def extract_role(text):
    role_patterns = [
        r'\.NET\s*/\s*React\s*Developer',
        r'Full\s*Stack\s*Developer',
        r'React\s*Developer',
        r'Python\s*Developer',
        r'Software\s*Engineer',
        r'Web\s*Developer'
    ]

    for pattern in role_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(0).strip()

    return None


# -------------------------
# Extract Skills
# -------------------------
def extract_skills(text):
    skill_keywords = [
        "Python", "Java", "JavaScript", "TypeScript", "React", "Node.js", "Express",
        "Flask", "Django", ".NET", "C#", "SQL", "MySQL", "PostgreSQL", "MongoDB",
        "HTML", "CSS", "Tailwind", "Bootstrap", "Git", "GitHub", "REST API",
        "Firebase", "Pandas", "NumPy", "Machine Learning", "AI", "Docker",
        "AWS", "Linux", "Excel", "Power BI"
    ]

    found = []
    lower_text = text.lower()

    for skill in skill_keywords:
        if skill.lower() in lower_text:
            found.append(skill)

    return sorted(list(set(found)))


# -------------------------
# Parse Education
# -------------------------
def parse_education(text):
    education_section = re.search(r"EDUCATION(.*?)(SKILLS|EXPERIENCE|PROJECTS|$)", text, re.S | re.I)

    education_list = []

    if education_section:
        lines = [line.strip() for line in education_section.group(1).split("\n") if line.strip()]
        current = {}

        for line in lines:
            if any(word in line for word in ["University", "Institute", "College", "School"]):
                if current:
                    education_list.append(current)
                    current = {}
                current["University"] = line

            elif any(word in line for word in ["Master", "Bachelor", "B.Tech", "M.Tech", "B.Sc", "M.Sc", "BCA", "MCA", "BE", "ME"]):
                current["Degree"] = line

            elif "India" in line:
                current["Location"] = line

            elif re.search(r"\b(19|20)\d{2}\b", line):
                current["Year"] = line

        if current:
            education_list.append(current)

    return education_list


# -------------------------
# Parse Experience
# -------------------------
def parse_experience(text):
    exp_section = re.search(r"EXPERIENCE(.*?)(PROJECTS|SKILLS|EDUCATION|$)", text, re.S | re.I)

    experiences = []

    if not exp_section:
        return experiences

    lines = [l.strip() for l in exp_section.group(1).split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        if "India" in line:
            parts = line.split("India")
            company = parts[0].strip(" ,|-")
            location = "India"

            role = None
            duration = None
            responsibilities = []

            if i + 1 < len(lines):
                role_line = lines[i + 1]

                match = re.search(r"(.*?)(\b(?:19|20)\d{2}.*)", role_line)
                if match:
                    role = match.group(1).strip(" |-")
                    duration = match.group(2).strip()
                else:
                    role = role_line

            j = i + 2

            while j < len(lines):
                bullet_line = lines[j]

                if "India" in bullet_line:
                    break

                if bullet_line.startswith("•") or bullet_line.startswith("-"):
                    responsibilities.append(
                        bullet_line.replace("•", "").replace("-", "").strip()
                    )

                j += 1

            experiences.append({
                "Company": company or None,
                "Location": location,
                "Role": role,
                "Duration": duration,
                "Responsibilities": responsibilities
            })

            i = j
        else:
            i += 1

    return experiences


# -------------------------
# Build JSON
# -------------------------
links = extract_links(text)
role = extract_role(text)

resume_json = {
    "Complete_Name": extract_name(text),
    "Professional_Title": role,
    "Primary_Email": extract_email(text),
    "Primary_Contact_Number": extract_phone(text),

    "Alternate_Email": None,
    "Alternate_Contact_Number": None,

    "Gender": None,
    "Marital_Status": None,
    "Birth_Date": None,
    "Age": None,

    "Nationality": "Indian",
    "Physically_Challenged": "No",

    "Current_Location": extract_location(text),

    "Preferred_Location": None,
    "Open_to_Relocation": None,
    "Open_to_Remote": None,

    "Total_Experience": extract_total_experience(text),

    "Current_CTC": None,
    "Expected_CTC": None,
    "Notice_Period": None,

    "Current_Role": role,
    "Current_Industry": "Software Development",

    "Key_Skills": extract_skills(text),

    "Professional_Summary": extract_summary(text),

    "Resume_File_Upload": resume_file,

    "LinkedIn_URL": clean_url(links["linkedin"]),
    "GitHub_URL": clean_url(links["github"]),
    "Portfolio_URL": clean_url(links["portfolio"]),

    "Education": parse_education(text),
    "Experience": parse_experience(text)
}

# -------------------------
# Save JSON
# -------------------------
json_file = os.path.splitext(resume_file)[0] + ".json"

with open(json_file, "w", encoding="utf-8") as f:
    json.dump(resume_json, f, indent=4, ensure_ascii=False)

print("JSON saved:", json_file)
print(json.dumps(resume_json, indent=4, ensure_ascii=False))