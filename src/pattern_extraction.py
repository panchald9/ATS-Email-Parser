"""
Pattern-based extraction functions for severely mangled PDF text.
These work by looking for date patterns, company keywords, role keywords, etc.
instead of relying on section structure.
"""
import re
from datetime import datetime

def extract_jobs_from_patterns(text):
    """
    Extract job entries directly by looking for date patterns, company names, and roles.
    Works even when text is severely jumbled with no clear section structure.
    
    Looks for patterns like:
    - "Jan 2023 - Present" or "2023 - 2025"
    - Company keywords: "Ltd", "Inc", "Services", etc.
    - Role keywords: "Developer", "Manager", "Engineer", etc.
    """
    if not text or len(text) < 50:
        return []
    
    jobs = []
    
    # Strong date patterns: "Month YYYY - Month YYYY" or "YYYY - YYYY"
    date_patterns = [
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}\s*[-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}\s*[-–]\s*(?:Present|Current)',
        r'20\d{2}\s*[-–]\s*20\d{2}',
        r'20\d{2}\s*[-–]\s*(?:Present|Current)',
    ]
    
    # Company keywords
    company_keywords = r'(?:Ltd|Limited|Inc|Company|Services|Pvt|Solutions|Tech|Group|Corporation|Corp|LLC)'
    
    # Role keywords
    role_keywords = r'(?:Developer|Engineer|Manager|Director|Lead|Architect|Consultant|Analyst|Designer|Trainer|Lecturer|Mentor|Coordinator|Officer|Specialist|Associate|Executive|Editor|Writer|Consultant)'
    
    # Find all date ranges in text
    all_jobs_text = []
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            all_jobs_text.append({
                'date_range': match.group(0),
                'date_pos': match.start(),
                'type': 'date'
            })
    
    if not all_jobs_text:
        return []
    
    # Sort by position
    all_jobs_text.sort(key=lambda x: x['date_pos'])
    
    # For each date range, extract surrounding context
    for item in all_jobs_text:
        start_pos = item['date_pos']
        end_pos = item['date_pos'] + len(item['date_range'])
        
        # Get text before and after (limited window)
        before_text = text[max(0, start_pos - 200):start_pos]
        after_text = text[end_pos:min(len(text), end_pos + 300)]
        
        context = before_text + ' ' + item['date_range'] + ' ' + after_text
        
        # Try to extract company from context
        company = None
        for match in re.finditer(r'([A-Z][A-Za-z\s&.,]*?)(?:' + company_keywords + r')(?:\s|$)', context, re.IGNORECASE):
            candidate = match.group(1).strip()
            if len(candidate) > 3 and len(candidate) < 80:
                company = candidate + ' ' + match.group(0).split()[-1]  # Include keyword
                break
        
        # Try to extract role from context
        role = None
        for match in re.finditer(role_keywords, context, re.IGNORECASE):
            # Get word boundaries
            start = max(0, match.start() - 50)
            end = min(len(context), match.end() + 50)
            phrase = context[start:end]
            
            # Extract phrase around role keyword
            words_before = phrase[:match.start() - start].split()
            role_word = match.group(0)
            words_after = phrase[match.end() - start:].split()[:2]
            
            potential_role = ' '.join(words_before[-3:] + [role_word] + words_after).strip()
            if len(potential_role) < 80:
                role = potential_role
                break
        
        if company or role:
            jobs.append({
                'date_range': item['date_range'],
                'company': company,
                'role': role,
                'context': context[:500]
            })
    
    return jobs


def extract_education_from_patterns(text):
    """
    Extract education entries by looking for degree patterns, university names, and years.
    Works even in jumbled text.
    """
    if not text or len(text) < 30:
        return []
    
    education_entries = []
    
    # Degree patterns
    degree_patterns = [
        r'B\.?(?:Tech|Sc|A|Com|E|.A|.Sc)',
        r'M\.?(?:Tech|Sc|A|Com|E|.A|.Sc)',
        r'(?:B\.?Sc|M\.?Sc|B\.?A|M\.?A|B\.?Com|MBA|PGDM|PhD|Diploma|IIT)',
        r'10th|12th|10 TH|12 TH|Tenth|Twelfth',
    ]
    
    # University keywords
    university_keywords = r'(?:University|Institute|School|College|Academy|Centre)'
    
    # Find degree patterns
    candidates = []
    for pattern in degree_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            candidates.append({
                'degree': match.group(0),
                'pos': match.start(),
                'type': 'degree'
            })
    
    # Find year patterns (2020-2024, 2019, etc.)
    for match in re.finditer(r'(?:20\d{2}|19\d{2})', text):
        candidates.append({
            'year': match.group(0),
            'pos': match.start(),
            'type': 'year'
        })
    
    # Sort by position
    candidates.sort(key=lambda x: x['pos'])
    
    # Group nearby candidates as one education entry
    if not candidates:
        return []
    
    current_group = [candidates[0]]
    for candidate in candidates[1:]:
        # If within 200 chars, group together
        if candidate['pos'] - current_group[-1]['pos'] < 200:
            current_group.append(candidate)
        else:
            # Process current group
            if len([c for c in current_group if c['type'] == 'degree']) > 0:
                entry = process_education_group(current_group, text)
                if entry:
                    education_entries.append(entry)
            current_group = [candidate]
    
    # Process last group
    if current_group and len([c for c in current_group if c['type'] == 'degree']) > 0:
        entry = process_education_group(current_group, text)
        if entry:
            education_entries.append(entry)
    
    return education_entries


def process_education_group(candidates, text):
    """Process a group of education-related candidates."""
    degree = None
    university = None
    year = None
    
    for candidate in candidates:
        if candidate['type'] == 'degree' and not degree:
            degree = candidate['degree']
        elif candidate['type'] == 'year' and not year:
            year = candidate['year']
    
    # Try to find university
    if candidates:
        pos = candidates[0]['pos']
        context = text[max(0, pos - 150):min(len(text), pos + 200)]
        for match in re.finditer(r'([A-Z][A-Za-z\s]*?)(?:University|Institute|College|School)', context, re.IGNORECASE):
            university = match.group(1).strip() + ' ' + match.group(0).split()[-1]
            break
    
    if degree:
        return {
            'qualification': degree,
            'institute_university': university,
            'passing_year': year,
        }
    
    return None


if __name__ == '__main__':
    # Test
    test_text = """
    2023 - 2025 PALM TREE CLUB  Lead Faculty Mentor Develop and deliver
    2022 - 2023 .Net Developer Industrial Analytical Services
    B.Tech 2022 - 2026 Information Technology Silver Oak University
    """
    
    print("Jobs found:")
    for job in extract_jobs_from_patterns(test_text):
        print(job)
    
    print("\nEducation found:")
    for edu in extract_education_from_patterns(test_text):
        print(edu)
