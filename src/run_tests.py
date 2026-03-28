"""
Resume Parser - Testing & Validation Runner
=============================================
Complete example showing how to:
1. Run batch processing with validation
2. Run tests on sample resumes
3. Generate reports
"""

import os
import sys
import json
from pathlib import Path

# Import the main parser module
from Main_Resume import (
    extract_text, extract_name, extract_contact_number,
    extract_email_from_resume, extract_gender, extract_address,
    extract_skills_from_resume, load_skills_from_csv,
    RESUME_FOLDER, SKILLS_CSV, OUTPUT_JSON, VALIDATION_JSON,
)

# Import validation module
try:
    from validation import ResumeValidator, print_validation_report
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    print("⚠️  validation module not found")

# Import testing module  
try:
    from test_parser import TestSuite, TestCase, TestResult
    TESTING_AVAILABLE = True
except ImportError:
    TESTING_AVAILABLE = False
    print("⚠️  test_parser module not found")


def extract_resume_data(file_path):
    """Extract all data from a single resume file."""
    try:
        text = extract_text(file_path)
        
        return {
            'file': os.path.basename(file_path),
            'name': extract_name(text),
            'contact_number': extract_contact_number(text),
            'email': extract_email_from_resume(text),
            'gender': extract_gender(text),
            'address': extract_address(text),
            'skills': extract_skills_from_resume(text, load_skills_from_csv(SKILLS_CSV)),
            'text_length': len(text),
        }
    except Exception as exc:
        return {
            'file': os.path.basename(file_path),
            'error': str(exc),
        }


def run_batch_validation(folder_path, output_report=True):
    """
    Run batch validation on all resumes in a folder.
    
    Args:
        folder_path: Path to folder with resumes
        output_report: Whether to print validation report
    
    Returns:
        Validation summary dict
    """
    if not VALIDATION_AVAILABLE:
        print("❌ Validation module not available")
        return None
    
    print(f"\n📊 Running batch validation on: {folder_path}\n")
    
    # Find all resume files
    supported_exts = {'.pdf', '.doc', '.docx'}
    resume_files = [f for f in os.listdir(folder_path) 
                   if os.path.splitext(f)[1].lower() in supported_exts]
    
    if not resume_files:
        print(f"❌ No resume files found in {folder_path}")
        return None
    
    print(f"Found {len(resume_files)} resume files\n")
    
    # Extract data from all resumes
    results = []
    for fname in resume_files:
        fpath = os.path.join(folder_path, fname)
        result = extract_resume_data(fpath)
        results.append(result)
        status = "✅" if 'error' not in result else "❌"
        print(f"  {status} {fname}")
    
    # Validate batch
    validator = ResumeValidator()
    validation_summary = validator.validate_batch(results)
    
    # Print report
    if output_report:
        print_validation_report(validation_summary)
    
    return validation_summary


def run_sample_tests(resume_folder):
    """
    Run tests on sample resumes.
    
    You need to update the test cases with actual expected values
    from your sample resume files.
    """
    if not TESTING_AVAILABLE:
        print("❌ Testing module not available")
        return None
    
    print(f"\n🧪 Running sample tests\n")
    
    # Create test suite
    suite = TestSuite("Resume Parser Sample Tests")
    
    # Add your test cases here
    # IMPORTANT: Update these with actual values from your test files
    suite.add_tests(
        TestCase(
            'sample1.pdf',
            expected_name='John Doe',  # Update with actual name from your resume
            expected_email='john.doe@example.com',  # Update with actual email
            expected_phone='9876543210',  # Update with actual phone
            expected_skills=['Python', 'Java'],  # Update with actual skills
            description='Test standard resume format'
        ),
    )
    
    # Run tests
    try:
        results = suite.run_tests(extract_resume_data, resume_folder)
        
        # Print report
        suite.print_report()
        
        return suite.get_summary()
    except Exception as exc:
        print(f"❌ Error running tests: {exc}")
        return None


def quick_resume_analysis(file_path):
    """Quick analysis of a single resume."""
    print(f"\n📄 Analyzing: {os.path.basename(file_path)}\n")
    
    result = extract_resume_data(file_path)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"Name:        {result['name'] or '❌ Not found'}")
    print(f"Email:       {result['email'] or '❌ Not found'}")
    print(f"Phone:       {result['contact_number'] or '❌ Not found'}")
    print(f"Gender:      {result['gender'] or '❌ Not found'}")
    print(f"Address:     {result['address'][:50] + '...' if result['address'] else '❌ Not found'}")
    print(f"Skills:      {', '.join(result['skills'][:5]) if result['skills'] else '❌ Not found'}")
    print(f"Text Length: {result['text_length']} characters")
    
    # Validate this single result
    if VALIDATION_AVAILABLE:
        validator = ResumeValidator()
        validation = validator.validate_resume(result)
        print(f"\nValidation Score: {validation['overall_score']:.1f}/100 ({validation['quality_level'].upper()})")


