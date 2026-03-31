import json
from Main_Resume import _extract_resume_record, extract_text, normalize_compact_text
import os

# Create a test resume file
test_resume = """
JOHN KUMAR SHARMA
john.sharma@email.com | +91-9876543210 | Mumbai, Maharashtra

OBJECTIVE
Experienced Chemical Process Engineer seeking to leverage expertise in hydrometallurgy and solvent extraction to optimize production efficiency and reduce operational costs.

WORK EXPERIENCE

Senior Process Engineer | Vedanta Alumina Ltd | Jan 2020 – Present
• Supervised solvent extraction process operations achieving 98% extraction efficiency
• Implemented acid leaching process optimization reducing costs by 22%
• Managed centrifuge filter and filter press maintenance reducing downtime by 40%
• Designed and implemented ETP (effluent treatment plant) quality monitoring system
• Led cross-functional team of 8 technicians on process improvements
• Conducted root cause analysis and troubleshooting of equipment failures

Process Engineer | Hindalco Hydrometallurgy Lab | Jun 2018 – Dec 2019
• Supported roasting and calcination process development
• Assisted with acid leaching experiments and yield optimization
• Performed quality control (QC) testing and analytical laboratory work
• Maintained process documentation and SOP compliance
• Involved in ETP monitoring and environmental compliance

Process Technician | Copper Extraction Plant | Jan 2017 – May 2018
• Operated centrifuge filters and filter press equipment
• Assisted in flotation and crystallization processes
• Supported quality assurance (QA) activities
• Basic equipment maintenance and process monitoring

EDUCATION
B.Tech in Chemical Engineering | IITB | 2016
• Thesis: Optimization of Solvent Extraction Parameters
• GPA: 3.8/4.0

SKILLS
Technical: Hydrometallurgy, Process Control, Quality Management
Software: Excel, Python, MATLAB
Languages: English, Hindi, Marathi

DECLARATION
I hereby declare that the information provided above is true and accurate to the best of my knowledge.
"""

# Save to temp file
test_file = "test_resume.txt"
with open(test_file, "w") as f:
    f.write(test_resume)

try:
    # Extract resume data
    result = _extract_resume_record(
        test_file, 
        ".", 
        skill_source='csv',  # Try CSV extraction
        skills_list=[],
        compiled_skill_matchers=None,
        fast_response=False
    )
    
    print("📄 RESUME EXTRACTION RESULTS")
    print("=" * 70)
    print(f"\n👤 Name: {result['name']}")
    print(f"📧 Email: {result['email']}")
    print(f"📱 Contact: {result['contact_number']}")
    print(f"🎂 DOB: {result['dob']}")
    print(f"⚧ Gender: {result['gender']}")
    print(f"📍 Address: {result['address']}")
    
    print(f"\n🧪 EXTRACTED SKILLS ({len(result['skills'])} skills found):")
    print("=" * 70)
    if result['skills']:
        for skill in sorted(result['skills']):
            print(f"   ✓ {skill}")
    else:
        print("   (No skills extracted)")
    
    # Highlight work experience skills
    work_exp_skills = [
        'Hydrometallurgy', 'Solvent Extraction', 'Acid Leaching', 'Calcination',
        'Roasting', 'Centrifuge Filter', 'Filter Press', 'Effluent Treatment',
        'Process Optimization', 'Quality Control', 'Equipment Maintenance'
    ]
    
    matched_work_skills = [s for s in result['skills'] if s in work_exp_skills]
    if matched_work_skills:
        print(f"\n🔬 Domain-specific skills from WORK EXPERIENCE:")
        for skill in sorted(matched_work_skills):
            print(f"   ⭐ {skill}")
    
finally:
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
