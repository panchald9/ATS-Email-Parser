import os
import unittest

from Main_Resume import extract_professional_experience_profile, extract_text


class ProfessionalExperienceParserTests(unittest.TestCase):
    def test_separate_company_role_lines_with_wrapped_bullets(self):
        text = """PROFESSIONAL EXPERIENCE

Acme Industries Pvt. Ltd.
Quality Supervisor
Surat, Gujarat, India
Jan 2022 - Present
• Managed daily inspections and reporting across 3 production lines,
ensuring compliance with client specifications.
• Coordinated maintenance and quality teams.

Beta Labs Pvt. Ltd.
Production Executive
Vapi, Gujarat, India
Jun 2020 - Dec 2021
• Led batch documentation and sampling.

EDUCATION
B.Sc
"""

        experiences = extract_professional_experience_profile(text)

        self.assertEqual(len(experiences), 2)
        self.assertEqual(experiences[0]["company_name"], "Acme Industries Pvt. Ltd.")
        self.assertEqual(experiences[0]["role"], "Quality Supervisor")
        self.assertIn(
            "Managed daily inspections and reporting across 3 production lines, ensuring compliance with client specifications.",
            experiences[0]["responsibilities"],
        )

    def test_fragment_lines_do_not_become_fake_companies(self):
        text = """WORK EXPERIENCE

.NET / React Developer | Industrial Analytical Services
Ahmedabad, Gujarat, India
May 2025 - Jan 2026
• Engineered and maintained responsive React web applications, improving UI
consistency by 30% across modules.
• Architected .NET backend services with secure JWT authentication, reducing average
API response time by 40%.

Faculty Lecturer | C-DAC India
Ahmedabad, Gujarat, India
May 2023 - Jul 2025
• Designed curriculum modules covering AI integration, web technologies, and real-world application development, bridging
theory and industry practice.

SKILLS
Python
"""

        experiences = extract_professional_experience_profile(text)
        company_names = [item.get("company_name") for item in experiences]

        self.assertEqual(len(experiences), 2)
        self.assertNotIn("solutions.", company_names)
        self.assertEqual(experiences[1]["company_name"], "C-DAC India")
        self.assertEqual(experiences[1]["role"], "Faculty Lecturer")
        self.assertIn(
            "Designed curriculum modules covering AI integration, web technologies, and real-world application development, bridging theory and industry practice.",
            experiences[1]["responsibilities"],
        )

    def test_dhruv_pdf_regression(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_path = os.path.join(repo_root, "Bulk_Resumes_1775020050", "Dhruv_Panchal_CV.pdf")
        self.assertTrue(os.path.exists(pdf_path), pdf_path)

        text = extract_text(pdf_path)
        experiences = extract_professional_experience_profile(text)
        company_names = [item.get("company_name") for item in experiences]
        self.assertEqual(len(experiences), 3)
        self.assertEqual(experiences[2]["company_name"], "C-DAC India")
        self.assertEqual(experiences[2]["role"], "Faculty Lecturer")
        self.assertNotIn("solutions.", company_names)
        self.assertIn(
            "Leading a cross-functional development team, overseeing full-stack web and mobile application delivery using React.js, Node.js, Flutter, MySQL, and PostgreSQL across multiple client projects.",
            experiences[0]["responsibilities"],
        )
        self.assertIn(
            "Delivered hands-on training in advanced computing, AI technologies, and software development to 100+ students across multiple batches, maintaining 90%+ satisfaction scores.",
            experiences[2]["responsibilities"],
        )
        self.assertIn(
            "Designed curriculum modules covering AI integration, web technologies, and real-world application development, bridging theory and industry practice.",
            experiences[2]["responsibilities"],
        )

    def test_inline_header_with_trailing_dates_and_parenthetical_company(self):
        text = """WORK EXPERIENCE

Operation & Strategy Planner IEarnify (Styflowne Finance Services Pvt. Ltd.) Jan 2023 – Jun 2024
Tracked and monitored key operational KPIs across lead management, client conversion, and service delivery to ensure process efficiency and performance improvement.
Prepared daily, weekly, and monthly operational reports for management, highlighting trends, gaps, and areas for improvement.
Designed and maintained Excel and Power BI dashboards to analyze KPIs such as lead flow, conversion ratios, response time, and team performance.

Aishee Holidays | Operation Executive Apr 2022 – Dec 2022
Managed lead follow-ups, client coordination, and booking schedules to ensure smooth service execution.
Coordinated with vendors, travel partners, and internal teams for timely delivery of travel services.

SKILLS
Power BI
"""

        experiences = extract_professional_experience_profile(text)

        self.assertEqual(len(experiences), 2)
        self.assertEqual(experiences[0]["company_name"], "IEarnify (Styflowne Finance Services Pvt. Ltd.)")
        self.assertEqual(experiences[0]["role"], "Operation & Strategy Planner")
        self.assertEqual(experiences[0]["start_date"], "Jan 2023")
        self.assertEqual(experiences[0]["end_date"], "Jun 2024")
        self.assertEqual(experiences[1]["company_name"], "Aishee Holidays")
        self.assertEqual(experiences[1]["role"], "Operation Executive")
        self.assertEqual(experiences[1]["start_date"], "Apr 2022")
        self.assertEqual(experiences[1]["end_date"], "Dec 2022")


if __name__ == "__main__":
    unittest.main()
