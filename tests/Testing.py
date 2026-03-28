"""
batch_extract.py
================
Give it a FOLDER of resumes (PDF, TXT, DOCX) → Ollama extracts all data
→ saves each result as a separate .txt file in an output folder.

Usage:
  python batch_extract.py resumes/
  python batch_extract.py resumes/ --output results/
  python batch_extract.py resumes/ --output results/ --model llama3.2
"""

import sys
import os
import json
import re
import argparse
import ollama

# ── Config ────────────────────────────────────────────────────
DEFAULT_MODEL = "llama3.2"
SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".doc", ".docx")


# ── Parse Ollama JSON response ────────────────────────────────
def parse_ollama_json(response: dict) -> dict:
    raw = response["message"]["content"].strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise json.JSONDecodeError(
            f"{exc.msg}. Raw response: {raw[:300]}",
            exc.doc,
            exc.pos,
        ) from exc


# ── Read resume file ──────────────────────────────────────────
def read_file(path: str) -> str:
    ext = path.lower().split(".")[-1]

    if ext == "txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == "pdf":
        try:
            import pdfplumber
        except ImportError:
            print("  📦 Installing pdfplumber...")
            os.system("pip install pdfplumber -q")
            import pdfplumber
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text

    elif ext in ("doc", "docx"):
        try:
            import docx
        except ImportError:
            print("  📦 Installing python-docx...")
            os.system("pip install python-docx -q")
            import docx
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)

    else:
        raise ValueError(f"Unsupported file type: .{ext}")


# ── Prompt ────────────────────────────────────────────────────
PROMPT = """You are an expert ATS resume parser. Extract ALL information from the resume below.
Return ONLY valid JSON, no explanation, no markdown, no code blocks.

RESUME TEXT:
{resume_text}

Return this EXACT JSON structure (use null for missing fields):

{{
  "candidate": {{
    "full_name": null,
    "professional_title": null,
    "current_designation": null,
    "email": null,
    "phone": null,
    "alternate_phone": null,
    "address": null,
    "city": null,
    "linkedin": null,
    "github": null,
    "portfolio": null,
    "twitter": null,
    "professional_summary": null,
    "total_experience_months": 0,
    "current_ctc": null,
    "expected_ctc": null,
    "notice_period_days": null,
    "open_to_relocation": false,
    "open_to_remote": false
  }},

  "experience": [
    {{
      "company_name": null,
      "designation_role": null,
      "employment_type": "Full-time",
      "industry": null,
      "functional_area": null,
      "department": null,
      "location": null,
      "employment_start_date": null,
      "employment_end_date": null,
      "currently_working": false,
      "role_experience_months": 0,
      "team_size": null,
      "reporting_to": null,
      "key_responsibilities": null,
      "key_achievements": null,
      "technologies_used": null,
      "business_impact": null,
      "reason_for_leaving": null
    }}
  ],

  "graduation": {{
    "qualification": null,
    "specialization_branch": null,
    "institute_university_name": null,
    "location": null,
    "passing_year": null,
    "grade_cgpa_percent": null,
    "mode_of_study": "Full-time",
    "major_subjects": null
  }},

  "post_graduation": {{
    "qualification": null,
    "specialization": null,
    "institute_university_name": null,
    "location": null,
    "passing_year": null,
    "grade": null,
    "research_area": null,
    "thesis_major_project_title": null
  }},

  "technical_skills": [
    {{
      "skill_name": null,
      "category": "Other",
      "version": null,
      "years_of_experience": 0,
      "currently_using": true,
      "skill_level_rating": 3,
      "proficiency": "Intermediate"
    }}
  ],

  "projects": [
    {{
      "project_title": null,
      "project_category": "General",
      "organization_client_name": null,
      "your_role_designation": null,
      "industry_domain": null,
      "project_start_date": null,
      "project_end_date": null,
      "currently_working": false,
      "team_size": null,
      "project_objective": null,
      "your_responsibilities": null,
      "tools_technologies_used": null,
      "methodology_used": null,
      "key_achievements": null,
      "business_academic_impact": null,
      "quantifiable_results": null
    }}
  ],

  "certifications": [
    {{
      "certification": null,
      "issuing_organization": null,
      "completed_date": null,
      "valid_till": null,
      "grade_score": null,
      "credential_id": null,
      "certification_link": null,
      "skills_covered": null,
      "mode": "Online",
      "institute_name": null
    }}
  ],

  "languages": [
    {{
      "language_name": null,
      "proficiency_level": "Intermediate",
      "can_read": true,
      "can_write": true,
      "can_speak": true,
      "business_communication_capability": false
    }}
  ],

  "references": [
    {{
      "reference_type": "Professional",
      "person_name": null,
      "designation": null,
      "organization_name": null,
      "relationship_with_you": null,
      "contact_number": null,
      "email_id": null,
      "years_known": null
    }}
  ],

  "social_networks": [
    {{
      "network": null,
      "link": null,
      "username": null
    }}
  ]
}}"""


