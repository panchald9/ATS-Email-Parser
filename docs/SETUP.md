"""
RESUME PARSER - SETUP & INSTALLATION GUIDE
==========================================

Complete instructions for setting up the enhanced Resume Parser.
"""

# SYSTEM REQUIREMENTS
####################
"""
- Python 3.7+
- Windows/Linux/macOS
- 50MB+ disk space for dependencies
"""

# STEP 1: INSTALL CORE DEPENDENCIES
###################################
"""
Run in command line:

pip install pdfminer.six
pip install python-docx
pip install python-docx  # for DOCX support

Optional (for NLP name extraction):

pip install spacy
python -m spacy download en_core_web_sm

pip install names-dataset  # for gender inference

For legacy .doc files:

pip install textract
"""

# STEP 2: VERIFY INSTALLATION
#############################
"""
Test that all dependencies are installed:

python -c "import pdfminer; import docx; print('✅ Core deps OK')"
python -c "import spacy; print('✅ Spacy OK')"
python -c "from names_dataset import NameDataset; print('✅ Names-dataset OK')"
python -c "import textract; print('✅ Textract OK')"
"""

# STEP 3: DIRECTORY STRUCTURE
#############################
"""
Your project should look like:

ATS Email Parser/
├── Main Resume.py              ← Main parser (UPDATED)
├── validation.py               ← NEW: Validation module
├── test_parser.py              ← NEW: Testing framework
├── run_tests.py                ← NEW: Test runner
├── README_ENHANCEMENTS.md       ← NEW: Documentation
├── Skill.csv                   ← Skills reference
├── output/
│   ├── resume_parsed.json      ← Results (auto-generated)
│   ├── validation_report.json  ← Validation results (auto-generated)
│   └── parser.log              ← Processing log (auto-generated)
├── Resume/                     ← Default resume folder
│   ├── resume1.pdf
│   ├── resume2.docx
│   └── ...
└── pending resume/             ← Alternative folder
    ├── resume1.pdf
    └── ...
"""

# STEP 4: CONFIGURATION
#######################
"""
Edit Main Resume.py to configure:

1. RESUME_FOLDER
   Default folder to process
   - Default: "D:\\Ktas Project\\ATS\\ATS Email Parser\\Resume"
   - Change to your folder path

2. SKILLS_CSV
   Location of skills reference file
   - Expected format: CSV with 'skill' column

3. PROCESS_FOLDER
   Can be changed in the main() function (line ~1350)
   - Currently defaults to "pending resume" folder if it exists

4. ENABLE_VALIDATION
   Set to True to generate validation reports
   - Default: True

5. ENABLE_DETAILED_LOGGING
   Set to True for verbose output
   - Default: True
"""

# STEP 5: RUN BATCH PROCESSING
##############################
"""
Option A: Direct execution (processes PROCESS_FOLDER)

    python "Main Resume.py"

Option B: Using the test runner

    python run_tests.py
    # Select option 2 (Batch Validation)
    # Enter folder path

Option C: From Python script

    from Main_Resume import *
    from validation import ResumeValidator
    
    # Process resumes (see Main Resume.py __main__ section)
"""

# STEP 6: VALIDATE ACCURACY
###########################
"""
After batch processing, check quality:

1. View validation_report.json for accuracy scores
2. Check quality distribution (excellent/good/fair/poor)
3. Identify problematic resumes

Example:
    
    import json
    with open('output/validation_report.json') as f:
        report = json.load(f)
    
    print(f"Average Score: {report['average_score']:.1f}/100")
    print(f"Quality: {report['quality_distribution']}")
"""

# STEP 7: TEST ON SAMPLES
########################
"""
Create test cases for validation:

1. Choose 3-5 sample resumes with known values
2. Create test cases in run_tests.py:

   from test_parser import TestCase
   
   TestCase(
       'sample1.pdf',
       expected_name='John Doe',
       expected_email='john@example.com',
       expected_phone='9876543210',
       expected_skills=['Python', 'Java'],
       description='Standard format resume'
   )

3. Run tests:

   python run_tests.py
   # Choose option 3
"""

# STEP 8: TROUBLESHOOT ISSUES
#############################
"""
If extraction fails:

1. Check pdfminer installation:
   
   python -c "from pdfminer.high_level import extract_text; print('OK')"

2. Try manual extraction:
   
   python run_tests.py
   # Choose option 1 (Quick Analysis)
   # Enter resume path

3. Review parser.log for error messages

4. For DOCX issues:
   
   python -c "from docx import Document; print('OK')"

5. For DOC issues:
   
   python -c "import textract; print('OK')"
"""

