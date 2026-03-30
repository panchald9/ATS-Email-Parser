"""
SKILL ANALYSIS PIPELINE v2.0
=============================
Integrated with Main_Resume.py for enhanced skill extraction and analysis.

5-Stage Pipeline:
1. INPUT:    Resume file + optional job role
2. PARSE:    Extract text, detect sections
3. EXTRACT:  Skills using hybrid approach (section-wise + full-document)
4. CLASSIFY: Organize by category (Programming, Tools, Domain, Soft Skills, etc.)
5. ANALYZE:  Gap analysis, scoring, recommendations (if job role provided)
"""

import re
import json
from typing import List, Dict, Tuple, Optional
from collections import Counter

# ═══════════════════════════════════════════════════════════════
#  SKILL CATEGORIES & TAXONOMY
# ═══════════════════════════════════════════════════════════════

SKILL_TAXONOMY = {
    'Programming Languages': {
        'keywords': ['java', 'python', 'javascript', 'c++', 'c#', 'ruby', 'php', 'go', 'rust', 'swift', 
                    'kotlin', 'scala', 'perl', 'r language', 'matlab', 'typescript', 'coffeescript',
                    'groovy', 'elixir', 'haskell', 'clojure', 'julia', 'lua', 'bash', 'shell'],
        'label': '💻 Languages'
    },
    'Web Frameworks': {
        'keywords': ['react', 'vue', 'angular', 'django', 'flask', 'spring', 'express', 'rails',
                    'laravel', 'symfony', 'asp.net', 'next.js', 'nuxt', 'ember', 'backbone',
                    'meteor', 'fastapi', 'tornado', 'pyramid', 'saas'],
        'label': '🌐 Web Frameworks'
    },
    'Backend/APIs': {
        'keywords': ['rest api', 'graphql', 'soap', 'microservices', 'nodejs', 'node.js', 'grpc',
                    'api design', 'webhook', 'oauth', 'jwt', 'api gateway'],
        'label': '🔧 Backend/APIs'
    },
    'Databases': {
        'keywords': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'cassandra', 'dynamodb',
                    'oracle', 'elasticsearch', 'firebase', 'firestore', 'couchdb', 'neo4j',
                    'memcached', 'snowflake', 'bigquery', 'datastore'],
        'label': '🗄️ Databases'
    },
    'Cloud Platforms': {
        'keywords': ['aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digital ocean', 'linode',
                    'rackspace', 'cloudflare', 'vercel', 'netlify', 'alibaba cloud', 'ibm cloud'],
        'label': '☁️ Cloud'
    },
    'DevOps/Infrastructure': {
        'keywords': ['docker', 'kubernetes', 'terraform', 'ansible', 'jenkins', 'gitlab ci',
                    'github actions', 'circleci', 'travis ci', 'aws cloudformation', 'puppet',
                    'chef', 'prometheus', 'grafana', 'elk stack', 'datadog', 'newrelic'],
        'label': '⚙️ DevOps'
    },
    'Data/Analytics': {
        'keywords': ['hadoop', 'spark', 'kafka', 'airflow', 'etl', 'data warehouse', 'data lakes',
                    'big data', 'hadoop', 'hive', 'pig', 'hbase', 'tableau', 'power bi', 'looker',
                    'dbt', 'pandas', 'numpy', 'scipy'],
        'label': '📊 Data/Analytics'
    },
    'Testing/QA': {
        'keywords': ['selenium', 'junit', 'testng', 'pytest', 'mocha', 'chai', 'rspec', 'cypress',
                    'playwright', 'jmeter', 'loadrunner', 'test automation', 'unit testing',
                    'integration testing', 'api testing', 'tdd', 'bdd', 'postman'],
        'label': '🧪 Testing'
    },
    'Mobile': {
        'keywords': ['ios', 'android', 'swift', 'kotlin', 'react native', 'flutter', 'xamarin',
                    'cordova', 'ionic', 'objective-c'],
        'label': '📱 Mobile'
    },
    'AI/ML': {
        'keywords': ['machine learning', 'deep learning', 'tensorflow', 'keras', 'pytorch', 'scikit',
                    'nlp', 'computer vision', 'neural networks', 'gpt', 'bert', 'hugging face'],
        'label': '🤖 AI/ML'
    },
    'Tools/Platforms': {
        'keywords': ['git', 'git hub', 'gitlab', 'bitbucket', 'jira', 'confluence', 'slack',
                    'miro', 'figma', 'sketch', 'xd', 'vs code', 'intellij', 'eclipse', 'vim'],
        'label': '🛠️ Tools'
    },
    'Soft Skills': {
        'keywords': ['communication', 'teamwork', 'leadership', 'problem solving', 'critical thinking',
                    'project management', 'agile', 'scrum', 'analytical', 'presentation', 'negotiation',
                    'conflict resolution', 'time management', 'adaptability'],
        'label': '💬 Soft Skills'
    },
    'Domain Knowledge': {
        'keywords': ['sdlc', 'rest', 'soap', 'microservices', 'distributed systems', 'system design',
                    'scalability', 'performance optimization', 'security', 'authentication', 'caching',
                    'load balancing', 'cdn', 'database design'],
        'label': '📚 Domain'
    },
    'Certifications': {
        'keywords': ['aws certified', 'kubernetes', 'scrum master', 'google cloud', 'azure certified',
                    'certified', 'pmp', 'cissp', 'ccna', 'ocpjp'],
        'label': '🏆 Certifications'
    }
}