# ── Extract with Ollama ───────────────────────────────────────
def extract(resume_text: str, model: str) -> dict:
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": PROMPT.format(resume_text=resume_text[:6000])}],
        format="json",
        options={"temperature": 0}
    )
    return parse_ollama_json(response)


# ── Format output as readable text ───────────────────────────
def format_output(data: dict, source_file: str) -> str:
    lines = []

    def h(title): lines.append(f"\n{'='*55}\n  {title}\n{'='*55}")
    def field(k, v):
        if v not in (None, "", [], {}):
            lines.append(f"  {k:<30} {v}")

    lines.append(f"\n  SOURCE FILE: {source_file}")

    # ── Candidate ──
    h("👤 PERSONAL DETAILS")
    c = data.get("candidate", {}) or {}
    field("Full Name",            c.get("full_name"))
    field("Professional Title",   c.get("professional_title"))
    field("Current Designation",  c.get("current_designation"))
    field("Email",                c.get("email"))
    field("Phone",                c.get("phone"))
    field("Alternate Phone",      c.get("alternate_phone"))
    field("Address/City",         c.get("address") or c.get("city"))
    field("LinkedIn",             c.get("linkedin"))
    field("GitHub",               c.get("github"))
    field("Portfolio",            c.get("portfolio"))
    field("Total Experience",     f"{c.get('total_experience_months', 0)} months")
    field("Current CTC",          c.get("current_ctc"))
    field("Expected CTC",         c.get("expected_ctc"))
    field("Notice Period (days)", c.get("notice_period_days"))
    field("Open to Relocation",   c.get("open_to_relocation"))
    field("Open to Remote",       c.get("open_to_remote"))
    if c.get("professional_summary"):
        lines.append(f"\n  Summary:\n  {c['professional_summary']}")

    # ── Experience ──
    h("💼 WORK EXPERIENCE")
    for i, exp in enumerate(data.get("experience", []) or [], 1):
        lines.append(f"\n  [{i}] {exp.get('company_name')} — {exp.get('designation_role')}")
        field("  Employment Type",     exp.get("employment_type"))
        field("  Industry",            exp.get("industry"))
        field("  Location",            exp.get("location"))
        field("  Start Date",          exp.get("employment_start_date"))
        field("  End Date",            exp.get("employment_end_date") or ("Present" if exp.get("currently_working") else None))
        field("  Experience Months",   exp.get("role_experience_months"))
        field("  Team Size",           exp.get("team_size"))
        field("  Reporting To",        exp.get("reporting_to"))
        field("  Technologies",        exp.get("technologies_used"))
        if exp.get("key_responsibilities"):
            lines.append(f"  Responsibilities:\n    {exp['key_responsibilities'][:300]}")
        if exp.get("key_achievements"):
            lines.append(f"  Achievements:\n    {exp['key_achievements'][:300]}")

    # ── Education ──
    h("🎓 EDUCATION")
    g = data.get("graduation", {}) or {}
    if g.get("qualification"):
        lines.append(f"\n  Graduation:")
        field("  Qualification",       g.get("qualification"))
        field("  Specialization",      g.get("specialization_branch"))
        field("  Institute",           g.get("institute_university_name"))
        field("  Passing Year",        g.get("passing_year"))
        field("  Grade/CGPA",          g.get("grade_cgpa_percent"))

    pg = data.get("post_graduation", {}) or {}
    if pg.get("qualification"):
        lines.append(f"\n  Post Graduation:")
        field("  Qualification",       pg.get("qualification"))
        field("  Specialization",      pg.get("specialization"))
        field("  Institute",           pg.get("institute_university_name"))
        field("  Passing Year",        pg.get("passing_year"))
        field("  Grade",               pg.get("grade"))

    # ── Skills ──
    h("🛠️  TECHNICAL SKILLS")
    for sk in (data.get("technical_skills", []) or []):
        if sk.get("skill_name"):
            lines.append(f"  • {sk['skill_name']:<25} {sk.get('proficiency',''):<15} {sk.get('category','')}")

    # ── Projects ──
    h("🗂️  PROJECTS")
    for i, p in enumerate(data.get("projects", []) or [], 1):
        if p.get("project_title"):
            lines.append(f"\n  [{i}] {p['project_title']}")
            field("  Category",            p.get("project_category"))
            field("  Role",                p.get("your_role_designation"))
            field("  Tools/Tech",          p.get("tools_technologies_used"))
            field("  Duration",            f"{p.get('project_start_date','')} → {p.get('project_end_date','Present')}")
            if p.get("project_objective"):
                lines.append(f"  Objective: {p['project_objective'][:200]}")

    # ── Certifications ──
    h("📜 CERTIFICATIONS")
    for cert in (data.get("certifications", []) or []):
        if cert.get("certification"):
            lines.append(f"  • {cert['certification']}")
            field("    Issuer",         cert.get("issuing_organization"))
            field("    Completed",      cert.get("completed_date"))
            field("    Credential ID",  cert.get("credential_id"))

    # ── Languages ──
    h("🌐 LANGUAGES")
    for lang in (data.get("languages", []) or []):
        if lang.get("language_name"):
            caps = []
            if lang.get("can_read"):  caps.append("Read")
            if lang.get("can_write"): caps.append("Write")
            if lang.get("can_speak"): caps.append("Speak")
            lines.append(f"  • {lang['language_name']:<15} {lang.get('proficiency_level',''):<15} ({', '.join(caps)})")

    # ── References ──
    h("👥 REFERENCES")
    for ref in (data.get("references", []) or []):
        if ref.get("person_name"):
            lines.append(f"  • {ref['person_name']} — {ref.get('designation','')} @ {ref.get('organization_name','')}")
            field("    Contact",        ref.get("contact_number"))
            field("    Email",          ref.get("email_id"))

    # ── Social ──
    h("🔗 SOCIAL NETWORKS")
    for net in (data.get("social_networks", []) or []):
        if net.get("network") and net.get("link"):
            lines.append(f"  • {net['network']:<15} {net['link']}")

    lines.append("\n" + "="*55)
    lines.append("  ✅ Extraction complete — ready to import to DB")
    lines.append("="*55 + "\n")

    return "\n".join(str(l) for l in lines)