# QUICK TEST
###########
"""
Test the parser on a single file:

python run_tests.py
# Menu option 1: Quick Resume Analysis
# Enter path to a test resume

Expected output:
    Name:        [extracted name]
    Email:       [extracted email]
    Phone:       [extracted phone]
    Skills:      [extracted skills]
    Validation Score: X/100 (QUALITY_LEVEL)
"""

# COMMON ISSUES & SOLUTIONS
###########################
"""
Issue: "pdfminer module not found"
Solution: pip install pdfminer.six

Issue: "python-docx module not found"
Solution: pip install python-docx

Issue: "No resume files found"
Solution: 
- Check folder path is correct
- Verify files have .pdf, .docx, or .doc extension
- Check folder exists and has read permissions

Issue: "Empty text extracted"
Solution:
- May be scanned PDF (image-based)
- Try converting to digital PDF
- Check if file is corrupted

Issue: "Email/Phone not extracted"
Solution:
- Verify resume contains this information
- Check the expected format
- Review parser.log for details

Issue: "Validation scores low"
Solution:
- Review validation_report.json for specific issues
- Check each field's validation score
- May indicate extraction or resume format problems
"""

# PERFORMANCE TIPS
#################
"""
For large batches (100+ resumes):

1. Disable detailed logging to speed up:
   ENABLE_DETAILED_LOGGING = False

2. Process in smaller batches if memory is limited

3. Validation adds ~10% overhead - disable if not needed:
   ENABLE_VALIDATION = False

4. Use SSD for faster file I/O

Typical speed:
- PDF extraction: 1-2 seconds per file
- Total processing: 2-3 seconds per file
- 1000 resumes: ~30-50 minutes
"""

# NEXT STEPS
###########
"""
1. ✅ Install all dependencies (Step 1-2)
2. ✅ Verify directory structure (Step 3)
3. ✅ Configure paths (Step 4)
4. ✅ Test single file (Step 8 / Quick Test)
5. ✅ Run batch processing (Step 5)
6. ✅ Check validation results (Step 6)
7. ✅ Create test cases (Step 7)
8. ✅ Review accuracy (Step 6 again)

You're ready to process resumes!
"""

# FILE REFERENCE
###############
"""
New Files Added:
- validation.py           - Accuracy validation & scoring
- test_parser.py          - Test framework & test cases
- run_tests.py            - Interactive test runner
- README_ENHANCEMENTS.md  - Complete documentation

Modified Files:
- Main Resume.py          - Enhanced with validation & logging

Unchanged Files:
- Skill.csv               - Skills reference (same format)
- All extraction logic    - Improved error handling only
"""

# SUPPORT
########
"""
If you encounter issues:

1. Check README_ENHANCEMENTS.md for detailed docs
2. Review parser.log for error messages
3. Run run_tests.py with option 4 (Debug Extraction)
4. Check validation_report.json for quality issues

For persistent issues:
- Verify Python version: python --version (need 3.7+)
- Check all dependencies: pip list | grep -E "pdfminer|docx|spacy|textract"
- Review error messages in detail
"""

if __name__ == '__main__':
    """Quick verification script"""
    import sys
    
    print("Resume Parser - Dependency Checker\n")
    
    deps = {
        'pdfminer': 'pdfminer.high_level',
        'python-docx': 'docx',
        'spacy (optional)': 'spacy',
        'names-dataset (optional)': 'names_dataset',
        'textract (optional)': 'textract',
    }
    
    all_ok = True
    for dep_name, import_name in deps.items():
        try:
            __import__(import_name)
            print(f"✅ {dep_name}: OK")
        except ImportError:
            is_optional = 'optional' in dep_name
            status = "⚠️  OPTIONAL" if is_optional else "❌ REQUIRED"
            print(f"{status} {dep_name}: NOT INSTALLED")
            if not is_optional:
                all_ok = False
    
    print()
    if all_ok:
        print("✅ All required dependencies installed!")
        print("\nYou can now run:")
        print("  python \"Main Resume.py\"")
        print("  python run_tests.py")
    else:
        print("❌ Missing required dependencies. Please run:")
        print("  pip install pdfminer.six python-docx")
        sys.exit(1)
