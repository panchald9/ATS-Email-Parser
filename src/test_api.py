"""
Test suite for Resume Parser API
Unit and integration tests for API endpoints
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from io import BytesIO

# Set test environment variables before importing the app
os.environ["API_KEY"] = "dev-secret-key"
os.environ["ENV"] = "testing"

from fastapi.testclient import TestClient
import main_resume_api as api_module


# ──────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    """Create test client"""
    return TestClient(api_module.app)


@pytest.fixture
def valid_api_key():
    """Get valid API key"""
    return api_module.API_KEY


@pytest.fixture
def invalid_api_key():
    """Get invalid API key"""
    return "invalid-key-12345"


@pytest.fixture
def sample_pdf_file():
    """Create a fake PDF file for testing"""
    pdf_content = b"%PDF-1.4\n%fake pdf content\nendstream\nendobj"
    return BytesIO(pdf_content)


@pytest.fixture
def sample_docx_file():
    """Create a fake DOCX file for testing"""
    # Minimal DOCX is a ZIP file
    docx_content = b"PK\x03\x04"  # ZIP file header
    return BytesIO(docx_content)


# ──────────────────────────────────────────────────────────────────
# Authentication Tests
# ──────────────────────────────────────────────────────────────────
class TestAuthentication:
    """Test API authentication"""
    
    def test_health_check_without_key(self, client):
        """Test health endpoint without API key"""
        response = client.get("/health")
        assert response.status_code == 401
        assert "Unauthorized" in response.text or "detail" in response.json()
    
    def test_health_check_with_invalid_key(self, client, invalid_api_key):
        """Test health endpoint with invalid API key"""
        response = client.get(
            "/health",
            headers={"x-api-key": invalid_api_key}
        )
        assert response.status_code == 401
    
    def test_health_check_with_valid_key(self, client, valid_api_key):
        """Test health endpoint with valid API key"""
        response = client.get(
            "/health",
            headers={"x-api-key": valid_api_key}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ──────────────────────────────────────────────────────────────────
# Endpoint Tests
# ──────────────────────────────────────────────────────────────────
class TestEndpoints:
    """Test API endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data
    
    def test_health_endpoint(self, client, valid_api_key):
        """Test health endpoint"""
        response = client.get(
            "/health",
            headers={"x-api-key": valid_api_key}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ──────────────────────────────────────────────────────────────────
# File Upload Tests
# ──────────────────────────────────────────────────────────────────
class TestFileUpload:
    """Test file upload functionality"""
    
    def test_parse_without_file(self, client, valid_api_key):
        """Test parse endpoint without file"""
        response = client.post(
            "/parse",
            headers={"x-api-key": valid_api_key}
        )
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_parse_with_unsupported_file_type(self, client, valid_api_key):
        """Test parse endpoint with unsupported file type"""
        response = client.post(
            "/parse",
            files={"file": ("test.txt", BytesIO(b"text content"), "text/plain")},
            headers={"x-api-key": valid_api_key}
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
    
    def test_parse_with_pdf(self, client, valid_api_key, sample_pdf_file):
        """Test parse endpoint with PDF file"""
        response = client.post(
            "/parse",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            headers={"x-api-key": valid_api_key}
        )
        # Should return 422 if parsing fails (expected for fake PDF)
        assert response.status_code in [200, 422]
    
    def test_parse_batch_without_files(self, client, valid_api_key):
        """Test batch parse without files"""
        response = client.post(
            "/parse-batch",
            headers={"x-api-key": valid_api_key}
        )
        assert response.status_code == 422
    
    def test_parse_batch_with_multiple_files(self, client, valid_api_key):
        """Test batch parse with multiple files"""
        files = [
            ("file1.pdf", BytesIO(b"%PDF-1.4\n"), "application/pdf"),
            ("file2.pdf", BytesIO(b"%PDF-1.4\n"), "application/pdf"),
        ]
        response = client.post(
            "/parse-batch",
            files=[("files", f) for f in files],
            headers={"x-api-key": valid_api_key}
        )
        # Should return 200 for batch endpoint
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "results" in data


# ──────────────────────────────────────────────────────────────────
# Rate Limiting Tests
# ──────────────────────────────────────────────────────────────────
class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_not_exceeded(self, client, valid_api_key):
        """Test that normal requests are allowed"""
        response = client.get(
            "/health",
            headers={"x-api-key": valid_api_key}
        )
        assert response.status_code == 200
    
    def test_rate_limit_header(self, client, valid_api_key):
        """Test rate limit configuration"""
        # Make a single request to check we're under the limit
        response = client.get(
            "/health",
            headers={"x-api-key": valid_api_key}
        )
        assert response.status_code == 200


# ──────────────────────────────────────────────────────────────────
# Response Format Tests
# ──────────────────────────────────────────────────────────────────
class TestResponseFormats:
    """Test response data formats"""
    
    def test_health_response_format(self, client, valid_api_key):
        """Test health response has correct format"""
        response = client.get(
            "/health",
            headers={"x-api-key": valid_api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
    
    def test_error_response_format(self, client, invalid_api_key):
        """Test error response has correct format"""
        response = client.get(
            "/health",
            headers={"x-api-key": invalid_api_key}
        )
        assert response.status_code == 401
        data = response.json()
        assert isinstance(data, dict)
        assert "detail" in data


# ──────────────────────────────────────────────────────────────────
# Configuration Tests
# ──────────────────────────────────────────────────────────────────
class TestConfiguration:
    """Test API configuration"""
    
    def test_max_upload_size_configured(self):
        """Test max upload size is configured"""
        assert api_module.MAX_UPLOAD_MB > 0
        assert api_module.MAX_UPLOAD_BYTES == api_module.MAX_UPLOAD_MB * 1024 * 1024
    
    def test_rate_limit_configured(self):
        """Test rate limit is configured"""
        assert api_module.RATE_LIMIT_PER_MINUTE > 0
    
    def test_supported_extensions_configured(self):
        """Test supported file extensions are configured"""
        assert ".pdf" in api_module.SUPPORTED_EXTENSIONS
        assert ".docx" in api_module.SUPPORTED_EXTENSIONS
        assert ".doc" in api_module.SUPPORTED_EXTENSIONS
    
    def test_cors_origins_configured(self):
        """Test CORS origins are configured"""
        assert len(api_module.ALLOWED_ORIGINS) > 0


# ──────────────────────────────────────────────────────────────────
# Edge Cases
# ──────────────────────────────────────────────────────────────────
class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_filename(self, client, valid_api_key):
        """Test with empty filename"""
        response = client.post(
            "/parse",
            files={"file": ("", BytesIO(b"content"), "application/pdf")},
            headers={"x-api-key": valid_api_key}
        )
        # Should handle gracefully
        assert response.status_code in [400, 422]
    
    def test_very_large_key(self, client):
        """Test with very large API key"""
        large_key = "x" * 1000
        response = client.get(
            "/health",
            headers={"x-api-key": large_key}
        )
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────
# Run Tests
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
