# from pyresparser import ResumeParser

# data = ResumeParser("resume.pdf").get_extracted_data()

# print(data)

# import os
# from pyresparser import ResumeParser

# folder = "Resume"

# for file in os.listdir(folder):
#     if file.endswith(".pdf"):
#         path = os.path.join(folder, file)
#         data = ResumeParser(path).get_extracted_data()
#         print(data["name"], data["skills"])

# import json
# from pyresparser import ResumeParser

# data = ResumeParser("resume.pdf").get_extracted_data()

# resume_json = {
#     "personal_details": {
#         "name": data.get("name"),
#         "email": data.get("email"),
#         "phone": data.get("mobile_number")
#     },
#     "skills": data.get("skills"),
#     "education": data.get("degree"),
#     "experience": data.get("experience"),
#     "total_experience": data.get("total_experience")
# }

# print(json.dumps(resume_json, indent=8))
##12121
# import json
# import os
# from datetime import datetime
# from pyresparser import ResumeParser

# # ---- Resume file ----
# resume_file = "resume.pdf"

# # ---- Extract data ----
# data = ResumeParser(resume_file).get_extracted_data()

# # ---- Auto calculations ----
# def calculate_age(birth_date):
#     if not birth_date:
#         return None
#     try:
#         birth = datetime.strptime(birth_date, "%Y-%m-%d")
#         today = datetime.today()
#         return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
#     except:
#         return None

# def calculate_total_experience(exp):
#     if exp:
#         return exp
#     return None

# # ---- Resume JSON Structure ----
# resume_json = {

#     "Complete_Name": data.get("name"),
#     "Professional_Title": None,

#     "Primary_Email": data.get("email"),
#     "Primary_Contact_Number": data.get("mobile_number"),

#     "Alternate_Email": None,
#     "Alternate_Contact_Number": None,

#     "Gender": None,
#     "Marital_Status": None,
#     "Birth_Date": None,
#     "Age": calculate_age(None),

#     "Nationality": None,
#     "Physically_Challenged": None,

#     "Current_Location": None,
#     "Preferred_Location": None,
#     "Open_to_Relocation": None,
#     "Open_to_Remote": None,

#     "Total_Experience": calculate_total_experience(data.get("total_experience")),

#     "Current_CTC": None,
#     "Expected_CTC": None,
#     "Notice_Period": None,

#     "Current_Role": None,
#     "Current_Industry": None,

#     "Key_Skills": data.get("skills"),
#     "Professional_Summary": None,

#     "Resume_File_Upload": resume_file,

#     "LinkedIn_URL": None,
#     "GitHub_URL": None,
#     "Portfolio_URL": None,

#     "Education": data.get("degree"),
#     "Experience": data.get("experience")
# }

# # ---- JSON filename same as PDF ----
# json_file_name = os.path.splitext(resume_file)[0] + ".json"

# # ---- Save JSON ----
# with open(json_file_name, "w", encoding="utf-8") as f:
#     json.dump(resume_json, f, indent=4)

# print(f"Resume data saved to {json_file_name}")

###  some of the batter  ###

# import json
# import os
# import re
# import pdfplumber
# from pyresparser import ResumeParser

# resume_file = "resume.pdf"

# # ----------------------------
# # Extract raw text from PDF
# # ----------------------------
# text = ""
# with pdfplumber.open(resume_file) as pdf:
#     for page in pdf.pages:
#         text += page.extract_text() + "\n"

# # ----------------------------
# # pyresparser basic extraction
# # ----------------------------
# data = ResumeParser(resume_file).get_extracted_data()

# # ----------------------------
# # Regex extractions
# # ----------------------------

# linkedin = re.search(r"(linkedin\.com\/[^\s]+)", text)
# github = re.search(r"(github\.com\/[^\s]+)", text)
# portfolio = re.search(r"(portfolio|portfolio\.com|\.dev|\.io)", text)

# location = re.search(r"(Ahmedabad|Gujrat|Gujarat|India)", text)

# # Professional summary
# summary_match = re.search(r"PROFILE(.*?)EDUCATION", text, re.S)
# summary = summary_match.group(1).strip() if summary_match else None

