"""
RESUME PARSER - ENHANCEMENTS DOCUMENTATION
===========================================

This document describes the validation, testing, and batch processing
enhancements added to the Resume Parser system.
"""

# NEW FEATURES & MODULES
# ======================

## 1. VALIDATION MODULE (validation.py)
###################################

### Purpose
- Provides accuracy scoring and validation for extracted resume data
- Checks data quality against predefined rules
- Generates batch validation reports

### Key Classes

**ValidationRules**
- Email validation patterns (RFC 5322 simplified)
- Phone number patterns (India & International)
- Gender, address, name constraints
- Skill validation rules

**AccuracyScore**
- score_email(): Validates email format, returns (is_valid, score, reason)
- score_phone(): Validates phone number, returns (is_valid, score, reason)
- score_name(): Validates name format, returns (is_valid, score, reason)
- score_gender(): Validates gender field, returns (is_valid, score, reason)
- score_address(): Validates address format, returns (is_valid, score, reason)
- score_skills(): Validates skills list, returns (is_valid, score, reason)

**ResumeValidator**
- validate_resume(): Validates single resume, returns detailed validation dict
- validate_batch(): Validates multiple resumes, returns summary statistics
- Returns quality levels: 'excellent' (90+), 'good' (75+), 'fair' (60+), 'poor' (<60)

### Usage Example

```python
from validation import ResumeValidator

validator = ResumeValidator()

# Validate single resume
resume_data = {
    'file': 'sample.pdf',
    'name': 'John Doe',
    'email': 'john@example.com',
    'contact_number': '9876543210',
    'gender': 'Male',
    'address': '123 Main St, New York, NY',
    'skills': ['Python', 'Java'],
}

result = validator.validate_resume(resume_data)
print(f"Overall Score: {result['overall_score']:.1f}/100")
print(f"Quality: {result['quality_level']}")

# Validate batch
results_list = [resume1, resume2, resume3, ...]
summary = validator.validate_batch(results_list)
print(f"Average Score: {summary['average_score']:.1f}/100")
```

### Validation Scoring

Each field (name, email, phone, etc.) is scored 0-100:
- **100**: Perfect/valid format
- **75-99**: Valid with minor issues
- **50-74**: Acceptable but questionable
- **25-49**: Invalid with minor salvageable content
- **0-24**: Invalid/missing

Overall score is the average of all field scores.

---

## 2. TESTING MODULE (test_parser.py)
####################################

### Purpose
- Framework for creating and running test cases on resume samples
- Validates extraction accuracy against known expected values
- Generates detailed test reports

### Key Classes

**TestCase**
```python
TestCase(
    file_name='sample.pdf',
    expected_name='John Doe',
    expected_email='john@example.com',
    expected_phone='9876543210',
    expected_skills=['Python', 'Java'],
    description='Standard resume format'
)
```

**TestSuite**
- add_test(): Add single test case
- add_tests(): Add multiple test cases
- run_tests(): Execute all tests
- get_summary(): Get statistics
- print_report(): Print detailed results

**TestResult**
- check_name(): Validate extracted name
- check_email(): Validate extracted email
- check_phone(): Validate extracted phone
- check_skills(): Validate extracted skills
- calculate_pass_fail(): Determine overall pass/fail

### Usage Example

```python
from test_parser import TestSuite, TestCase

# Create test suite
suite = TestSuite("My Resume Tests")

# Add test cases with known expected values
suite.add_tests(
    TestCase('resume1.pdf', 
             expected_name='John Doe',
             expected_email='john@example.com',
             expected_phone='9876543210',
             expected_skills=['Python', 'Java']),
    TestCase('resume2.pdf',
             expected_name='Jane Smith',
             expected_email='jane@company.com'),
)

# Run tests
from Main_Resume import extract_resume_data
results = suite.run_tests(extract_resume_data, '/path/to/resumes/')

# Print report
suite.print_report()
summary = suite.get_summary()
print(f"Pass Rate: {summary['pass_rate']:.1f}%")
```

### Test Matching

- **Name**: Case-insensitive exact match
- **Email**: Case-insensitive exact match
- **Phone**: Digit-wise comparison (ignores formatting)
- **Skills**: Fuzzy matching (at least 60% of expected skills found)

---

## 3. ENHANCED BATCH PROCESSING (Main Resume.py)
##############################################

### Improvements

