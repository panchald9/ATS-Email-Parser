"""
Resume Parser Testing Module
==============================
Test suite for validating resume parsing accuracy on sample files.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class TestCase:
    """Single test case for resume parsing."""
    
    def __init__(self, 
                 file_name: str,
                 expected_name: str = None,
                 expected_email: str = None,
                 expected_phone: str = None,
                 expected_skills: List[str] = None,
                 description: str = ""):
        """
        Args:
            file_name: Resume file to test
            expected_name: Expected extracted name
            expected_email: Expected extracted email
            expected_phone: Expected extracted phone
            expected_skills: Expected skills (subset)
            description: Test description
        """
        self.file_name = file_name
        self.expected_name = expected_name or ""
        self.expected_email = expected_email or ""
        self.expected_phone = expected_phone or ""
        self.expected_skills = expected_skills or []
        self.description = description
    
    def __repr__(self):
        return f"TestCase({self.file_name})"


class TestResult:
    """Result of a single test."""
    
    def __init__(self, test_case: TestCase, actual_data: Dict):
        self.test_case = test_case
        self.actual_data = actual_data
        self.checks = {
            'name': False,
            'email': False,
            'phone': False,
            'skills': False,
        }
        self.messages = []
        self.passed = False
    
    def check_name(self, exact=True, ignore_case=True) -> bool:
        """Check if extracted name matches expected."""
        actual = self.actual_data.get('name', '')
        expected = self.test_case.expected_name
        
        if not expected:
            self.checks['name'] = None  # Not tested
            return True
        
        if ignore_case:
            actual = (actual or '').lower().strip()
            expected = expected.lower().strip()
        else:
            actual = (actual or '').strip()
            expected = expected.strip()
        
        if exact:
            passed = actual == expected
            if not passed:
                self.messages.append(f"❌ Name mismatch: expected '{expected}', got '{actual}'")
            else:
                self.messages.append(f"✅ Name matches: '{actual}'")
        else:
            # Check if all expected words are in actual
            exp_words = set(expected.split())
            act_words = set(actual.split())
            passed = exp_words.issubset(act_words)
            if not passed:
                self.messages.append(f"⚠️  Name partial match: expected words {exp_words}, got {act_words}")
            else:
                self.messages.append(f"✅ Name contains expected: '{actual}'")
        
        self.checks['name'] = passed
        return passed
    
    def check_email(self, exact=True) -> bool:
        """Check if extracted email matches expected."""
        actual = (self.actual_data.get('email') or '').lower().strip()
        expected = (self.test_case.expected_email or '').lower().strip()
        
        if not expected:
            self.checks['email'] = None  # Not tested
            return True
        
        passed = actual == expected
        
        if not passed:
            self.messages.append(f"❌ Email mismatch: expected '{expected}', got '{actual}'")
        else:
            self.messages.append(f"✅ Email matches: '{actual}'")
        
        self.checks['email'] = passed
        return passed
    
    def check_phone(self, exact=True) -> bool:
        """Check if extracted phone matches expected."""
        actual = (self.actual_data.get('contact_number') or '').strip()
        expected = (self.test_case.expected_phone or '').strip()
        
        if not expected:
            self.checks['phone'] = None  # Not tested
            return True
        
        # Normalize for comparison (remove spaces, dashes)
        import re
        actual_digits = re.sub(r'\D', '', actual)
        expected_digits = re.sub(r'\D', '', expected)
        
        passed = actual_digits == expected_digits
        
        if not passed:
            self.messages.append(f"⚠️  Phone mismatch: expected '{expected}', got '{actual}'")
        else:
            self.messages.append(f"✅ Phone matches: '{actual}'")
        
        self.checks['phone'] = passed
        return passed
    
    def check_skills(self, min_match_ratio=0.8) -> bool:
        """Check if extracted skills contain expected skills."""
        actual = [s.lower().strip() for s in self.actual_data.get('skills', [])]
        expected = [s.lower().strip() for s in self.test_case.expected_skills]
        
        if not expected:
            self.checks['skills'] = None  # Not tested
            return True
        
        matched = sum(1 for exp in expected if any(exp in act or act in exp for act in actual))
        match_ratio = matched / len(expected) if expected else 1.0
        
        passed = match_ratio >= min_match_ratio
        
        if not passed:
            self.messages.append(
                f"⚠️  Skills: {matched}/{len(expected)} matched ({match_ratio*100:.0f}%). "
                f"Expected: {expected}, Got: {actual[:5]}"
            )
        else:
            self.messages.append(
                f"✅ Skills: {matched}/{len(expected)} matched ({match_ratio*100:.0f}%)"
            )
        
        self.checks['skills'] = passed
        return passed
    
    def calculate_pass_fail(self, require_all=False) -> bool:
        """Calculate overall pass/fail."""
        checks = [v for v in self.checks.values() if v is not None]
        
        if not checks:
            self.passed = True
            self.messages.append("ℹ️  No specific checks configured")
            return True
        
        if require_all:
            self.passed = all(checks)
        else:
            self.passed = any(checks)
        
        return self.passed
    
    def summary(self) -> str:
        """Get summary string."""
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} | {self.test_case.file_name}"


class TestSuite:
    """Collection of test cases."""
    
    def __init__(self, name: str = "Resume Parser Tests"):
        self.name = name
        self.tests = []
        self.results = []
    
    def add_test(self, test_case: TestCase):
        """Add a test case."""
        self.tests.append(test_case)
    
    def add_tests(self, *test_cases: TestCase):
        """Add multiple test cases."""
        self.tests.extend(test_cases)
    
    def run_tests(self, extract_func, resume_folder: str) -> List[TestResult]:
        """
        Run all tests using provided extraction function.
        
        Args:
            extract_func: Function that takes file path and returns extracted dict
            resume_folder: Folder containing test resume files
        
        Returns:
            List of TestResult objects
        """
        self.results = []
        
        print(f"\n{'='*80}")
        print(f"🧪 RUNNING TEST SUITE: {self.name}")
        print(f"{'='*80}\n")
        
        for i, test in enumerate(self.tests, 1):
            file_path = os.path.join(resume_folder, test.file_name)
            
            if not os.path.exists(file_path):
                result = TestResult(test, {})
                result.passed = False
                result.messages.append(f"❌ Test file not found: {file_path}")
                self.results.append(result)
                print(f"  [{i}/{len(self.tests)}] ❌ FILE NOT FOUND: {test.file_name}")
                continue
            
            try:
                # Extract data
                actual_data = extract_func(file_path)
                result = TestResult(test, actual_data)
                
                # Run checks
                result.check_name(exact=True, ignore_case=True)
                result.check_email(exact=True)
                result.check_phone(exact=True)
                result.check_skills(min_match_ratio=0.6)
                
                # Calculate overall result
                result.calculate_pass_fail(require_all=False)
                
                self.results.append(result)
                
                # Print result
                print(f"  [{i}/{len(self.tests)}] {result.summary()}")
                if test.description:
                    print(f"       Description: {test.description}")
                for msg in result.messages:
                    print(f"       {msg}")
                
            except Exception as exc:
                result = TestResult(test, {})
                result.passed = False
                result.messages.append(f"❌ Extraction error: {exc}")
                self.results.append(result)
                print(f"  [{i}/{len(self.tests)}] ❌ ERROR: {test.file_name} - {exc}")
        
        return self.results
    
    def get_summary(self) -> Dict:
        """Get test summary statistics."""
        if not self.results:
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'pass_rate': 0,
                'coverage': {}
            }
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        # Coverage by field
        coverage = {
            'name': 0,
            'email': 0,
            'phone': 0,
            'skills': 0,
        }
        
        for result in self.results:
            for field in coverage.keys():
                check = result.checks.get(field)
                if check is True:
                    coverage[field] += 1
        
        return {
            'total': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'coverage': {k: f"{v}/{total} ({v/total*100:.0f}%)" for k, v in coverage.items()}
        }
    
    def print_report(self):
        """Print detailed test report."""
        summary = self.get_summary()
        
        print(f"\n{'='*80}")
        print(f"📋 TEST REPORT: {self.name}")
        print(f"{'='*80}\n")
        
        print(f"Overall Results:")
        print(f"  Total Tests: {summary['total']}")
        print(f"  Passed: {summary['passed']} ✅")
        print(f"  Failed: {summary['failed']} ❌")
        print(f"  Pass Rate: {summary['pass_rate']:.1f}%")
        
        print(f"\nField Coverage:")
        for field, coverage in summary['coverage'].items():
            print(f"  {field.capitalize()}: {coverage}")
        
        print(f"\n{'='*80}\n")
        
        return summary


def create_sample_test_suite() -> TestSuite:
    """Create sample test suite for demonstration."""
    suite = TestSuite("Sample Resume Parser Tests")
    
    # Example test cases - adjust these based on your actual test files
    suite.add_tests(
        TestCase(
            'sample1.pdf',
            expected_name='John Doe',
            expected_email='john.doe@example.com',
            expected_phone='9876543210',
            expected_skills=['Python', 'Java', 'JavaScript'],
            description='Standard resume format'
        ),
        TestCase(
            'sample2.pdf',
            expected_name='Jane Smith',
            expected_email='jane.smith@company.com',
            expected_phone='+919876543210',
            expected_skills=['SQL', 'Database', 'Management'],
            description='Resume with international phone format'
        ),
        TestCase(
            'sample3.pdf',
            expected_name='Robert Johnson',
            expected_email='robert.j@email.co.in',
            expected_phone='8765432109',
            expected_skills=['AWS', 'Cloud', 'DevOps'],
            description='Technical skills focused resume'
        ),
    )
    
    return suite


if __name__ == '__main__':
    print("Resume Parser Testing Module")
    print("Usage: Import this module and create a TestSuite with test cases")
    print("       Run tests using: suite.run_tests(extract_function, '/path/to/resumes')")