# ═══════════════════════════════════════════════════════════════
#  JOB ROLE REQUIREMENTS
# ═══════════════════════════════════════════════════════════════

JOB_ROLES = {
    'Software Developer': {
        'essential': ['java', 'python', 'c#', 'javascript', 'sql', 'git', 'api'],
        'nice_to_have': ['docker', 'kubernetes', 'aws', 'azure', 'jenkins', 'ci/cd', 'microservices'],
        'soft_skills': ['problem solving', 'communication', 'teamwork', 'agile']
    },
    'QA Engineer': {
        'essential': ['selenium', 'test automation', 'jira', 'sql', 'api testing', 'bug tracking'],
        'nice_to_have': ['junit', 'testng', 'loadrunner', 'python', 'javascript', 'performance testing'],
        'soft_skills': ['attention to detail', 'communication', 'analytical thinking', 'teamwork']
    },
    'QA Manager': {
        'essential': ['qms', 'iso 9001', 'process validation', 'change management', 'risk assessment'],
        'nice_to_have': ['six sigma', 'lean', 'test automation', 'defect management', 'test case design'],
        'soft_skills': ['team leadership', 'communication', 'strategic thinking', 'decision making']
    },
    'Mechanical Engineer': {
        'essential': ['cad', 'autocad', 'fmea', 'root cause analysis', 'thermodynamics', 'mechanics'],
        'nice_to_have': ['ansys', 'matlab', 'simulation', 'finite element', 'pumps', 'compressors'],
        'soft_skills': ['problem solving', 'analytical thinking', 'teamwork', 'project management']
    },
    'Maintenance Engineer': {
        'essential': ['preventive maintenance', 'cmms', 'equipment troubleshooting', 'ndt', 'electrical', 'mechanical'],
        'nice_to_have': ['cost control', 'spare parts management', 'reliability engineering', 'safety management'],
        'soft_skills': ['problem solving', 'team leadership', 'decision making', 'communication']
    },
    'Production Executive': {
        'essential': ['production planning', 'scheduling', 'cost control', 'inventory management', 'safety protocols'],
        'nice_to_have': ['lean manufacturing', 'six sigma', 'erp', 'quality control', 'team leadership'],
        'soft_skills': ['leadership', 'communication', 'planning', 'decision making']
    }
}

# ═══════════════════════════════════════════════════════════════
#  CLASSIFICATION & ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def classify_skill(skill: str) -> Tuple[str, str]:
    """
    Classify a skill into a category.
    Returns: (category_name, category_label)
    """
    skill_lower = skill.lower()
    
    for category, info in SKILL_TAXONOMY.items():
        for keyword in info['keywords']:
            if keyword in skill_lower or skill_lower in keyword:
                return (category, info['label'])
    
    # Default classification
    return ('Other', '📌 Other')


def categorize_skills(skills: List[str]) -> Dict[str, List[str]]:
    """
    Organize skills into categorical buckets.
    Returns: {category_name: [skills]}
    """
    categorized = {}
    
    for skill in skills:
        category, _ = classify_skill(skill)
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(skill)
    
    # Sort by category importance
    priority_order = [
        'Programming Languages', 'Web Frameworks', 'Backend/APIs', 'Databases',
        'Cloud Platforms', 'DevOps/Infrastructure', 'Data/Analytics', 'Testing/QA',
        'Mobile', 'AI/ML', 'Tools/Platforms', 'Soft Skills', 'Domain Knowledge',
        'Certifications', 'Other'
    ]
    
    sorted_categorized = {}
    for cat in priority_order:
        if cat in categorized:
            sorted_categorized[cat] = categorized[cat]
    
    return sorted_categorized