# # Current role
# role_match = re.search(r"\.NET\s*\/React\s*Developer", text)

# # ----------------------------
# # Build JSON
# # ----------------------------

# resume_json = {

#     "Complete_Name": data.get("name"),

#     "Professional_Title":
#         role_match.group(0) if role_match else None,

#     "Primary_Email": data.get("email"),
#     "Primary_Contact_Number": data.get("mobile_number"),

#     "Alternate_Email": None,
#     "Alternate_Contact_Number": None,

#     "Gender": None,
#     "Marital_Status": None,
#     "Birth_Date": None,
#     "Age": None,

#     "Nationality": "Indian",

#     "Physically_Challenged": "No",

#     "Current_Location":
#         location.group(0) if location else None,

#     "Preferred_Location": None,

#     "Open_to_Relocation": None,
#     "Open_to_Remote": None,

#     "Total_Experience": data.get("total_experience"),

#     "Current_CTC": None,
#     "Expected_CTC": None,

#     "Notice_Period": None,

#     "Current_Role":
#         role_match.group(0) if role_match else None,

#     "Current_Industry": "Software Development",

#     "Key_Skills": data.get("skills"),

#     "Professional_Summary": summary,

#     "Resume_File_Upload": resume_file,

#     "LinkedIn_URL":
#         linkedin.group(0) if linkedin else None,

#     "GitHub_URL":
#         github.group(0) if github else None,

#     "Portfolio_URL":
#         portfolio.group(0) if portfolio else None,

#     "Education": data.get("degree"),

#     "Experience": data.get("experience")

# }

# # ----------------------------
# # Save JSON with same name
# # ----------------------------

# json_file = os.path.splitext(resume_file)[0] + ".json"

# with open(json_file, "w", encoding="utf-8") as f:
#     json.dump(resume_json, f, indent=4)

# print("Saved:", json_file)

# # Second version with better regex and cleaning skills
# import json
# import os
# import re
# import pdfplumber
# from pyresparser import ResumeParser

# resume_file = "resume.pdf"

# # -------------------------
# # Extract text
# # -------------------------
# text = ""
# with pdfplumber.open(resume_file) as pdf:
#     for page in pdf.pages:
#         text += page.extract_text() + "\n"

# # -------------------------
# # Basic parser
# # -------------------------
# data = ResumeParser(resume_file).get_extracted_data()

# # -------------------------
# # Extract LinkedIn
# # -------------------------
# linkedin = re.search(r"(linkedin\.com\/[^\s]+)", text)

# # -------------------------
# # Extract GitHub (real URL only)
# # -------------------------
# github = re.search(r"(github\.com\/[^\s]+)", text)

# # -------------------------
# # Extract portfolio (real site)
# # -------------------------
# portfolio = re.search(r"(https?:\/\/[^\s]+\.(dev|io|com))", text)

# # -------------------------
# # Extract location
# # -------------------------
# location_match = re.search(r"Ahmedabad.*India", text)

# # -------------------------
# # Extract summary
# # -------------------------
# summary_match = re.search(r"PROFILE(.*?)EDUCATION", text, re.S)
# summary = summary_match.group(1).replace("\n", " ").strip() if summary_match else None

# # -------------------------
# # Extract role
# # -------------------------
# role_match = re.search(r"\.NET\s*\/React\s*Developer", text)

# # -------------------------
# # Clean skills
# # -------------------------
# skills = data.get("skills")

# bad_words = [
#     "English","Engineering","Certification","Technical",
#     "Analysis","Training","Project management"
# ]

# clean_skills = [s for s in skills if s not in bad_words] if skills else []

# # -------------------------
# # Education
# # -------------------------
# edu_match = re.search(r"EDUCATION(.*?)SKILLS", text, re.S)
# education = edu_match.group(1).replace("\n"," ").strip() if edu_match else None

# # -------------------------
# # Build JSON
# # -------------------------
# resume_json = {

# "Complete_Name": data.get("name"),

# "Professional_Title": role_match.group(0) if role_match else None,

# "Primary_Email": data.get("email"),

# "Primary_Contact_Number": data.get("mobile_number"),

