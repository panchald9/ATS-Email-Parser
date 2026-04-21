"""
Streamlit UI for Resume Parser
Provides interactive interface for uploading and parsing resumes
No external API required - runs directly using Main_Resume parser
"""

import streamlit as st
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import tempfile

# Import the resume parser
try:
    import Main_Resume as resume_parser
    PARSER_AVAILABLE = True
except Exception as e:
    PARSER_AVAILABLE = False
    st.error(f"❌ Failed to load resume parser: {e}")


# ─────────────────────────────────────────────────────────────────
# Caching for Performance
# ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_parser():
    """Cache the parser to avoid reloading"""
    return resume_parser

# ─────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Parser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────────────────────────
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f4f8;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-card {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        color: #155724;
    }
    .error-card {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        color: #721c24;
    }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# Initialize Session State
# ─────────────────────────────────────────────────────────────────
if "parse_result" not in st.session_state:
    st.session_state.parse_result = None
if "parsing_failed" not in st.session_state:
    st.session_state.parsing_failed = False
if "show_results" not in st.session_state:
    st.session_state.show_results = False


# ─────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────
st.title("📄 Resume Parser")
st.markdown("Extract structured information from CVs and resumes using AI")

if not PARSER_AVAILABLE:
    st.error("❌ Resume parser not available. Please check Main_Resume.py is in the same directory.")
    st.stop()

# ─────────────────────────────────────────────────────────────────
# Main Content
# ─────────────────────────────────────────────────────────────────
tabs = st.tabs(["📤 Upload & Parse", "📊 View Results", "ℹ️ API Info", "⚙️ Settings"])