def skill_matches(skill: str, requirement: str) -> bool:
    """Check if extracted skill matches a job requirement."""
    skill_norm = skill.lower().strip()
    req_norm = requirement.lower().strip()
    
    # Remove generic words
    skill_norm = re.sub(r'\b(programming|language|software|tool|experience|knowledge|proficiency)\b', '', skill_norm)
    req_norm = re.sub(r'\b(programming|language|software|tool|experience|knowledge|proficiency)\b', '', req_norm)
    
    skill_norm = re.sub(r'\s+', ' ', skill_norm).strip()
    req_norm = re.sub(r'\s+', ' ', req_norm).strip()
    
    # Exact or substring match
    if req_norm in skill_norm or skill_norm in req_norm:
        return True
    
    # Word overlap
    skill_words = set(skill_norm.split())
    req_words = set(req_norm.split())
    if len(skill_words & req_words) >= 1:
        return True
    
    return False


def analyze_skill_gap(extracted_skills: List[str], job_role: str) -> Optional[Dict]:
    """
    Analyze skill gaps for a specific job role.
    Returns detailed gap analysis or None if role not found.
    """
    if job_role not in JOB_ROLES:
        return None
    
    role_req = JOB_ROLES[job_role]
    
    # Check essential skills
    essential_found = []
    essential_missing = []
    for req in role_req['essential']:
        found = any(skill_matches(e, req) for e in extracted_skills)
        if found:
            essential_found.append(req)
        else:
            essential_missing.append(req)
    
    # Check nice-to-have skills
    nice_found = []
    nice_missing = []
    for req in role_req['nice_to_have']:
        found = any(skill_matches(e, req) for e in extracted_skills)
        if found:
            nice_found.append(req)
        else:
            nice_missing.append(req)
    
    # Check soft skills
    soft_found = []
    soft_missing = []
    for req in role_req['soft_skills']:
        found = any(skill_matches(e, req) for e in extracted_skills)
        if found:
            soft_found.append(req)
        else:
            soft_missing.append(req)
    
    # Calculate match score
    total_essential = len(role_req['essential'])
    match_score = (len(essential_found) / total_essential * 100) if total_essential > 0 else 0
    
    return {
        'job_role': job_role,
        'match_score': round(match_score, 1),
        'match_level': '🟢 EXCELLENT' if match_score >= 80 else '🟡 MODERATE' if match_score >= 60 else '🔴 WEAK',
        'essential_found': essential_found,
        'essential_missing': essential_missing,
        'nice_found': nice_found,
        'nice_missing': nice_missing,
        'soft_found': soft_found,
        'soft_missing': soft_missing,
        'total_skills_extracted': len(extracted_skills)
    }