# "Alternate_Email": None,

# "Alternate_Contact_Number": None,

# "Gender": None,

# "Marital_Status": None,

# "Birth_Date": None,

# "Age": None,

# "Nationality": "Indian",

# "Physically_Challenged": "No",

# "Current_Location":
# location_match.group(0) if location_match else "Ahmedabad, Gujarat, India",

# "Preferred_Location": None,

# "Open_to_Relocation": None,

# "Open_to_Remote": None,

# "Total_Experience": data.get("total_experience"),

# "Current_CTC": None,

# "Expected_CTC": None,

# "Notice_Period": None,

# "Current_Role": role_match.group(0) if role_match else None,

# "Current_Industry": "Software Development",

# "Key_Skills": clean_skills,

# "Professional_Summary": summary,

# "Resume_File_Upload": resume_file,

# "LinkedIn_URL": linkedin.group(0) if linkedin else None,

# "GitHub_URL": github.group(0) if github else None,

# "Portfolio_URL": portfolio.group(0) if portfolio else None,

# "Education": education,

# "Experience": data.get("experience")

# }

# # -------------------------
# # Save JSON
# # -------------------------
# json_file = os.path.splitext(resume_file)[0] + ".json"

# with open(json_file,"w",encoding="utf-8") as f:
#     json.dump(resume_json,f,indent=4)

# print("Saved:",json_file)


import json
import os
import re
import pdfplumber
from pyresparser import ResumeParser

resume_file = "resume.pdf"

# -------------------------
# Extract text from PDF
# -------------------------
text = ""
with pdfplumber.open(resume_file) as pdf:
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

# -------------------------
# Basic pyresparser data
# -------------------------
data = ResumeParser(resume_file).get_extracted_data()

# -------------------------
# Extract Links
# -------------------------
linkedin = re.search(r"(linkedin\.com\/[^\s]+)", text)
github = re.search(r"(github\.com\/[^\s]+)", text)
portfolio = re.search(r"https?:\/\/[^\s]+", text)

# -------------------------
# Extract Location
# -------------------------
location_match = re.search(r"(Ahmedabad.*India)", text)

# -------------------------
# Extract Summary
# -------------------------
summary_match = re.search(r"PROFILE(.*?)EDUCATION", text, re.S)
summary = summary_match.group(1).replace("\n"," ").strip() if summary_match else None

# -------------------------
# Extract Role
# -------------------------
role_match = re.search(r"\.NET\s*\/React\s*Developer", text)

# -------------------------
# Clean Skills
# -------------------------
skills = data.get("skills")

bad_words = [
"English","Engineering","Certification","Technical",
"Analysis","Training","Project management"
]

clean_skills = []

if skills:
    for s in skills:
        if s not in bad_words:
            clean_skills.append(s)

# -------------------------
# Parse Education
# -------------------------
def parse_education(text):

    education_section = re.search(r"EDUCATION(.*?)SKILLS", text, re.S)

    education_list = []

    if education_section:

        lines = education_section.group(1).split("\n")

        current = {}

        for line in lines:

            line = line.strip()

            if not line:
                continue

            if "University" in line:
                current["University"] = line

            elif "Master" in line or "Bachelor" in line or "M.Sc" in line:
                current["Degree"] = line

            elif "India" in line:
                current["Location"] = line

            elif re.search(r"\d{4}", line):
                current["Year"] = line

        if current:
            education_list.append(current)

    return education_list


# -------------------------
# Parse Experience
# -------------------------

# Model 1: Simple line-based parsing (less accurate)
# def parse_experience(text):

#     exp_section = re.search(r"EXPERIENCE(.*?)PROJECTS", text, re.S)

#     experiences = []

#     if exp_section:

#         lines = exp_section.group(1).split("\n")

#         current = {}

#         for line in lines:

#             line = line.strip()

#             if not line:
#                 continue

#             if "Developer" in line or "Lecturer" in line:
#                 current["Role"] = line

#             elif "India" in line:
#                 current["Location"] = line

#             elif "–" in line or "-" in line:
#                 if re.search(r"\d{4}", line):
#                     current["Duration"] = line