# ─────────────────────────────────────────────────────────────────
# TAB 1: Upload & Parse
# ─────────────────────────────────────────────────────────────────
with tabs[0]:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Resume")
        uploaded_file = st.file_uploader(
            "Choose a resume file",
            type=["pdf", "docx", "doc"],
            help="Supported formats: PDF, DOCX, DOC"
        )
    
    # Parse button
    if uploaded_file is not None:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Parse Resume", use_container_width=True):
                with st.spinner("⏳ Parsing resume..."):
                    try:
                        # Create temporary file
                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=Path(uploaded_file.name).suffix
                        ) as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            tmp_path = tmp_file.name
                        
                        # Parse resume directly using Main_Resume
                        process_folder = os.path.dirname(tmp_path)
                        temp_fname = os.path.basename(tmp_path)
                        
                        # Call parser
                        result = resume_parser._extract_resume_record(
                            fname=temp_fname,
                            process_folder=process_folder,
                            skill_source='auto',
                            skills_list=[],
                            compiled_skill_matchers=None,
                            fast_response=False,
                        )
                        
                        if result and not result.get("error"):
                            st.session_state.parse_result = result
                            st.session_state.parsing_failed = False
                            st.session_state.show_results = True  # Flag to display results
                            st.success("✅ Resume parsed successfully!")
                        else:
                            error_msg = result.get("error", "Unknown parsing error") if result else "Failed to parse resume"
                            st.error(f"❌ {error_msg}")
                            st.session_state.parsing_failed = True
                        
                        # Cleanup
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.session_state.parsing_failed = True
        
        with col2:
            st.write("")  # Spacer
        
        with col3:
            if st.session_state.parse_result:
                if st.button("📥 Download JSON", use_container_width=True):
                    json_str = json.dumps(
                        st.session_state.parse_result,
                        indent=2
                    )
                    st.download_button(
                        label="Download",
                        data=json_str,
                        file_name="resume_parsed.json",
                        mime="application/json"
                    )
    else:
        st.info("👆 Please upload a resume file to get started")
    
    # ─────────────────────────────────────────────────────────────────
    # AUTO-DISPLAY FULL RESULTS AFTER PARSING
    # ─────────────────────────────────────────────────────────────────
    if st.session_state.show_results and st.session_state.parse_result:
        st.divider()
        st.subheader("📊 Parsing Results")
        
        result = st.session_state.parse_result
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Name", result.get("name", "N/A"))
        with col2:
            st.metric("Skills Count", len(result.get("skills", [])))
        with col3:
            st.metric("Education Entries", len(result.get("education", [])))
        with col4:
            st.metric("Experience Entries", len(result.get("professional_experience", [])))
        
        st.divider()
        
        # Personal Data
        with st.expander("👤 Personal Information", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Name:**", result.get("name", "N/A"))
                st.write("**Email:**", result.get("email", "N/A"))
                st.write("**DOB:**", result.get("dob", "N/A"))
            with col2:
                st.write("**Gender:**", result.get("gender", "N/A"))
                st.write("**Address:**", result.get("address", "N/A"))
                st.write("**Phone:**", result.get("contact_number", "N/A"))
        
        # Education
        education = result.get("education", [])
        with st.expander("🎓 Education", expanded=True):
            if education:
                for idx, edu in enumerate(education, 1):
                    qual = edu.get('qualification', 'Unknown')
                    st.write(f"### Education #{idx}: {qual}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Qualification:**", edu.get("qualification", "N/A"))
                        st.write("**Institution:**", edu.get("institute_university", "N/A"))
                        st.write("**Branch/Specialization:**", edu.get("specialization_branch", "N/A"))
                    with col2:
                        st.write("**Year:**", edu.get("passing_year", "N/A"))
                        st.write("**CGPA/Grade:**", edu.get("grade_cgpa", "N/A"))
                        st.write("**Mode of Study:**", edu.get("mode_of_study", "N/A"))
                    st.write("**Location:**", edu.get("location", "N/A"))
                    st.divider()
            else:
                st.info("No education data extracted")
        
        # Experience
        experience = result.get("professional_experience", [])
        with st.expander("💼 Professional Experience", expanded=True):
            if experience:
                for idx, exp in enumerate(experience, 1):
                    role = exp.get('role', 'Unknown')
                    st.write(f"### Job #{idx}: {role}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Role/Title:**", exp.get("role", "N/A"))
                        st.write("**Company:**", exp.get("company_name", "N/A"))
                        st.write("**Duration:**", exp.get("duration_text", "N/A"))
                    with col2:
                        st.write("**Location:**", exp.get("location", "N/A"))
                        st.write("**Employment Type:**", exp.get("employment_type", "N/A"))
                        st.write("**Currently Working:**", exp.get("currently_working", "N/A"))
                    
                    # Technologies
                    techs = exp.get("technologies", [])
                    if techs:
                        st.write("**Technologies:**", ", ".join(techs))
                    
                    # Responsibilities
                    resp = exp.get("responsibilities", [])
                    if resp:
                        st.write("**Responsibilities:**")
                        for r in resp:
                            st.write(f"• {r}")
                    st.divider()
            else:
                st.info("No experience data extracted")
        
        # Skills
        skills = result.get("skills", [])
        with st.expander("🛠️ Technical & Professional Skills", expanded=True):
            if skills:
                # Display all skills as formatted badges
                skill_badges = " | ".join([f"🏷️ {skill}" for skill in skills])
                st.markdown(skill_badges)
                st.write(f"**Total Skills:** {len(skills)}")
            else:
                st.info("No skills extracted")
        
        # Raw JSON
        with st.expander("📋 Raw JSON Data"):
            st.json(result)

# ─────────────────────────────────────────────────────────────────
# TAB 2: View Results
# ─────────────────────────────────────────────────────────────────
with tabs[1]:
    if st.session_state.parse_result:
        result = st.session_state.parse_result
        
        # Summary metrics
        st.subheader("📈 Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Name Found", "✅" if result.get("personal_data", {}).get("name") else "❌")
        with col2:
            st.metric("Skills Count", len(result.get("skills", [])))
        with col3:
            st.metric("Education Entries", len(result.get("education", [])))
        with col4:
            st.metric("Experience Entries", len(result.get("experience", [])))
        
        st.divider()
        
        # Detailed results in tabs
        result_tabs = st.tabs([
            "👤 Personal",
            "🎓 Education",
            "💼 Experience",
            "🛠️ Skills",
            "📞 Contact",
            "🏷️ Other"
        ])
        
        # Personal Data
        with result_tabs[0]:
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Name:**", result.get("name", "N/A"))
                st.write("**Email:**", result.get("email", "N/A"))
                st.write("**DOB:**", result.get("dob", "N/A"))
            with col2:
                st.write("**Gender:**", result.get("gender", "N/A"))
                st.write("**Address:**", result.get("address", "N/A"))
                st.write("**Phone:**", result.get("contact_number", "N/A"))
        
        # Education
        with result_tabs[1]:
            education = result.get("education", [])
            if education:
                for idx, edu in enumerate(education, 1):
                    qual = edu.get('qualification', 'Unknown')
                    with st.expander(f"Education #{idx}: {qual}"):
                        st.write("**Qualification:**", edu.get("qualification", "N/A"))
                        st.write("**Institution:**", edu.get("institute_university", "N/A"))
                        st.write("**Branch/Specialization:**", edu.get("specialization_branch", "N/A"))
                        st.write("**Year:**", edu.get("passing_year", "N/A"))
                        st.write("**CGPA/Grade:**", edu.get("grade_cgpa", "N/A"))
                        st.write("**Mode of Study:**", edu.get("mode_of_study", "N/A"))
                        st.write("**Location:**", edu.get("location", "N/A"))
            else:
                st.info("No education data extracted")
        
        # Experience
        with result_tabs[2]:
            experience = result.get("professional_experience", [])
            if experience:
                for idx, exp in enumerate(experience, 1):
                    role = exp.get('role', 'Unknown')
                    with st.expander(f"Job #{idx}: {role}"):
                        st.write("**Role/Title:**", exp.get("role", "N/A"))
                        st.write("**Company:**", exp.get("company_name", "N/A"))
                        st.write("**Duration:**", exp.get("duration_text", "N/A"))
                        st.write("**Location:**", exp.get("location", "N/A"))
                        st.write("**Employment Type:**", exp.get("employment_type", "N/A"))
                        st.write("**Currently Working:**", exp.get("currently_working", "N/A"))
                        
                        # Technologies
                        techs = exp.get("technologies", [])
                        if techs:
                            st.write("**Technologies:**", ", ".join(techs))
                        
                        # Responsibilities
                        resp = exp.get("responsibilities", [])
                        if resp:
                            st.write("**Responsibilities:**")
                            for r in resp:
                                st.write(f"• {r}")
            else:
                st.info("No experience data extracted")
        
        # Skills
        with result_tabs[3]:
            skills = result.get("skills", [])
            if skills:
                # Display skills as formatted badges
                skill_badges = " | ".join([f"🏷️ {skill}" for skill in skills])
                st.markdown(skill_badges)
                st.write(f"**Total Skills:** {len(skills)}")
            else:
                st.info("No skills extracted")
        
        # Contact
        with result_tabs[4]:
            contact_phone = result.get("contact_number", "N/A")
            contact_email = result.get("email", "N/A")
            st.write("**Email:**", contact_email)
            st.write("**Phone:**", contact_phone)
        
        # Other
        with result_tabs[5]:
            # Show fields not displayed in other tabs
            excluded_keys = {
                "name", "email", "contact_number", "dob", "gender", "address",
                "skills", "professional_experience", "education", "file"
            }
            other = {k: v for k, v in result.items() if k not in excluded_keys}
            if other:
                for key, value in other.items():
                    st.write(f"**{key}:**", value)
            else:
                st.info("No additional data")
        
        st.divider()
        
        # Raw JSON
        if st.checkbox("Show Raw JSON"):
            st.json(result)
    
    else:
        st.info("👈 Parse a resume first to see results here")

# ─────────────────────────────────────────────────────────────────
# TAB 3: About & Info
# ─────────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("📋 About Resume Parser")
    
    st.markdown("""
    **Resume Parser** is an AI-powered tool that extracts structured information from CVs and resumes.
    
    ✨ **Features:**
    - Extract personal information (name, email, phone, DOB, address)
    - Identify education history (degree, institution, field, year)
    - Parse work experience (job title, company, duration, location)
    - Recognize technical and soft skills
    - Support for PDF, DOCX, and DOC formats
    
    **Technology Stack:**
    - spaCy for NLP processing
    - pdfminer.six for PDF extraction
    - python-docx for Word document parsing
    - Pattern matching for skill extraction
    
    **Supported File Formats:**
    - PDF (.pdf)
    - Word Documents (.docx, .doc)
    - Max file size: Unlimited (local processing)
    """)
    
    st.divider()
    
    st.subheader("📊 Parser Configuration")
    st.write("**Current Settings:**")
    st.write(f"- Skill Source: **auto**")
    st.write(f"- Validation: **Enabled**")
    st.write(f"- Detailed Logging: **Enabled**")
    st.write(f"- Parser Type: **Standalone (No API)**")

# ─────────────────────────────────────────────────────────────────
# TAB 4: Settings
# ─────────────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("⚙️ About This App")
    
    st.markdown("""
    **Resume Parser v1.0**
    
    Extract structured information from CVs and resumes using advanced AI and pattern matching.
    
    ✨ **Supported Formats:**
    - PDF
    - DOCX
    - DOC
    
    📊 **Extracted Information:**
    - Personal details (name, email, phone, DOB, address)
    - Education history
    - Work experience
    - Technical skills
    - Contact information
    
    🚀 **Features:**
    - Validation reporting
    - Detailed logging
    - JSON export
    - Completely local processing (no API needed!)
    
    ---
    
    **Technology:**
    - Built with Streamlit for web interface
    - Uses spaCy for NLP processing
    - pdfminer.six for PDF extraction
    - python-docx for Word parsing
    
    **No Configuration Needed!**
    Just upload a resume and start parsing.
    """)
    """
    - Contact information
    
    **Features:**
    - Validation reporting
    - Detailed logging
    - JSON export
    """

# ─────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<small>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>",
    unsafe_allow_html=True
)