# ── Scan folder for resume files ──────────────────────────────
def get_resume_files(folder: str) -> list:
    """Return all supported resume files from a folder (non-recursive)."""
    if not os.path.isdir(folder):
        print(f"❌ Folder not found: {folder}")
        sys.exit(1)

    files = []
    for fname in sorted(os.listdir(folder)):
        if fname.lower().endswith(SUPPORTED_EXTENSIONS):
            files.append(os.path.join(folder, fname))

    return files


# ── Safe output filename ──────────────────────────────────────
def safe_stem(filename: str) -> str:
    """Convert filename (without ext) to a safe output stem."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r'[^\w\s-]', '', stem).strip()
    stem = re.sub(r'\s+', '_', stem)
    return stem or "resume"


# ── Main ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Batch resume extractor — processes a folder of resumes with Ollama"
    )
    parser.add_argument("folder", help="Folder containing resume files (PDF/TXT/DOCX)")
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output folder for .txt results (default: <folder>/extracted/)"
    )
    parser.add_argument(
        "--model", "-m", default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Also save raw JSON alongside each .txt file"
    )
    args = parser.parse_args()

    # Resolve output folder
    output_dir = args.output or os.path.join(args.folder, "extracted")
    os.makedirs(output_dir, exist_ok=True)

    # Gather files
    resume_files = get_resume_files(args.folder)
    if not resume_files:
        print(f"❌ No supported resume files found in: {args.folder}")
        print(f"   Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(1)

    total = len(resume_files)
    print(f"\n📂 Folder    : {args.folder}")
    print(f"📁 Output    : {output_dir}")
    print(f"🤖 Model     : {args.model}")
    print(f"📄 Resumes   : {total} file(s) found")
    print(f"{'─'*55}")

    passed, failed = [], []

    for idx, resume_path in enumerate(resume_files, 1):
        fname = os.path.basename(resume_path)
        print(f"\n[{idx}/{total}] 📄 {fname}")

        # ── Read ──
        try:
            resume_text = read_file(resume_path)
            print(f"        ✅ Read  — {len(resume_text):,} characters")
        except Exception as e:
            print(f"        ❌ Read failed: {e}")
            failed.append((fname, str(e)))
            continue

        # ── Extract ──
        try:
            print(f"        🤖 Sending to Ollama ({args.model})...")
            data = extract(resume_text, args.model)
            print(f"        ✅ Extracted")
        except json.JSONDecodeError as e:
            print(f"        ❌ JSON parse error: {e}")
            failed.append((fname, str(e)))
            continue
        except Exception as e:
            print(f"        ❌ Ollama error: {e}")
            print(f"           Make sure Ollama is running: ollama serve")
            failed.append((fname, str(e)))
            continue

        # ── Save ──
        stem = safe_stem(fname)
        txt_path  = os.path.join(output_dir, f"{stem}.txt")
        json_path = os.path.join(output_dir, f"{stem}.json")

        readable = format_output(data, source_file=fname)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(readable)

        if args.json:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"        💾 Saved → {stem}.txt  +  {stem}.json")
        else:
            print(f"        💾 Saved → {stem}.txt")

        # Show candidate name if found
        name = (data.get("candidate") or {}).get("full_name")
        if name:
            print(f"        👤 Name  → {name}")

        passed.append(fname)

    # ── Summary ──────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  ✅ Processed : {len(passed)}/{total}")
    if failed:
        print(f"  ❌ Failed    : {len(failed)}/{total}")
        for fname, reason in failed:
            print(f"     • {fname}: {reason[:80]}")
    print(f"  📁 Output    : {output_dir}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()