import json
import os
import tempfile
from pathlib import Path

import streamlit as st

from Main_Resume import (
    SKILLS_CSV,
    _extract_resume_record,
    build_skill_matchers,
    load_skills_from_csv,
)

SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx"}


@st.cache_data(show_spinner=False)
def get_skills_list():
    return load_skills_from_csv(SKILLS_CSV)


@st.cache_data(show_spinner=False)
def get_compiled_skill_matchers():
    return build_skill_matchers(get_skills_list())


def parse_resume_bytes(file_name: str, file_bytes: bytes):
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported format. Please upload .pdf, .doc, or .docx file")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        record = _extract_resume_record(
            fname=os.path.basename(temp_path),
            process_folder=os.path.dirname(temp_path),
            skill_source="auto",
            skills_list=get_skills_list(),
            compiled_skill_matchers=get_compiled_skill_matchers(),
            fast_response=False,
        )

        record["file"] = file_name
        return record
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def main():
    st.set_page_config(page_title="ATS Resume Parser", page_icon="📄", layout="wide")

    st.title("ATS Resume Parser")
    st.caption("Upload resumes and view structured extraction output in the browser")

    uploaded_files = st.file_uploader(
        "Upload resume files (.pdf, .doc, .docx)",
        type=["pdf", "doc", "docx"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("Select one or more resume files to parse.")
        return

    if st.button("Parse Resumes", type="primary"):
        parsed_results = []
        with st.spinner("Parsing resumes..."):
            for uploaded in uploaded_files:
                try:
                    data = parse_resume_bytes(uploaded.name, uploaded.getvalue())
                    parsed_results.append(data)
                except Exception as exc:
                    parsed_results.append(
                        {
                            "file": uploaded.name,
                            "name": None,
                            "contact_number": None,
                            "email": None,
                            "dob": None,
                            "gender": None,
                            "address": None,
                            "skills": [],
                            "professional_experience": [],
                            "error": str(exc),
                        }
                    )

        st.success(f"Parsed {len(parsed_results)} file(s)")

        table_rows = []
        for item in parsed_results:
            experiences = item.get("professional_experience") or []
            first_exp = experiences[0] if experiences else {}
            table_rows.append(
                {
                    "file": item.get("file"),
                    "name": item.get("name") or "",
                    "contact_number": item.get("contact_number") or "",
                    "email": item.get("email") or "",
                    "dob": item.get("dob") or "",
                    "gender": item.get("gender") or "",
                    "skills_count": len(item.get("skills") or []),
                    "experience_count": len(experiences),
                    "latest_company": first_exp.get("company_name") or "",
                    "latest_role": first_exp.get("role") or "",
                    "currently_working": bool(first_exp.get("currently_working", False)),
                    "error": item.get("error") or "",
                }
            )

        st.subheader("Summary")
        st.dataframe(table_rows, width="stretch")

        st.subheader("Experience Details")
        for item in parsed_results:
            with st.expander(f"{item.get('file')} - professional_experience"):
                experiences = item.get("professional_experience") or []
                if experiences:
                    st.json(experiences)
                else:
                    st.caption("No structured professional experience detected.")

        st.subheader("File-by-File Response")
        for item in parsed_results:
            file_name = item.get("file") or "unknown_file"
            with st.expander(f"{file_name} - full parsed response"):
                st.json(item)

        json_data = json.dumps(parsed_results, indent=2, ensure_ascii=False)
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name="resume_parsed_streamlit.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