**Better Error Handling**
- Improved PDF/DOC/DOCX extraction with fallback mechanisms
- Detailed error messages indicating failure point
- Graceful handling of corrupted or unreadable files
- Extracts partial data when full extraction fails

**Logging System**
- Console output + file logging (output/parser.log)
- Timestamps for all operations
- Detailed messages for debugging

**Validation Integration**
- Automatic accuracy validation after extraction
- Quality scoring for each resume
- Batch statistics and reports

**Processing Statistics**
```
📊 PROCESSING SUMMARY:
   Total files processed: 50
   Successfully parsed: 48 (96%)
   Extraction errors: 2 (4%)

📋 EXTRACTION QUALITY:
   Names found: 47/50 (94%)
   Emails found: 46/50 (92%)
   Phones found: 44/50 (88%)
   Resumes with skills: 49/50 (98%)
```

**Configuration Options**

```python
# In Main Resume.py

RESUME_FOLDER = r"D:\path\to\resumes"  # Default folder
SKILLS_CSV = "Skill.csv"  # Skills reference file
OUTPUT_JSON = "output/resume_parsed.json"  # Results file
VALIDATION_JSON = "output/validation_report.json"  # Validation results

ENABLE_VALIDATION = True  # Enable accuracy checking
ENABLE_DETAILED_LOGGING = True  # Enable verbose logging
LOG_FILE = "output/parser.log"  # Log file location
```

---

## 4. TESTING & VALIDATION RUNNER (run_tests.py)
##############################################

### Interactive Tool for Testing & Validation

**Features**
- Menu-driven interface
- Single resume analysis
- Batch validation
- Test suite execution
- Extraction method debugging
- Report generation

**Usage**

```bash
# Interactive mode
python run_tests.py

# Command-line batch validation
python run_tests.py --batch "D:\path\to\resumes"

# Quick analysis of single file
python run_tests.py --quick "D:\path\to\resume.pdf"

# Run test suite
python run_tests.py --test "D:\path\to\samples"
```

**Menu Options**

1. **Quick Resume Analysis** - Analyze single file with details
2. **Batch Validation** - Run validation on folder of resumes
3. **Test Suite** - Run predefined test cases
4. **Debug Extraction** - Compare extraction methods
5. **Load Previous Results** - Analyze saved validation reports

---

## 5. PDF & DOC EXTRACTION IMPROVEMENTS
#####################################

### Enhanced extract_text() Function

**Handles Multiple Formats**
- PDF (via pdfminer)
- DOCX (via python-docx)
- DOC (via textract)

**Error Recovery**
```python
try:
    # Attempt extraction
    text = pdf_extract_text(path)
    
    # If empty, report warning
    if not text:
        print("Warning: PDF extraction returned empty text")
    
except Exception as pdf_err:
    # Log detailed error
    error = f"pdfminer error: {str(pdf_err)[:100]}"
```

**File Validation**
- Checks file exists before processing
- Validates extracted text is not empty
- Provides specific error messages

**Dependency Handling**
- Gracefully handles missing optional libraries
- Suggests installation commands
- Falls back when dependencies unavailable

### Configuration

All optional dependencies are listed in Main Resume.py header:

```python
# Optional speed-ups (install if available):
pip install spacy && python -m spacy download en_core_web_sm
pip install names-dataset
pip install textract   # for legacy .doc files
```

---

## OUTPUT FILES
##############

### 1. resume_parsed.json
Main extraction results:
```json
[
  {
    "file": "resume1.pdf",
    "name": "John Doe",
    "contact_number": "9876543210",
    "email": "john@example.com",
    "gender": "Male",
    "address": "123 Main St, New York, NY",
    "skills": ["Python", "Java", "SQL"]
  },
  ...
]
```

### 2. validation_report.json
Validation summary with scores:
```json
{
  "total_resumes": 50,
  "average_score": 82.5,
  "quality_distribution": {
    "excellent": 25,
    "good": 15,
    "fair": 8,
    "poor": 2
  },
  "validated_results": [
    {
      "file": "resume1.pdf",
      "overall_score": 95.0,
      "quality_level": "excellent",
      "fields": {
        "name": {"valid": true, "score": 100, "reason": "Valid name format"},
        "email": {"valid": true, "score": 100, "reason": "Email valid"},
        ...
      }
    }
  ]
}
```

