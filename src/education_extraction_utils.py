"""
Education Extraction Utilities with Parsel Support
==================================================

This module provides enhanced education extraction for PDF/DOC resumes
with structured parsing using Parsel selectors.
"""

import re
from typing import List, Dict, Optional, Tuple

try:
    from parsel import Selector
    PARSEL_AVAILABLE = True
except ImportError:
    PARSEL_AVAILABLE = False
    Selector = None


class EducationExtractor:
    """Enhanced education extraction with Parsel support."""
    
    # Degree pattern definitions
    DEGREE_PATTERNS = [
        (r'\b(?:b\.?a\.?|bachelor\s+of\s+arts)\b', 'B.A'),
        (r'\b(?:b\.?sc\.?|bachelor\s+of\s+science)\b', 'B.Sc'),
        (r'\b(?:b\.?com\.?|bachelor\s+of\s+commerce)\b', 'B.Com'),
        (r'\b(?:b\.?tech|btech|bachelor\s+of\s+technology)\b', 'B.Tech'),
        (r'\b(?:b\.?e\.?|bachelor\s+of\s+engineering)\b', 'B.E'),
        (r'\b(?:b\.?cs\.?|bachelor\s+of\s+computer\s+science|bcs)\b', 'B.CS'),
        (r'\b(?:bba|bachelor\s+of\s+business\s+administration)\b', 'BBA'),
        (r'\b(?:m\.?a\.?|master\s+of\s+arts)\b', 'M.A'),
        (r'\b(?:m\.?sc\.?|master\s+of\s+science)\b', 'M.Sc'),
        (r'\b(?:m\.?com\.?|master\s+of\s+commerce)\b', 'M.Com'),
        (r'\b(?:m\.?tech|mtech|master\s+of\s+technology)\b', 'M.Tech'),
        (r'\b(?:m\.?e\.?|master\s+of\s+engineering)\b', 'M.E'),
        (r'\b(?:mba|master\s+(?:of\s+)?business\s+administration)\b', 'MBA'),
        (r'\b(?:pgdm|post\s+graduate\s+diploma\s+in\s+management)\b', 'PGDM'),
        (r'\b(?:llb|bachelor\s+of\s+laws)\b', 'LLB'),
        (r'\b(?:llm|master\s+of\s+laws)\b', 'LLM'),
        (r'\bphd\b|\bdoctor\s+of\s+philosophy\b', 'PhD'),
        (r'\b(?:iti|industrial\s+training\s+institute|industrial\s+training\s+diploma)\b', 'ITI'),
        (r'\b(?:diploma|diplom[aá])\b', 'Diploma'),
        (r'\bgrad\w*\b', 'Graduate'),
        (r'\b(?:12th?|intermediate|h\.?s\.?c|hs|high\s+school)\b', '12th'),
        (r'\b(?:10th?|s\.?s\.?c|ssc|secondary)\b', '10th'),
    ]
    
    EDUCATION_MARKERS = [
        'education', 'academic', 'qualifications', 'degrees',
        'educational', 'academia', 'schooling', 'academic background'
    ]
    
    SECTION_END_MARKERS = [
        'experience', 'work experience', 'professional experience',
        'skills', 'projects', 'certifications', 'languages',
        'references', 'declaration', 'technical skills'
    ]
    
    def __init__(self):
        self.parsel_enabled = PARSEL_AVAILABLE
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text from PDF/DOC extraction."""
        if not text:
            return ""
        
        # Handle common OCR/extraction issues
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)  # Remove control chars
        text = re.sub(r'–', '-', text)  # Normalize dashes
        text = re.sub(r'\.{2,}', '.', text)  # Collapse multiple dots
        
        return text.strip()
    
    def extract_education_section_text(self, text: str) -> Tuple[Optional[str], bool]:
        """Extract education section boundaries from text.
        
        Returns:
            Tuple of (education_text, was_found) where was_found indicates
            if an education section header was found.
        """
        if not text:
            return None, False
        
        lines = text.split('\n')
        education_start = -1
        
        # Find education section start
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            if any(marker in line_lower for marker in self.EDUCATION_MARKERS):
                # Verify it's a header (short line, no excluded keywords)
                if (len(line_lower) < 50 and 
                    not any(skip in line_lower for skip in ['requirement', 'preference'])):
                    education_start = i
                    break
        
        if education_start < 0:
            return None, False
        
        # Find section end
        education_end = len(lines)
        for i in range(education_start + 1, len(lines)):
            line_lower = lines[i].strip().lower()
            if any(marker in line_lower for marker in self.SECTION_END_MARKERS):
                if len(line_lower) < 50:
                    education_end = i
                    break
        
        # Extract and return section text
        section_lines = lines[education_start + 1:education_end]
        section_text = '\n'.join(section_lines).strip()
        
        return section_text if section_text else None, True
    
    def extract_with_parsel(self, text: str) -> List[str]:
        """Extract education entries using Parsel selector approach.
        
        This is especially useful for structured text from PDF/DOC.
        """
        if not self.parsel_enabled or not text:
            return []
        
        try:
            # Normalize text to HTML-like structure
            html = self._text_to_html(text)
            selector = Selector(text=html)
            
            # Extract paragraphs
            paragraphs = selector.xpath('//p/text()').getall()
            
            if not paragraphs:
                return []
            
            # Find education section marker
            edu_start = -1
            for i, para in enumerate(paragraphs):
                para_lower = para.lower().strip()
                if any(m in para_lower for m in self.EDUCATION_MARKERS):
                    if len(para_lower) < 50:
                        edu_start = i
                        break
            
            if edu_start < 0:
                return []
            
            # Find section end
            edu_end = len(paragraphs)
            for i in range(edu_start + 1, len(paragraphs)):
                para_lower = paragraphs[i].lower().strip()
                if any(m in para_lower for m in self.SECTION_END_MARKERS):
                    if len(para_lower) < 50:
                        edu_end = i
                        break
            
            # Return extracted education lines
            edu_lines = paragraphs[edu_start + 1:edu_end]
            return [line.strip() for line in edu_lines if line.strip()]
        
        except Exception as e:
            print(f"Parsel extraction error: {e}")
            return []
    
    def _text_to_html(self, text: str) -> str:
        """Convert plain text to HTML-like structure for Parsel parsing."""
        if not text:
            return '<div></div>'
        
        lines = text.splitlines()
        html_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                html_lines.append('<br/>')
            else:
                # Escape HTML and wrap in paragraph
                escaped = (line.replace('&', '&amp;')
                              .replace('<', '&lt;')
                              .replace('>', '&gt;'))
                html_lines.append(f'<p>{escaped}</p>')
        
        return f'<div>{"".join(html_lines)}</div>'
    
    def has_degree(self, text: str) -> bool:
        """Check if text contains any degree pattern."""
        if not text:
            return False
        return any(re.search(pattern, text, re.I) 
                   for pattern, _ in self.DEGREE_PATTERNS)
    
    def extract_degree(self, text: str) -> Optional[str]:
        """Extract degree name from text."""
        if not text:
            return None
        
        for pattern, degree_name in self.DEGREE_PATTERNS:
            if re.search(pattern, text, re.I):
                return degree_name
        
        return None
    
    def extract_text_after_degree(self, text: str) -> Optional[str]:
        """Extract text that comes after the degree pattern in the string.
        
        Useful for finding specialization from text like "B.Tech (Chemical)"
        where the degree pattern match ends before the parenthetical content.
        """
        if not text:
            return None
        
        for pattern, _ in self.DEGREE_PATTERNS:
            match = re.search(pattern, text, re.I)
            if match:
                # Get text after the matched degree pattern
                after_pos = match.end()
                remaining = text[after_pos:].strip()
                if remaining and len(remaining) > 0:
                    return remaining
                break
        
        return None
    
    def extract_year(self, text: str) -> Optional[str]:
        """Extract graduation/passing year from text.
        
        For duration ranges like '2016-2020', returns the END year (2020) as passing year.
        """
        if not text:
            return None
        
        # PRIORITY 1: Look for year range (2016-2020) and extract the END year
        range_match = re.search(r'\b(19[89]\d|20[0-2]\d)\s*[–\-]\s*(19[89]\d|20[0-2]\d)\b', text)
        if range_match:
            end_year = range_match.group(2)  # Get the SECOND year (end year)
            try:
                year_int = int(end_year)
                if 1980 <= year_int <= 2030:
                    return end_year
            except:
                pass
        
        # PRIORITY 2: Look for single 4-digit year in valid range
        # Find ALL matches and return the LAST one (most likely the passing year)
        year_matches = list(re.finditer(r'\b(19[89]\d|20[0-2]\d)\b', text))
        if year_matches:
            # Return the LAST year found (end date, not start date)
            year = year_matches[-1].group(1)
            try:
                year_int = int(year)
                if 1980 <= year_int <= 2030:
                    return year
            except:
                pass
        
        return None
    
    def extract_university(self, text: str) -> Optional[str]:
        """Extract university/institute name from text.
        
        Handles multiple formats:
        - 'from University Name'
        - 'University Name University/College/Institute'
        - Standalone institution names in capital letters
        - Indian institution names without keywords
        """
        if not text:
            return None
        
        # Common patterns for institutions
        patterns = [
            # Pattern 1: "from/at Institute Name" with optional keyword
            r'(?:from|at)\s+([A-Z][A-Za-z\s&\.\,-]+?)(?:\s+(?:University|Institute|College|Academy|Board|School))?(?:\s+(?:–|--|-|with|in|,)|$)',
            # Pattern 2: "Institute Name University/College/Institute/Academy/Board/School"
            r'([A-Z][A-Za-z\s&\-\.]*(?:University|Institute|College|Academy|School|Board))',
            # Pattern 3: Multiple capital words (common for Indian institutions)
            # Look for 2-4 capitalized words in sequence
            r'\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*){1,3})\b',
            # Pattern 4: All caps words (acronyms for institutions like VJTI, NIT, BITS, etc)
            r'\b([A-Z]{2,}(?:\s+[A-Z]{2,})?(?:\s+[A-Z][a-z]+[a-z\s]*)?)\b',
        ]
        
        candidates = []
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                institute = match.group(1).strip().rstrip('–-:,')
                # Filter quality checks
                if (len(institute) > 2 and len(institute) < 150 and
                    not any(x in institute.lower() for x in ['year', 'grade', 'cgpa', 'gpa', 'percent', 'marks',
                                                              'passing', '%', 'board examination', 'email', 'contact'])):
                    # Avoid single common words
                    if len(institute.split()) > 1 or institute.lower() not in ['the', 'and', 'from', 'with', 'in', 'of']:
                        candidates.append(institute)
        
        # Return the first valid candidate (longest and most specific)
        # Prefer those with university/institute keywords
        if candidates:
            # Sort by length (longer = more specific) but prefer those with keywords
            has_keyword = [c for c in candidates if any(kw in c.lower() for kw in 
                          ['university', 'institute', 'college', 'academy', 'board', 'school'])]
            if has_keyword:
                return sorted(has_keyword, key=len, reverse=True)[0]
            return sorted(candidates, key=len, reverse=True)[0]
        
        return None
    
    def extract_grade(self, text: str) -> Optional[str]:
        """Extract CGPA/percentage from text."""
        if not text:
            return None
        
        # Look for percentage with %
        pct_match = re.search(r'(\d+\.?\d*)\s*%', text)
        if pct_match:
            return pct_match.group(0).strip()
        
        # Look for CGPA format (X.XX) preceded by "cgpa" or "gpa"
        cgpa_match = re.search(r'(?:cgpa?|gpa)\s*[:\-]?\s*([0-9]\.[0-9]{1,2})', text, re.I)
        if cgpa_match:
            return cgpa_match.group(1)
        
        # Look for standalone decimal numbers (7.6, 8.5, etc.) that could be CGPA
        # Pattern: decimal between 0-10, not preceded by year pattern
        standalone_cgpa = re.search(r'(?<!\d)(\d\.\d{1,2})(?!\d)', text)
        if standalone_cgpa:
            cgpa_val = standalone_cgpa.group(1)
            cgpa_float = float(cgpa_val)
            # If it looks like a CGPA (between 1 and 10), return it
            if 0.5 <= cgpa_float <= 10.0:
                return cgpa_val
        
        return None
    
    def extract_specialization(self, text: str) -> Optional[str]:
        """Extract specialization/branch from text."""
        if not text:
            return None
        
        # Common locations and non-specialization terms to exclude
        exclusions = [
            'year', 'board', 'from', 'email', 'mardah', 'ghazipur', 'kanpur', 'lucknow',
            'delhi', 'mumbai', 'bangalore', 'hyderabad', 'pune', 'kolkata', 'delhi',
            'college', 'university', 'institute', 'academy', 'school',
            'main', 'branch', 'campus', 'center', 'centre', 'office'
        ]
        
        # Look for specialization in parentheses
        spec_match = re.search(r'\(([^)]+)\)', text)
        if spec_match:
            spec = spec_match.group(1).strip()
            spec_lower = spec.lower()
            if (4 < len(spec) < 80 and 
                not any(x in spec_lower for x in exclusions)):
                return spec
        
        # Look for "in Branch" pattern
        branch_match = re.search(r'(?:in|of)\s+([A-Za-z\s]+)(?:\s*(?:–|-|from|$))', text)
        if branch_match:
            branch = branch_match.group(1).strip()
            branch_lower = branch.lower()
            if 4 < len(branch) < 80 and not any(x in branch_lower for x in exclusions):
                return branch
        
        return None
    
    def parse_education_entry(self, text: str) -> Dict[str, Optional[str]]:
        """Parse a single education entry and extract all available fields.
        
        Handles:
        - Inline format: "S.S.C in 2016 from GSEB with 51%"
        - B.Com format: "B.Com completed in May 2025 from Dr. Babasaheb Ambedkar University"
        - Table merged format: "B.Tech Chemical Engineering Abdul Kalam University 2023 7.6"
        """
        result = {
            'qualification': None,
            'specialization_branch': None,
            'institute_university': None,
            'passing_year': None,
            'grade_cgpa': None,
            'mode_of_study': None,
            'location': None,
            'major_subjects': None,
        }
        
        if not text or len(text.strip()) < 3:
            return result
        
        # Extract in priority order
        result['qualification'] = self.extract_degree(text)
        if not result['qualification']:
            return result  # No degree found, skip
        
        # Extract year
        result['passing_year'] = self.extract_year(text)
        
        # Extract grade/CGPA
        result['grade_cgpa'] = self.extract_grade(text)
        
        # Extract university - try multiple approaches
        result['institute_university'] = self.extract_university(text)
        
        # If no university found, try extracting capitalized phrases
        if not result['institute_university']:
            # Look for capitalized phrases that might be institution names
            capsules = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b', text)
            for capsule in capsules:
                capsule_lower = capsule.lower()
                if (len(capsule) > 3 and 
                    capsule_lower not in ['cgpa', 'grade', 'year', 'completed', 'from', 'with', 'in'] and
                    not any(d in capsule for d in ['2019', '2020', '2021', '2022', '2023', '2024', '2025'])):
                    result['institute_university'] = capsule
                    break
        
        # Extract specialization - look for patterns like "(Computer Science)" or "in Branch"
        spec = self.extract_specialization(text)
        if spec:
            result['specialization_branch'] = spec
        
        # Try extraction from parentheses if not found
        if not result['specialization_branch']:
            paren_match = re.search(r'\(([^)]+)\)', text)
            if paren_match:
                spec = paren_match.group(1).strip()
                if (4 < len(spec) < 80 and 
                    not any(x in spec.lower() for x in ['year', 'board', 'from', 'email', 'aicte', 'approved'])):
                    result['specialization_branch'] = spec
        
        # Extract mode of study
        mode_match = re.search(
            r'\b(?:full[- ]?time|part[- ]?time|distance|online|regular|fulltime|parttime)\b',
            text, re.I
        )
        if mode_match:
            mode_text = mode_match.group(0).lower()
            if 'full' in mode_text or 'regular' in mode_text:
                result['mode_of_study'] = 'Full-time'
            elif 'part' in mode_text:
                result['mode_of_study'] = 'Part-time'
            elif 'distance' in mode_text or 'online' in mode_text:
                result['mode_of_study'] = 'Distance'
        
        return result
    
    def _split_by_degree_patterns(self, text: str) -> List[str]:
        """Split a text string by degree pattern occurrences.
        
        Handles cases where multiple education entries are on one line:
        e.g., "PGDM(...), BBA, 12th, ..." -> ["PGDM(...)", "BBA...", "12th..."]
        
        Returns list of text segments, each starting with a degree pattern.
        """
        if not text:
            return []
        
        import re
        
        # Find all degree pattern matches with their positions
        matches = []
        for pattern, degree_name in self.DEGREE_PATTERNS:
            for match in re.finditer(pattern, text, re.I):
                # Skip false positives (e.g., "secondary" in "Board of Secondary Education")
                matched_text = match.group(0).lower()
                
                # Skip if surrounded by context that suggests it's not a degree
                start = match.start()
                end = match.end()
                
                # Check context before and after
                before = text[max(0, start-30):start].lower()
                after = text[end:min(len(text), end+30)].lower()
                
                # Skip "10th/secondary" if it appears in "board of secondary education"
                if matched_text in ['10th', 'secondary', 'tenth'] and 'board' in before and 'education' in after:
                    continue
                
                matches.append((start, end, degree_name))
        
        if not matches:
            return []
        
        # Sort by position
        matches.sort(key=lambda x: x[0])
        
        # Build segments starting from each match
        segments = []
        for i, (start, end, degree_name) in enumerate(matches):
            # Get text from this match to either the next match or end of string
            if i < len(matches) - 1:
                next_start = matches[i + 1][0]
                segment = text[start:next_start].rstrip(',').strip()
            else:
                segment = text[start:].strip()
            
            if segment:
                segments.append(segment)
        
        return segments
    
    def extract_all_education(self, text: str) -> List[Dict[str, Optional[str]]]:
        """Extract all education entries from text using multiple strategies."""
        results = []
        seen = set()
        
        if not text:
            return results
        
        # Strategy 1: Section-based extraction (best for structured text with headers)
        section_text, found_header = self.extract_education_section_text(text)
        if section_text and found_header:
            lines = [line.strip() for line in section_text.split('\n')]
            
            # Strategy 1A: Try table format parsing first
            table_rows = self._extract_table_rows(lines)
            if table_rows and len(table_rows) >= 1:  # Process all filtered rows
                for row in table_rows:  # Process all rows (headers already filtered out)
                    if not row or len(row) == 0:
                        continue
                    parsed = self._parse_table_row(row)
                    if parsed['qualification']:
                        key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
                        if key not in seen:
                            seen.add(key)
                            results.append(parsed)
            
            # Strategy 1B: If no table rows found, try line-by-line parsing
            if not results:
                entries = self._split_education_entries(section_text)
                for entry_text in entries:
                    parsed = self.parse_education_entry(entry_text)
                    if parsed['qualification']:
                        key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
                        if key not in seen:
                            seen.add(key)
                            results.append(parsed)
        
        # If we got good results from section extraction, return early
        if len(results) >= 1:
            return results
        
        # Strategy 2: Parsel extraction (for unstructured text)
        if self.parsel_enabled and not results:
            try:
                parsel_lines = self.extract_with_parsel(text)
                for line in parsel_lines:
                    # Skip very short lines or obvious metadata
                    if len(line.strip()) < 5:
                        continue
                    parsed = self.parse_education_entry(line)
                    if parsed['qualification']:
                        key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
                        if key not in seen:
                            seen.add(key)
                            results.append(parsed)
            except:
                pass
        
        # Strategy 3: Fallback to line-by-line search if no section found
        if not results:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip very long lines UNLESS they contain degree patterns
                if len(line) > 300 and not self.has_degree(line):
                    continue
                
                # Check if line has education markers
                if self.has_degree(line):
                    # Skip ONLY if the line starts with experience keywords AND has no degree pattern at start
                    # (Don't skip long concatenated lines where education comes first)
                    first_50 = line[:50].lower()
                    starts_with_job_context = any(skip in first_50 for skip in 
                              ['requirement', 'prefer', 'responsible'])
                    
                    if starts_with_job_context:
                        continue
                    
                    # Try to split if multiple degrees in one line
                    segments = self._split_by_degree_patterns(line)
                    if len(segments) > 1:
                        # Multiple degrees found - parse each separately
                        for segment in segments:
                            parsed = self.parse_education_entry(segment)
                            if parsed['qualification']:
                                key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
                                if key not in seen:
                                    seen.add(key)
                                    results.append(parsed)
                    else:
                        # Single degree or couldn't split - parse as-is
                        parsed = self.parse_education_entry(line)
                        if parsed['qualification']:
                            key = (parsed['qualification'], parsed['institute_university'], parsed['passing_year'])
                            if key not in seen:
                                seen.add(key)
                                results.append(parsed)
        
        return results
    
    def _extract_table_rows(self, lines: List[str]) -> List[List[str]]:
        """Extract table rows by identifying degree patterns as row starts.
        
        Since PDF tables may not have clear row separators, we use education keywords
        (degree names) to identify where each row begins.
        
        Returns a list of rows, where each row is a list of cells/fields.
        """
        if not lines:
            return []
        
        rows = []
        current_row = []
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                # Blank line - skip
                continue
            
            # Check if this line starts with a degree pattern
            is_degree_start = any(re.search(pattern, stripped, re.I) 
                                 for pattern, _ in self.DEGREE_PATTERNS)
            
            if is_degree_start and current_row:
                # New education entry starts - save the current row
                rows.append(current_row)
                current_row = [stripped]
            else:
                # Continue building current row
                current_row.append(stripped)
        
        if current_row:
            rows.append(current_row)
        
        # Filter out header row (contains keywords like "Course", "Year", "Percent", "Name")
        # But don't filter out rows that start with valid degrees
        filtered_rows = []
        
        for row in rows:
            if not row:
                continue
            
            # Check if first cell is a valid degree
            first_cell = row[0].strip().lower()
            has_valid_degree = any(re.search(pattern, first_cell, re.I) 
                                  for pattern, _ in self.DEGREE_PATTERNS)
            
            if has_valid_degree:
                # If first cell is a valid degree, it's definitely an education entry
                filtered_rows.append(row)
            else:
                # Check if this looks like a header row by checking for header patterns
                combined = ' '.join(row).lower()
                # Only consider it a header if multiple header terms appear together
                # and the first cell doesn't look like data
                is_clearly_header = (
                    re.search(r'\bcourse.*certificate\b|\bcertificate.*course\b', combined) is not None or
                    (combined.count('year') > 0 and combined.count('passing') > 0) or
                    (first_cell.count('/') == len(row) - 1)  # Multiple slashes suggest header row
                )
                
                if not is_clearly_header:
                    filtered_rows.append(row)
        
        return filtered_rows
    
    def _parse_table_row(self, row_cells: List[str]) -> Dict[str, Optional[str]]:
        """Parse a single table row with cells as list of strings.
        
        Each cell is already a concatenated string from multi-line fields.
        Expected pattern typically:
        - Cell 0: Degree (B.Tech, MBA, etc.)
        - Cell 1: University/Board/Institute (can contain location)
        - Cell 2+: Year, CGPA/Grade, or additional details
        
        But can vary, so we intelligently extract from all cells combined.
        """
        result = {
            'qualification': None,
            'specialization_branch': None,
            'institute_university': None,
            'passing_year': None,
            'grade_cgpa': None,
            'mode_of_study': None,
            'location': None,
            'major_subjects': None,
        }
        
        if not row_cells or len(row_cells) == 0:
            return result
        
        # Use cells strategically
        combined = ' '.join(row_cells)
        
        # Cell 0 usually has degree  
        if row_cells and row_cells[0]:
            qual = self.extract_degree(row_cells[0])
            if qual:
                result['qualification'] = qual
        
        # If no degree found in first cell, search combined
        if not result['qualification']:
            result['qualification'] = self.extract_degree(combined)
        
        if not result['qualification']:
            return result  # No degree, skip this row
        
        # Extract text after degree for specialization (e.g., "(Chemical)" from "B.Tech (Chemical)")
        text_after_degree = self.extract_text_after_degree(row_cells[0])
        if text_after_degree and len(text_after_degree) < 100:
            # Extract specialization from the text after degree
            spec = self.extract_specialization(text_after_degree)
            if spec:
                result['specialization_branch'] = spec
        
        # Cell 1 usually has university
        if len(row_cells) > 1 and row_cells[1]:
            inst = self.extract_university(row_cells[1])
            if inst:
                result['institute_university'] = inst
        
        # Search year and grade across all cells
        result['passing_year'] = self.extract_year(combined)
        result['grade_cgpa'] = self.extract_grade(combined)
        
        # If university still not found, search in combined
        if not result['institute_university']:
            result['institute_university'] = self.extract_university(combined)
        
        # Extract specialization if not found yet
        if not result['specialization_branch']:
            spec = self.extract_specialization(combined)
            if spec:
                result['specialization_branch'] = spec
        
        return result
    
    def _split_education_entries(self, text: str) -> List[str]:
        """Split education section text into individual entries.
        
        Each line with a degree pattern starts a NEW entry.
        Metadata (year, grade, university) on the NEXT line is grouped with that degree.
        This prevents Diploma and ITI from being merged.
        
        Example:
        Input:  "Diploma in 2018\nITI in 2016 from XYZ"
        Output: ["Diploma in 2018", "ITI in 2016 from XYZ"]
        """
        if not text:
            return []
        
        entries = []
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line_stripped = lines[i].strip()
            
            if not line_stripped:
                # Skip blank lines
                i += 1
                continue
            
            has_degree = self.has_degree(line_stripped)
            
            if has_degree:
                # Start a new education entry with this degree line
                entry_lines = [line_stripped]
                i += 1
                
                # Collect metadata from the next line(s) ONLY if they don't have degrees
                # and are short enough to be metadata
                while i < len(lines):
                    next_line = lines[i].strip()
                    
                    if not next_line:
                        # Skip blank lines but continue looking
                        i += 1
                        continue
                    
                    # If next line has a degree, STOP and let it start its own entry
                    if self.has_degree(next_line):
                        break
                    
                    # If it's metadata (short line with year/grade/university), add it
                    # But don't add very long lines that might be multi-degree entries
                    if len(next_line) < 200:
                        entry_lines.append(next_line)
                        i += 1
                    else:
                        # Long line might contain multiple degrees, stop
                        break
                
                # Save this entry
                entries.append('\n'.join(entry_lines))
            else:
                # Line without degree - skip it (orphan metadata)
                i += 1
        
        return [e.strip() for e in entries if e.strip()]


def extract_education_pdf_doc(text: str) -> List[Dict[str, Optional[str]]]:
    """
    Main function for extracting education from PDF/DOC text.
    
    Args:
        text: Extracted text from PDF/DOC file
    
    Returns:
        List of education records with degree, university, year, etc.
    """
    extractor = EducationExtractor()
    return extractor.extract_all_education(text)
