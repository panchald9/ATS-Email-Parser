"""
Validation & Accuracy Checking Module
======================================
Provides data validation, accuracy scoring, and quality checks for extracted resume data.
"""

import re
import json
from typing import Dict, List, Tuple, Optional


class ValidationRules:
    """Email validation patterns and rules."""
    
    # Email regex (RFC 5322 simplified)
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Phone number patterns (India & International)
    PHONE_PATTERNS = [
        r'^\+?1?\d{10}$',  # 10 digit US/Canada
        r'^\+91\d{10}$',   # India with country code
        r'^\d{10}$',       # India 10 digit
        r'^\+?[1-9]\d{1,14}$',  # International E.164
    ]
    
    # Gender validation
    VALID_GENDERS = {'Male', 'Female', 'male', 'female', 'M', 'F', 'm', 'f'}
    
    # Address length constraints
    MIN_ADDRESS_LENGTH = 8
    MAX_ADDRESS_LENGTH = 220
    
    # Name constraints
    MIN_NAME_LENGTH = 3
    MAX_NAME_LENGTH = 60
    MIN_NAME_WORDS = 1
    MAX_NAME_WORDS = 5


class AccuracyScore:
    """Calculate accuracy scores for extracted data."""
    
    @staticmethod
    def score_email(email: str) -> Tuple[bool, float, str]:
        """
        Validate email and assign accuracy score (0-100).
        Returns: (is_valid, score, reason)
        """
        if not email:
            return False, 0, "Email is empty"
        
        if not re.match(ValidationRules.EMAIL_PATTERN, email):
            return False, 20, "Email format invalid (wrong pattern)"
        
        # Check for common noise
        if email.count('.') > 3:
            return False, 40, "Too many dots in email"
        
        if '..' in email or email.endswith('.'):
            return False, 35, "Email has invalid structure (.. or ends with .)"
        
        if len(email) > 100:
            return False, 45, "Email suspiciously long"
        
        # Check for common TLDs
        common_tlds = {'com', 'org', 'net', 'edu', 'gov', 'in', 'co.in', 'org.in'}
        tld = email.split('.')[-1].lower()
        
        if tld not in common_tlds:
            return True, 70, "Email valid but uncommon TLD"
        
        return True, 100, "Email valid"
    
    @staticmethod
    def score_phone(phone: str) -> Tuple[bool, float, str]:
        """
        Validate phone and assign accuracy score (0-100).
        Returns: (is_valid, score, reason)
        """
        if not phone:
            return False, 0, "Phone is empty"
        
        digits = re.sub(r'\D', '', phone)
        
        if not (7 <= len(digits) <= 15):
            return False, 20, f"Phone has {len(digits)} digits (expected 7-15)"
        
        # Check for repeating digits (all same)
        if len(set(digits)) == 1:
            return False, 10, "Phone has all identical digits (likely invalid)"
        
        # Check if looks like year
        if re.match(r'^(19|20)\d{2}$', digits):
            return False, 15, "Phone looks like a year"
        
        # Validate length for common regions
        if len(digits) == 10:  # India standard
            return True, 95, "Valid Indian phone (10 digits)"
        elif len(digits) == 12 and phone.startswith('+'):
            return True, 90, "Valid international format with country code"
        elif 11 <= len(digits) <= 15:
            return True, 85, "Valid generic international format"
        
        return True, 75, "Phone format acceptable but not standard"
    
    @staticmethod
    def score_name(name: str) -> Tuple[bool, float, str]:
        """
        Validate name and assign accuracy score (0-100).
        Returns: (is_valid, score, reason)
        """
        if not name:
            return False, 0, "Name is empty"
        
        name_clean = name.strip()
        
        if len(name_clean) < ValidationRules.MIN_NAME_LENGTH:
            return False, 20, f"Name too short (< {ValidationRules.MIN_NAME_LENGTH} chars)"
        
        if len(name_clean) > ValidationRules.MAX_NAME_LENGTH:
            return False, 30, f"Name too long (> {ValidationRules.MAX_NAME_LENGTH} chars)"
        
        words = name_clean.split()
        word_count = len(words)
        
        if word_count < ValidationRules.MIN_NAME_WORDS:
            return False, 40, "Name has no words"
        
        if word_count > ValidationRules.MAX_NAME_WORDS:
            return False, 50, f"Name too many words ({word_count} > {ValidationRules.MAX_NAME_WORDS})"
        
        # Check for digits
        if any(ch.isdigit() for ch in name_clean):
            return False, 45, "Name contains digits"
        
        # Check for special characters
        if not re.match(r"^[A-Za-z\s\.\-\']+$", name_clean):
            return False, 55, "Name contains special characters"
        
        # Check capitalization
        if word_count >= 2:
            # At least first letters should be capitalized
            first_letters = [w[0] for w in words if w]
            capitalized = sum(1 for l in first_letters if l.isupper())
            if capitalized < word_count * 0.5:
                return False, 60, "Name capitalization looks wrong"
        
        return True, 95, "Valid name format"
    
    @staticmethod
    def score_gender(gender: str) -> Tuple[bool, float, str]:
        """
        Validate gender and assign accuracy score (0-100).
        Returns: (is_valid, score, reason)
        """
        if not gender:
            return False, 0, "Gender is empty"
        
        if gender not in ValidationRules.VALID_GENDERS:
            return False, 30, f"Gender '{gender}' not valid (expected Male/Female)"
        
        return True, 90, "Valid gender"
    
    @staticmethod
    def score_address(address: str) -> Tuple[bool, float, str]:
        """
        Validate address and assign accuracy score (0-100).
        Returns: (is_valid, score, reason)
        """
        if not address:
            return False, 0, "Address is empty"
        
        addr_clean = address.strip()
        
        if len(addr_clean) < ValidationRules.MIN_ADDRESS_LENGTH:
            return False, 25, f"Address too short (< {ValidationRules.MIN_ADDRESS_LENGTH} chars)"
        
        if len(addr_clean) > ValidationRules.MAX_ADDRESS_LENGTH:
            return False, 40, f"Address too long (> {ValidationRules.MAX_ADDRESS_LENGTH} chars)"
        
        # Address should have at least one digit or comma (structure indicator)
        has_digits = bool(re.search(r'\d', addr_clean))
        has_comma = ',' in addr_clean
        has_location_words = bool(re.search(
            r'\b(road|street|nagar|colony|city|state|india|pincode)\b',
            addr_clean, re.I
        ))
        
        score = 50
        if has_digits:
            score += 20
        if has_comma:
            score += 15
        if has_location_words:
            score += 20
        
        return True, min(score, 95), "Address appears valid"
    
    @staticmethod
    def score_skills(skills: List[str]) -> Tuple[bool, float, str]:
        """
        Validate skills list and assign accuracy score (0-100).
        Returns: (is_valid, score, reason)
        """
        if not skills:
            return False, 0, "No skills extracted"
        
        if len(skills) > 100:
            return False, 40, f"Too many skills ({len(skills)} > 100, likely noise)"
        
        # Check for obvious noise
        noise_patterns = [r'^\d+$', r'^[^a-zA-Z0-9+#\s]{5,}$']
        valid_skills = 0
        
        for skill in skills:
            is_noisy = any(re.match(p, skill) for p in noise_patterns)
            if not is_noisy and len(skill) >= 2:
                valid_skills += 1
        
        if valid_skills == 0:
            return False, 20, "All skills look like noise"
        
        validity_ratio = valid_skills / len(skills)
        score = 60 + (validity_ratio * 35)
        
        return True, score, f"{valid_skills}/{len(skills)} skills valid"


