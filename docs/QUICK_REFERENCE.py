"""
RESUME PARSER v2.0 - QUICK REFERENCE CARD
==========================================
Keep this handy while using the Resume Parser!
"""

QUICK_COMMANDS = """
═══════════════════════════════════════════════════════════════════════════
QUICK COMMANDS
═══════════════════════════════════════════════════════════════════════════

SETUP:
------
pip install pdfminer.six python-docx
python SETUP.md                          # Verify dependencies

BASIC USAGE:
-----------
python "Main Resume.py"                  # Process all resumes

TESTING:
--------
python run_tests.py                      # Interactive menu

python run_tests.py --batch "C:\\path"   # Batch validation

python run_tests.py --quick "C:\\file"   # Single file analysis

python run_tests.py --test "C:\\path"    # Run test suite

CHECKING RESULTS:
-----------------
# View in text editor:
output/resume_parsed.json                # All extracted data
output/validation_report.json            # Accuracy scores
output/parser.log                        # Processing log

# Python:
import json
with open('output/validation_report.json') as f:
    report = json.load(f)
    print(f"Average Score: {report['average_score']:.1f}/100")

═══════════════════════════════════════════════════════════════════════════
VALIDATION SCORES
═══════════════════════════════════════════════════════════════════════════

90-100 ✅ EXCELLENT  - All data extracted correctly
75-89  👍 GOOD       - Most data extracted, minor issues
60-74  ⚠️  FAIR       - Partial data extracted
0-59   ❌ POOR       - Significant data missing

═══════════════════════════════════════════════════════════════════════════
CONFIGURATION
═══════════════════════════════════════════════════════════════════════════

Edit in Main Resume.py:

RESUME_FOLDER = r"D:\\your\\folder"      # Default folder
ENABLE_VALIDATION = True                 # Score results (True/False)
ENABLE_DETAILED_LOGGING = True           # Verbose output (True/False)

Process alternate folder:
PROCESS_FOLDER = "D:\\other\\folder"     # In __main__ section

═══════════════════════════════════════════════════════════════════════════
FILE CHECKLIST
═══════════════════════════════════════════════════════════════════════════

✅ Main Resume.py         - Main parser (ENHANCED)
✅ validation.py          - Validation module (NEW)
✅ test_parser.py         - Testing framework (NEW)
✅ run_tests.py           - Test runner (NEW)
✅ Skill.csv              - Skills reference
✅ output/ folder         - Results (auto-created)
✅ Resume/ folder         - Input resumes
✅ README_ENHANCEMENTS.md - Full documentation
✅ SETUP.md               - Installation guide

═══════════════════════════════════════════════════════════════════════════
TESTING YOUR SETUP
═══════════════════════════════════════════════════════════════════════════

Step 1: Verify Python
python --version                         # Need 3.7+

Step 2: Check dependencies
python -c "import pdfminer; print('OK')"
python -c "import docx; print('OK')"

Step 3: Test parser
python run_tests.py
# Choose option 1: Quick Resume Analysis
# Enter path to a test PDF

Expected output:
Name:        John Doe
Email:       john@example.com
Phone:       9876543210
Skills:      Python, Java, SQL
Validation:  85.0/100 (GOOD)

═══════════════════════════════════════════════════════════════════════════
COMMON ISSUES
═══════════════════════════════════════════════════════════════════════════

Issue                          Solution
────────────────────────────────────────────────────────────────────────
No module named 'pdfminer'     pip install pdfminer.six
No module named 'docx'         pip install python-docx
Resume file not found          Check path is correct
Empty text extracted           Try different PDF format
Email/Phone not extracted      Check resume contains these
Validation score too low       Review validation_report.json

═══════════════════════════════════════════════════════════════════════════
PYTHON API REFERENCE
═══════════════════════════════════════════════════════════════════════════

Import main parser:
from Main_Resume import extract_resume_data, load_skills_from_csv

Extract single resume:
result = extract_resume_data('/path/to/resume.pdf')
print(result['name'])
print(result['email'])
print(result['skills'])

Run validation:
from validation import ResumeValidator
validator = ResumeValidator()
validation = validator.validate_resume(result)
print(f\"Score: {validation['overall_score']:.1f}/100\")

Run tests:
from test_parser import TestSuite, TestCase
suite = TestSuite("My Tests")
suite.add_test(TestCase('file.pdf', expected_name='John Doe'))
suite.run_tests(extract_resume_data, '/path/to/resumes/')
suite.print_report()

═══════════════════════════════════════════════════════════════════════════
PERFORMANCE TIPS
═══════════════════════════════════════════════════════════════════════════

For faster processing:
• Set ENABLE_DETAILED_LOGGING = False
• Set ENABLE_VALIDATION = False (if not needed)
• Use SSD for file storage
• Close other applications

Typical speed:
• 1-2 seconds per resume (extraction + validation)
• 100 resumes ≈ 2-3 minutes
• 1000 resumes ≈ 30-50 minutes

═══════════════════════════════════════════════════════════════════════════
VALIDATION FIELD SCORES
═══════════════════════════════════════════════════════════════════════════

Field      Excellent  Good    Fair    Poor
───────────────────────────────────────────
Name       95-100     75-94   50-74   0-49
Email      100        70-99   35-69   0-34
Phone      95-100     85-94   70-84   0-69
Gender     90         70-89   50-69   0-49
Address    95-100     75-94   50-74   0-49
Skills     90-100     70-89   50-69   0-49

═══════════════════════════════════════════════════════════════════════════
QUICK JSON EXAMPLES
═══════════════════════════════════════════════════════════════════════════

resume_parsed.json entry:
{
  "file": "resume1.pdf",
  "name": "John Doe",
  "email": "john@example.com",
  "contact_number": "9876543210",
  "gender": "Male",
  "address": "123 Main St, New York, NY",
  "skills": ["Python", "Java", "SQL"]
}

validation_report.json summary:
{
  "total_resumes": 50,
  "average_score": 82.5,
  "quality_distribution": {
    "excellent": 20,
    "good": 18,
    "fair": 10,
    "poor": 2
  }
}

═══════════════════════════════════════════════════════════════════════════
KEYBOARD SHORTCUTS (in interactive menu)
═══════════════════════════════════════════════════════════════════════════

python run_tests.py
├─ Option 1: Single file analysis
├─ Option 2: Batch validation
├─ Option 3: Test suite
├─ Option 4: Debug extraction
├─ Option 5: Load previous results
└─ Option 0: Exit

═══════════════════════════════════════════════════════════════════════════
DOCUMENTATION FILES
═══════════════════════════════════════════════════════════════════════════

START_HERE.py              ← You are here! Overview
README_ENHANCEMENTS.md     ← Complete feature documentation
SETUP.md                   ← Installation & setup guide
This file                  ← Quick reference (print this!)

═══════════════════════════════════════════════════════════════════════════

📊 Resume Parser v2.0
Ready to process resumes with accuracy validation!

Questions? Check README_ENHANCEMENTS.md
Issues? Check SETUP.md Troubleshooting section
Ready to test? Run: python run_tests.py

═══════════════════════════════════════════════════════════════════════════
"""

if __name__ == '__main__':
    print(QUICK_COMMANDS)
    
    # Try to show as HTML in browser for better viewing
    try:
        import webbrowser
        # Create a simple HTML version
        html = f"""
        <html>
        <head>
            <title>Resume Parser Quick Reference</title>
            <style>
                body {{ font-family: monospace; background: #f5f5f5; padding: 20px; }}
                pre {{ background: white; padding: 20px; border-radius: 5px; }}
                code {{ background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <pre>{QUICK_COMMANDS}</pre>
        </body>
        </html>
        """
        # Save to temp file
        with open('/tmp/resume_parser_ref.html', 'w') as f:
            f.write(html)
    except:
        pass
