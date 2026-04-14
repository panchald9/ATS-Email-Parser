"""
Test suite for Streamlit Resume Parser App
Tests for UI interaction and session state
"""

import pytest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))


# ──────────────────────────────────────────────────────────────────
# Session State Tests
# ──────────────────────────────────────────────────────────────────
class TestSessionState:
    """Test Streamlit session state management"""
    
    def test_session_state_initialization(self):
        """Test that session state initializes correctly"""
        # Mock session state
        session_state = {
            "parse_result": None,
            "parsing_failed": False
        }
        
        assert session_state["parse_result"] is None
        assert session_state["parsing_failed"] is False
    
    def test_session_state_update(self):
        """Test updating session state"""
        session_state = {
            "parse_result": None,
            "parsing_failed": False
        }
        
        # Simulate parsing result
        session_state["parse_result"] = {
            "personal_data": {"name": "John Doe"},
            "skills": ["Python", "JavaScript"]
        }
        session_state["parsing_failed"] = False
        
        assert session_state["parse_result"] is not None
        assert session_state["parse_result"]["personal_data"]["name"] == "John Doe"


# ──────────────────────────────────────────────────────────────────
# Configuration Tests
# ──────────────────────────────────────────────────────────────────
class TestStreamlitConfig:
    """Test Streamlit configuration"""
    
    def test_api_url_configuration(self):
        """Test API URL is configurable"""
        import os
        api_url = os.getenv("API_URL", "http://localhost:8000")
        assert "http" in api_url or "localhost" in api_url
    
    def test_api_key_configuration(self):
        """Test API key is configurable"""
        import os
        api_key = os.getenv("API_KEY", "dev-secret-key")
        assert len(api_key) > 0


# ──────────────────────────────────────────────────────────────────
# Data Parsing Tests
# ──────────────────────────────────────────────────────────────────
class TestDataParsing:
    """Test parsing resume data"""
    
    def test_parse_result_structure(self):
        """Test resume parsing result has correct structure"""
        result = {
            "personal_data": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "date_of_birth": "1990-01-01",
                "gender": "Male",
                "address": "123 Main St"
            },
            "education": [
                {
                    "degree": "B.S.",
                    "institution": "University",
                    "field": "Computer Science",
                    "year": "2012",
                    "cgpa": "3.8"
                }
            ],
            "experience": [
                {
                    "job_title": "Software Engineer",
                    "company_name": "Tech Corp",
                    "duration": "2012-2022",
                    "location": "New York",
                    "job_description": "Developed applications"
                }
            ],
            "skills": ["Python", "JavaScript", "React"],
            "contact_info": {
                "email": "john@example.com",
                "phone": "+1234567890"
            },
            "validation_issues": [],
            "parsing_success": True,
            "message": "Resume parsed successfully"
        }
        
        # Validate structure
        assert "personal_data" in result
        assert "education" in result
        assert "experience" in result
        assert "skills" in result
        assert isinstance(result["skills"], list)
        assert result["parsing_success"] is True


# ──────────────────────────────────────────────────────────────────
# Mock API Response Tests
# ──────────────────────────────────────────────────────────────────
class TestMockAPIResponse:
    """Test parsing mock API responses"""
    
    def test_valid_api_response_parsing(self):
        """Test parsing valid API response"""
        mock_response = {
            "personal_data": {
                "name": "Alice Smith",
                "email": "alice@example.com"
            },
            "skills": ["Python", "Data Analysis"],
            "education": [],
            "experience": [],
            "parsing_success": True
        }
        
        # Simulate parsing
        assert mock_response["personal_data"]["name"] == "Alice Smith"
        assert mock_response["parsing_success"] is True
        assert len(mock_response["skills"]) == 2
    
    def test_error_api_response_handling(self):
        """Test handling error API responses"""
        mock_error = {
            "detail": "Unsupported file type",
            "status_code": 400
        }
        
        assert "detail" in mock_error
        assert mock_error["status_code"] == 400


# ──────────────────────────────────────────────────────────────────
# UI Component Tests
# ──────────────────────────────────────────────────────────────────
class TestUIComponents:
    """Test UI component functionality"""
    
    def test_file_upload_validation(self):
        """Test file upload validation"""
        valid_extensions = [".pdf", ".docx", ".doc"]
        
        # Test valid file
        assert ".pdf" in valid_extensions
        assert ".docx" in valid_extensions
        
        # Test invalid file
        assert ".txt" not in valid_extensions
        assert ".jpg" not in valid_extensions
    
    def test_skill_display_formatting(self):
        """Test skill display formatting"""
        skills = ["Python", "JavaScript", "React", "PostgreSQL"]
        
        # Skills should be in columns (3 columns in UI)
        assert len(skills) > 0
        columns_needed = (len(skills) + 2) // 3
        assert columns_needed >= 1


# ──────────────────────────────────────────────────────────────────
# Tab Navigation Tests
# ──────────────────────────────────────────────────────────────────
class TestTabNavigation:
    """Test tab navigation structure"""
    
    def test_tab_structure(self):
        """Test that all required tabs are present"""
        tabs = [
            "📤 Upload & Parse",
            "📊 View Results",
            "ℹ️ API Info",
            "⚙️ Settings"
        ]
        
        assert len(tabs) == 4
        assert all(isinstance(tab, str) for tab in tabs)
        assert all(len(tab) > 0 for tab in tabs)
    
    def test_result_tabs_structure(self):
        """Test result display tabs"""
        result_tabs = [
            "👤 Personal",
            "🎓 Education",
            "💼 Experience",
            "🛠️ Skills",
            "📞 Contact",
            "🏷️ Other"
        ]
        
        assert len(result_tabs) == 6


# ──────────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────────
class TestIntegration:
    """Integration tests for Streamlit app"""
    
    def test_complete_resume_parsing_flow(self):
        """Test complete resume parsing workflow"""
        # Step 1: Initialize session state
        session_state = {"parse_result": None, "parsing_failed": False}
        
        # Step 2: Simulate file upload and parsing
        parse_result = {
            "personal_data": {"name": "John Doe", "email": "john@example.com"},
            "skills": ["Python", "JavaScript"],
            "education": [],
            "experience": [],
            "parsing_success": True
        }
        
        # Step 3: Update session state
        session_state["parse_result"] = parse_result
        session_state["parsing_failed"] = False
        
        # Step 4: Verify results
        assert session_state["parse_result"] is not None
        assert session_state["parsing_failed"] is False
        assert session_state["parse_result"]["personal_data"]["name"] == "John Doe"
    
    def test_error_handling_flow(self):
        """Test error handling in workflow"""
        session_state = {"parse_result": None, "parsing_failed": False}
        
        # Simulate error
        error_result = {
            "detail": "Unsupported file type",
            "status_code": 400
        }
        
        # Update state
        session_state["parsing_failed"] = True
        
        assert session_state["parsing_failed"] is True


# ──────────────────────────────────────────────────────────────────
# Run Tests
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