class ResumeValidator:
    """Comprehensive validation for resume extraction results."""
    
    def __init__(self):
        self.accuracy = AccuracyScore()
        self.validation_results = {}
    
    def validate_resume(self, resume_data: Dict) -> Dict:
        """
        Validate all fields in a resume extraction result.
        
        Returns dict with:
        {
            'file': filename,
            'overall_score': 0-100,
            'fields': {
                'name': {'valid': bool, 'score': float, 'reason': str},
                'email': {...},
                'phone': {...},
                'gender': {...},
                'address': {...},
                'skills': {...},
            },
            'warnings': [list of warnings],
            'quality_level': 'excellent'/'good'/'fair'/'poor'
        }
        """
        results = {
            'file': resume_data.get('file'),
            'fields': {},
            'warnings': [],
            'overall_score': 0,
            'quality_level': 'poor',
        }
        
        # Validate each field
        field_scores = []
        
        # Name validation
        name = resume_data.get('name')
        valid, score, reason = self.accuracy.score_name(name)
        results['fields']['name'] = {'valid': valid, 'score': score, 'reason': reason}
        field_scores.append(score)
        if not valid:
            results['warnings'].append(f"Name issue: {reason}")
        
        # Email validation
        email = resume_data.get('email')
        valid, score, reason = self.accuracy.score_email(email)
        results['fields']['email'] = {'valid': valid, 'score': score, 'reason': reason}
        field_scores.append(score)
        if not valid:
            results['warnings'].append(f"Email issue: {reason}")
        
        # Phone validation
        phone = resume_data.get('contact_number')
        valid, score, reason = self.accuracy.score_phone(phone)
        results['fields']['phone'] = {'valid': valid, 'score': score, 'reason': reason}
        field_scores.append(score)
        if not valid:
            results['warnings'].append(f"Phone issue: {reason}")
        
        # Gender validation
        gender = resume_data.get('gender')
        valid, score, reason = self.accuracy.score_gender(gender)
        results['fields']['gender'] = {'valid': valid, 'score': score, 'reason': reason}
        if gender:  # Only count if present
            field_scores.append(score)
        
        # Address validation
        address = resume_data.get('address')
        valid, score, reason = self.accuracy.score_address(address)
        results['fields']['address'] = {'valid': valid, 'score': score, 'reason': reason}
        if address:  # Only count if present
            field_scores.append(score)
        
        # Skills validation
        skills = resume_data.get('skills', [])
        valid, score, reason = self.accuracy.score_skills(skills)
        results['fields']['skills'] = {'valid': valid, 'score': score, 'reason': reason}
        if skills:  # Only count if present
            field_scores.append(score)
        
        # Calculate overall score (average of field scores)
        if field_scores:
            results['overall_score'] = sum(field_scores) / len(field_scores)
        
        # Determine quality level
        overall = results['overall_score']
        if overall >= 90:
            results['quality_level'] = 'excellent'
        elif overall >= 75:
            results['quality_level'] = 'good'
        elif overall >= 60:
            results['quality_level'] = 'fair'
        else:
            results['quality_level'] = 'poor'
        
        # Add cross-field warnings
        if resume_data.get('error'):
            results['warnings'].insert(0, f"Extraction error: {resume_data['error']}")
        
        if not name or not email:
            results['warnings'].append("⚠️ Missing critical fields (name or email)")
        
        return results
    
    def validate_batch(self, results_list: List[Dict]) -> Dict:
        """
        Validate a batch of resume extraction results.
        Returns summary statistics with validation details for each resume.
        """
        validated = []
        scores = []
        quality_counts = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        
        for result in results_list:
            val = self.validate_resume(result)
            validated.append(val)
            scores.append(val['overall_score'])
            quality_counts[val['quality_level']] += 1
        
        # Calculate batch statistics
        if scores:
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
        else:
            avg_score = min_score = max_score = 0
        
        summary = {
            'total_resumes': len(results_list),
            'average_score': round(avg_score, 2),
            'min_score': round(min_score, 2),
            'max_score': round(max_score, 2),
            'quality_distribution': quality_counts,
            'quality_percentage': {
                'excellent': round(quality_counts['excellent'] / len(results_list) * 100, 1) if results_list else 0,
                'good': round(quality_counts['good'] / len(results_list) * 100, 1) if results_list else 0,
                'fair': round(quality_counts['fair'] / len(results_list) * 100, 1) if results_list else 0,
                'poor': round(quality_counts['poor'] / len(results_list) * 100, 1) if results_list else 0,
            },
            'validated_results': validated,
        }
        
        return summary