def compare_extraction_methods(file_path):
    """Compare different PDF extraction methods for debugging."""
    print(f"\n🔍 Comparing extraction methods for: {os.path.basename(file_path)}\n")
    
    try:
        text = extract_text(file_path)
        print(f"✅ Extraction successful")
        print(f"   Text length: {len(text)} characters")
        print(f"   First 200 chars: {text[:200]}")
    except Exception as exc:
        print(f"❌ Extraction failed: {exc}")


def generate_accuracy_report(results_list):
    """Generate detailed accuracy report from results."""
    if not VALIDATION_AVAILABLE:
        print("❌ Validation module not available")
        return
    
    validator = ResumeValidator()
    summary = validator.validate_batch(results_list)
    
    print("\n📊 ACCURACY REPORT\n")
    print(f"Average Score: {summary['average_score']:.1f}/100")
    print(f"Score Range: {summary['min_score']:.1f} - {summary['max_score']:.1f}")
    
    print("\nQuality Distribution:")
    for level in ['excellent', 'good', 'fair', 'poor']:
        count = summary['quality_distribution'].get(level, 0)
        pct = summary['quality_percentage'].get(level, 0)
        print(f"  {level.capitalize()}: {count} ({pct:.1f}%)")
    
    print("\nField-Level Accuracy:")
    for result in summary['validated_results'][:5]:  # Show first 5
        print(f"\n  {result['file']}:")
        for field, details in result['fields'].items():
            if details['score'] > 0:
                print(f"    {field}: {details['score']:.0f}/100 - {details['reason']}")


def main():
    """Main menu for testing and validation."""
    print("\n" + "="*80)
    print("📊 RESUME PARSER - TESTING & VALIDATION")
    print("="*80 + "\n")
    
    print("Options:")
    print("  1. Quick analysis of a single resume")
    print("  2. Run batch validation on a folder")
    print("  3. Run test suite on sample resumes")
    print("  4. Debug extraction method for a file")
    print("  5. Load and validate previous results from JSON")
    print("  0. Exit")
    
    choice = input("\nEnter your choice (0-5): ").strip()
    
    if choice == '1':
        # Quick analysis
        file_path = input("Enter path to resume file: ").strip()
        if os.path.exists(file_path):
            quick_resume_analysis(file_path)
        else:
            print(f"❌ File not found: {file_path}")
    
    elif choice == '2':
        # Batch validation
        folder_path = input(f"Enter folder path (default: {RESUME_FOLDER}): ").strip()
        if not folder_path:
            folder_path = RESUME_FOLDER
        
        if os.path.isdir(folder_path):
            run_batch_validation(folder_path)
        else:
            print(f"❌ Folder not found: {folder_path}")
    
    elif choice == '3':
        # Run tests
        folder_path = input("Enter folder containing test resumes: ").strip()
        if os.path.isdir(folder_path):
            run_sample_tests(folder_path)
        else:
            print(f"❌ Folder not found: {folder_path}")
    
    elif choice == '4':
        # Debug extraction
        file_path = input("Enter path to resume file: ").strip()
        if os.path.exists(file_path):
            compare_extraction_methods(file_path)
        else:
            print(f"❌ File not found: {file_path}")
    
    elif choice == '5':
        # Load and validate previous results
        if os.path.exists(OUTPUT_JSON):
            with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"\n✅ Loaded {len(results)} results from {OUTPUT_JSON}")
            generate_accuracy_report(results)
        else:
            print(f"❌ Results file not found: {OUTPUT_JSON}")
    
    elif choice == '0':
        print("Goodbye!")
    
    else:
        print("❌ Invalid choice")


if __name__ == '__main__':
    # Run the main menu if this script is executed directly
    if len(sys.argv) > 1:
        # Command-line arguments for automated testing
        if sys.argv[1] == '--batch':
            folder = sys.argv[2] if len(sys.argv) > 2 else RESUME_FOLDER
            run_batch_validation(folder)
        elif sys.argv[1] == '--quick':
            file_path = sys.argv[2] if len(sys.argv) > 2 else ''
            if file_path and os.path.exists(file_path):
                quick_resume_analysis(file_path)
        elif sys.argv[1] == '--test':
            folder = sys.argv[2] if len(sys.argv) > 2 else RESUME_FOLDER
            run_sample_tests(folder)
    else:
        # Interactive menu
        main()