def get_skill_insights(categorized_skills: Dict[str, List[str]]) -> Dict:
    """
    Generate insights about the skill profile.
    """
    total_skills = sum(len(v) for v in categorized_skills.values())
    
    insights = {
        'total_unique_skills': total_skills,
        'categories_covered': len(categorized_skills),
        'strongest_areas': sorted(
            [(cat, len(skills)) for cat, skills in categorized_skills.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3],
        'has_programming': 'Programming Languages' in categorized_skills,
        'has_cloud': 'Cloud Platforms' in categorized_skills,
        'has_devops': 'DevOps/Infrastructure' in categorized_skills,
        'has_soft_skills': 'Soft Skills' in categorized_skills,
        'skill_diversity': len(categorized_skills) / len(SKILL_TAXONOMY)
    }
    
    return insights


def generate_recommendations(extracted_skills: List[str], job_role: Optional[str] = None) -> List[str]:
    """
    Generate actionable recommendations for skill improvement.
    """
    recommendations = []
    
    if not extracted_skills:
        return [
            "❗ No skills detected. Add a dedicated 'Skills' section to your resume.",
            "📝 List technical tools, frameworks, and methodologies you've used.",
        ]
    
    categorized = categorize_skills(extracted_skills)
    
    # Generic recommendations
    if 'Programming Languages' not in categorized:
        recommendations.append("🚀 Add programming language skills (Python, Java, JavaScript, etc.)")
    
    if 'Cloud Platforms' not in categorized:
        recommendations.append("☁️ Consider learning cloud platforms (AWS, Azure, GCP)")
    
    if 'Soft Skills' not in categorized:
        recommendations.append("💬 Highlight soft skills (communication, teamwork, leadership)")
    
    # Job-role-specific recommendations
    if job_role and job_role in JOB_ROLES:
        gap = analyze_skill_gap(extracted_skills, job_role)
        if gap:
            if gap['essential_missing']:
                recommendations.append(
                    f"⚡ CRITICAL: Add these essential skills for {job_role}: {', '.join(gap['essential_missing'][:3])}"
                )
            
            if gap['match_score'] < 60 and gap['nice_missing']:
                recommendations.append(
                    f"📚 Build depth: Add advanced skills like {', '.join(gap['nice_missing'][:2])}"
                )
    
    return recommendations if recommendations else [
        "✅ Good foundation! Consider specializing in one technology stack.",
        "📖 Keep learning and updating skills based on job market trends."
    ]


# ═══════════════════════════════════════════════════════════════
#  REPORT GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_skill_analysis_report(
    name: str,
    extracted_skills: List[str],
    job_role: Optional[str] = None,
    filename: Optional[str] = None
) -> Dict:
    """
    Generate a comprehensive skill analysis report.
    """
    categorized = categorize_skills(extracted_skills)
    insights = get_skill_insights(categorized)
    gap_analysis = analyze_skill_gap(extracted_skills, job_role) if job_role else None
    recommendations = generate_recommendations(extracted_skills, job_role)
    
    report = {
        'candidate_name': name,
        'filename': filename,
        'total_skills_extracted': insights['total_unique_skills'],
        'skill_categories': {
            cat: skills for cat, skills in categorized.items()
        },
        'categorized_stats': {
            category: len(skills)
            for category, skills in categorized.items()
        },
        'insights': insights,
        'gap_analysis': gap_analysis,
        'recommendations': recommendations,
        'report_version': '2.0'
    }
    
    return report


def format_report_for_display(report: Dict) -> str:
    """
    Format report as human-readable string.
    """
    lines = []
    lines.append(f"\n{'='*80}")
    lines.append(f"SKILL ANALYSIS REPORT v2.0")
    lines.append(f"{'='*80}\n")
    
    lines.append(f"👤 Candidate: {report['candidate_name']}")
    lines.append(f"📄 File: {report['filename']}")
    lines.append(f"📊 Total Skills: {report['total_skills_extracted']}\n")
    
    # Skills by category
    lines.append(f"{'─'*80}")
    lines.append("SKILLS BY CATEGORY")
    lines.append(f"{'─'*80}\n")
    
    for category, skills in report['skill_categories'].items():
        count = len(skills)
        skill_list = ', '.join(sorted(skills)[:5])
        if len(skills) > 5:
            skill_list += f", +{len(skills)-5} more"
        lines.append(f"  {category:<30} ({count:>2}): {skill_list}")
    
    # Gap analysis
    if report['gap_analysis']:
        gap = report['gap_analysis']
        lines.append(f"\n{'─'*80}")
        lines.append(f"SKILL GAP ANALYSIS: {gap['job_role']}")
        lines.append(f"{'─'*80}\n")
        
        lines.append(f"  Match Score: {gap['match_level']} {gap['match_score']}%\n")
        
        if gap['essential_found']:
            lines.append(f"  ✓ ESSENTIAL FOUND ({len(gap['essential_found'])}):")
            for skill in gap['essential_found']:
                lines.append(f"    • {skill}")
        
        if gap['essential_missing']:
            lines.append(f"\n  ✗ ESSENTIAL MISSING ({len(gap['essential_missing'])}):")
            for skill in gap['essential_missing']:
                lines.append(f"    • {skill}")
    
    # Recommendations
    if report['recommendations']:
        lines.append(f"\n{'─'*80}")
        lines.append("RECOMMENDATIONS")
        lines.append(f"{'─'*80}\n")
        for i, rec in enumerate(report['recommendations'], 1):
            lines.append(f"  {i}. {rec}")
    
    lines.append(f"\n{'='*80}\n")
    
    return '\n'.join(lines)