def print_validation_report(validation_summary: Dict):
    """Pretty print validation report."""
    print("\n" + "═" * 80)
    print(f"📊 VALIDATION REPORT")
    print("═" * 80)
    print(f"\nBatch Summary:")
    print(f"  Total Resumes: {validation_summary['total_resumes']}")
    print(f"  Average Score: {validation_summary['average_score']:.1f}/100")
    print(f"  Score Range: {validation_summary['min_score']:.1f} - {validation_summary['max_score']:.1f}")
    
    print(f"\nQuality Distribution:")
    dist = validation_summary['quality_distribution']
    pct = validation_summary['quality_percentage']
    print(f"  ✅ Excellent: {dist['excellent']} ({pct['excellent']:.1f}%)")
    print(f"  👍 Good:      {dist['good']} ({pct['good']:.1f}%)")
    print(f"  ⚠️  Fair:      {dist['fair']} ({pct['fair']:.1f}%)")
    print(f"  ❌ Poor:      {dist['poor']} ({pct['poor']:.1f}%)")
    
    print(f"\nDetailed Results:")
    for val in validation_summary['validated_results']:
        print(f"\n  {val['file']} [{val['quality_level'].upper()}] ({val['overall_score']:.1f}/100)")
        if val['warnings']:
            for warning in val['warnings']:
                print(f"    ⚠️  {warning}")


if __name__ == '__main__':
    # Example usage
    sample_resume = {
        'file': 'sample.pdf',
        'name': 'John Doe',
        'email': 'john.doe@gmail.com',
        'contact_number': '9876543210',
        'gender': 'Male',
        'address': '123 Main Street, New York, NY 10001',
        'skills': ['Python', 'Java', 'JavaScript'],
    }
    
    validator = ResumeValidator()
    result = validator.validate_resume(sample_resume)
    print(json.dumps(result, indent=2))