### 3. parser.log
Detailed processing log:
```
📄 Loaded 500 skills from: Skill.csv
📂 Processing 50 resume file(s) from: \pending resume

1  resume1.pdf  John Doe          9876543210  Male  john@example.com
   Address: 123 Main St, New York, NY...
   Skills [12]: Python, Java, SQL, JavaScript, ...

...

📊 PROCESSING SUMMARY:
   Total files processed: 50
   Successfully parsed: 48 (96%)
   ...
```

---

## QUICK START GUIDE
###################

### 1. Basic Batch Processing (No Validation)

```python
from Main_Resume import *

# Run the main script
if __name__ == '__main__':
    # Just execute Main Resume.py normally
    # Results saved to output/resume_parsed.json
```

### 2. With Validation

```python
# Enable validation in Main Resume.py
ENABLE_VALIDATION = True

# Run and get validation_report.json
python Main Resume.py
```

### 3. Test Accuracy on Samples

```python
from test_parser import TestSuite, TestCase
from Main_Resume import extract_resume_data

suite = TestSuite("Accuracy Tests")
suite.add_test(TestCase('sample.pdf', 
                        expected_name='John Doe',
                        expected_email='john@example.com'))
suite.run_tests(extract_resume_data, 'sample_folder/')
suite.print_report()
```

### 4. Interactive Testing

```bash
python run_tests.py
# Choose option from menu
```

---

## TROUBLESHOOTING
#################

### Issue: PDF extraction returns empty text
**Solution**: 
- Check if file is valid PDF
- May be scanned image-based PDF (needs OCR)
- Try with different PDF file
- Check pdfminer is installed: `pip install pdfminer.six`

### Issue: DOCX extraction fails
**Solution**:
- Install python-docx: `pip install python-docx`
- Check file is not corrupted
- Try opening in LibreOffice first

### Issue: Missing contact_number or email
**Solution**:
- Verify resume contains this information
- Check format (may need to fix extraction regex)
- Review extracted text in logs

### Issue: Skills not extracted
**Solution**:
- Verify Skill.csv exists and has skills listed
- Check resume mentions your skills exactly
- Review skill matching patterns

### Issue: Validation scores too low
**Solution**:
- Review specific field warnings in validation report
- May indicate extraction issues or resume format
- Run single resume analysis with run_tests.py

---

## CONFIGURATION REFERENCE
########################

### Main Resume.py Settings

```python
# Paths
RESUME_FOLDER = r"D:\path\to\Resume"        # Default folder
SKILLS_CSV = "Skill.csv"                    # Skills reference
OUTPUT_JSON = "output/resume_parsed.json"   # Results
VALIDATION_JSON = "output/validation_report.json"  # Validation

# Features
ENABLE_VALIDATION = True          # Enable accuracy checking
ENABLE_DETAILED_LOGGING = True    # Verbose logging
LOG_FILE = "output/parser.log"    # Log file

# Processing
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}
```

### Validation Rules

```python
# In validation.py - ValidationRules class
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 60
MIN_NAME_WORDS = 1
MAX_NAME_WORDS = 5

MIN_ADDRESS_LENGTH = 8
MAX_ADDRESS_LENGTH = 220

# Supported genders
VALID_GENDERS = {'Male', 'Female', 'm', 'f', ...}
```

---

## PERFORMANCE NOTES
###################

- Processing time: ~1-2 seconds per resume
- PDF extraction is slowest (pdfminer library)
- Validation adds ~10% to total time
- Logging adds minimal overhead

### Optimization Tips

1. Disable ENABLE_DETAILED_LOGGING if not needed
2. Process large batches in background
3. Use rolling output validation on first 10 files
4. Cache loaded skills_list for multiple runs

---

## NEXT STEPS
###########

1. **Test on your samples**: Run run_tests.py and test on sample resumes
2. **Adjust validation thresholds**: Modify validation.py if needed for your use case
3. **Create test suite**: Add your actual test cases with known expected values
4. **Monitor quality**: Check validation_report.json after batch runs
5. **Iterative improvement**: Use validation scores to identify extraction issues

---

## SUPPORT & DOCUMENTATION
##########################

For detailed API reference, see docstrings in:
- validation.py - ResumeValidator class
- test_parser.py - TestSuite class
- Main Resume.py - extract_* functions

For examples and usage patterns:
- run_tests.py - Complete usage examples
- test_parser.py - Sample test cases

---

Generated: 2024
Resume Parser Enhancement Pack v2.0
"""