#             elif "•" in line:
#                 current.setdefault("Responsibilities", []).append(
#                     line.replace("•","").strip()
#                 )

#             else:

#                 if "Company" not in current:
#                     current["Company"] = line

#                 else:
#                     experiences.append(current)
#                     current = {"Company": line}

#         if current:
#             experiences.append(current)

#     return experiences
# Model 2: More structured parsing based on company sections (more accurate)
# def parse_experience(text):

#     exp_section = re.search(r"EXPERIENCE(.*?)PROJECTS", text, re.S)

#     experiences = []

#     if not exp_section:
#         return experiences

#     lines = exp_section.group(1).split("\n")

#     current = None

#     for line in lines:

#         line = line.strip()

#         if not line:
#             continue

#         # Detect company name
#         if "Services" in line or "CDAC" in line:

#             if current:
#                 experiences.append(current)

#             current = {
#                 "Company": line,
#                 "Role": None,
#                 "Location": None,
#                 "Duration": None,
#                 "Responsibilities": []
#             }

#         # Detect role
#         elif "Developer" in line or "Lecturer" in line:

#             if current:
#                 current["Role"] = line

#         # Detect location
#         elif "India" in line:

#             if current:
#                 current["Location"] = line

#         # Detect duration
#         elif "–" in line or "-" in line:

#             if re.search(r"\d{4}", line):

#                 if current:
#                     current["Duration"] = line

#         # Detect responsibility bullet
#         elif "•" in line:

#             if current:
#                 current["Responsibilities"].append(
#                     line.replace("•","").strip()
#                 )

#     if current:
#         experiences.append(current)

#     return experiences

def parse_experience(text):

    exp_section = re.search(r"EXPERIENCE(.*?)PROJECTS", text, re.S)

    experiences = []

    if not exp_section:
        return experiences

    lines = [l.strip() for l in exp_section.group(1).split("\n") if l.strip()]

    i = 0
    while i < len(lines):

        line = lines[i]

        # Detect company + location
        if "India" in line:

            parts = line.split("India")

            company = parts[0].strip()
            location = "India"

            role = None
            duration = None
            responsibilities = []

            # next line → role + duration
            if i+1 < len(lines):
                role_line = lines[i+1]

                match = re.search(r"(.*?)(\d{4}.*)", role_line)

                if match:
                    role = match.group(1).strip()
                    duration = match.group(2).strip()
                else:
                    role = role_line

            j = i + 2

            # collect bullet points
            while j < len(lines) and "•" in lines[j]:
                responsibilities.append(
                    lines[j].replace("•","").strip()
                )
                j += 1

            experiences.append({
                "Company": company,
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
resume_json = {

"Complete_Name": data.get("name"),

"Professional_Title": role_match.group(0) if role_match else None,

"Primary_Email": data.get("email"),

"Primary_Contact_Number": data.get("mobile_number"),

"Alternate_Email": None,
"Alternate_Contact_Number": None,

"Gender": None,
"Marital_Status": None,
"Birth_Date": None,
"Age": None,

"Nationality": "Indian",
"Physically_Challenged": "No",

"Current_Location":
location_match.group(0) if location_match else None,

"Preferred_Location": None,
"Open_to_Relocation": None,
"Open_to_Remote": None,

"Total_Experience": data.get("total_experience"),

"Current_CTC": None,
"Expected_CTC": None,
"Notice_Period": None,

"Current_Role": role_match.group(0) if role_match else None,

"Current_Industry": "Software Development",

"Key_Skills": clean_skills,

"Professional_Summary": summary,

"Resume_File_Upload": resume_file,

"LinkedIn_URL": linkedin.group(0) if linkedin else None,
"GitHub_URL": github.group(0) if github else None,
"Portfolio_URL": portfolio.group(0) if portfolio else None,

"Education": parse_education(text),

"Experience": parse_experience(text)

}

# -------------------------
# Save JSON
# -------------------------
json_file = os.path.splitext(resume_file)[0] + ".json"

with open(json_file,"w",encoding="utf-8") as f:
    json.dump(resume_json,f,indent=4)

print("JSON saved:", json_file)