import os
import json
from pyresparser import ResumeParser

# Set the folder path containing resumes
resume_folder = r"D:\Ktas Project\ATS\ATS Email Parser\Resume"

# Dictionary to store all resume data organized by company
company_data = {}

# Process all PDF files in the folder
for filename in os.listdir(resume_folder):
    if filename.endswith('.pdf'):
        resume_path = os.path.join(resume_folder, filename)
        
        # Extract data from resume
        data = ResumeParser(resume_path).get_extracted_data()
        
        # Use filename (without extension) as identifier
        resume_id = os.path.splitext(filename)[0]
        
        # Store data with resume identifier
        company_data[resume_id] = data

# Save all resume data to JSON file
output_file = os.path.join(resume_folder, "company_resume_data.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(company_data, f, indent=4, ensure_ascii=False)

print(f"Resume data saved to: {output_file}")
print(f"Processed {len(company_data)} resumes")
