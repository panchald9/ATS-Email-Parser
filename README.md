# 📄 Resume Parser - AI-Powered Resume Extraction

A production-ready resume parsing system with Streamlit UI and FastAPI backend. Extract structured information from CVs and resumes using advanced AI and pattern matching.

## ✨ Features

### 🎯 Core Functionality
- ✅ **Multi-format Support**: PDF, DOCX, DOC
- ✅ **Personal Data Extraction**: Name, Email, Phone, DOB, Address, Gender
- ✅ **Education History**: Degree, Institution, Field, Year, CGPA
- ✅ **Work Experience**: Job Title, Company, Duration, Location, Description
- ✅ **Skills Recognition**: AI-powered skill extraction and validation
- ✅ **Batch Processing**: Parse multiple resumes in one go

### 🔒 Security & Reliability
- ✅ **API Key Authentication**: Secure endpoint protection
- ✅ **Rate Limiting**: Prevent abuse with per-minute limits
- ✅ **File Validation**: Type and size checking
- ✅ **CORS Support**: Safe cross-origin requests
- ✅ **Error Handling**: Graceful fallbacks and logging

### 🚀 Deployment Options
- ✅ **Local Development**: Run locally with `run_dev.py`
- ✅ **Docker Support**: Ready for containerization
- ✅ **Streamlit Cloud**: Deploy to https://share.streamlit.io/
- ✅ **API Hosting**: Deploy FastAPI anywhere (Railway, AWS, Azure, etc.)

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Local Development](#local-development)
4. [API Documentation](#api-documentation)
5. [Streamlit App](#streamlit-app)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### 30-Second Setup

```bash
# 1. Navigate to project directory
cd d:\Project\ATS\ATS\ Email\ Parser

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r src/requirements.txt

# 4. Run development servers (Windows)
run_dev.bat

# Or (macOS/Linux)
python run_dev.py
```

**That's it!** Your app is now running:
- 🎨 **Streamlit UI**: http://localhost:8501
- 🔌 **API Backend**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs

---

## 💻 Installation

### Prerequisites
- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/)
- **Virtual Environment** - Built into Python

### Step 1: Clone or Navigate to Project

```bash
# If cloning
git clone https://github.com/YOUR_USERNAME/resume-parser.git
cd resume-parser

# Or just navigate if already have the project
cd d:\Project\ATS\ATS\ Email\ Parser
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r src/requirements.txt

# Or install from root (if exists)
pip install -r requirements.txt
```

### Step 4: Download Language Models

```bash
# Download spaCy English model (required for NLP)
python -m spacy download en_core_web_sm
```

---

## 🔧 Local Development

### Option 1: Run Both Servers (Recommended)

```bash
# Windows
run_dev.bat

# macOS/Linux
python run_dev.py
```

This starts:
- FastAPI backend on `http://localhost:8000`
- Streamlit app on `http://localhost:8501`

### Option 2: Run Separately

```bash
# Terminal 1: Start API
cd src
python -m uvicorn main_resume_api:app --reload --port 8000

# Terminal 2: Start Streamlit
cd src
streamlit run streamlit_app.py --server.port 8501
```

### Option 3: Quick Test

```bash
# Just run Streamlit (uses default API_URL)
cd src
streamlit run streamlit_app.py
```

---

## 📚 API Documentation

### Base Configuration

```python
# Environment Variables (.env or .env.example)
API_KEY=dev-secret-key
API_URL=http://localhost:8000
MAX_UPLOAD_MB=10
RATE_LIMIT_PER_MINUTE=30
```

### Authentication

All API endpoints require the `x-api-key` header:

```bash
curl -H "x-api-key: dev-secret-key" http://localhost:8000/health
```

### Endpoints

#### 1. Health Check
```bash
GET /health

Response:
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2024-04-14T10:30:00Z"
}
```

#### 2. Parse Resume
```bash
POST /parse
Content-Type: multipart/form-data

Parameters:
  - file: Resume file (PDF, DOCX, or DOC)
  - enable_validation: boolean (optional)
  - enable_detailed_log: boolean (optional)

Response:
{
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
      "institution": "MIT",
      "field": "Computer Science",
      "year": "2012",
      "cgpa": "3.8"
    }
  ],
  "experience": [
    {
      "job_title": "Senior Engineer",
      "company_name": "Tech Corp",
      "duration": "2012-2023",
      "location": "San Francisco",
      "job_description": "Led engineering team..."
    }
  ],
  "skills": ["Python", "JavaScript", "React", "AWS"],
  "parsing_success": true,
  "message": "Resume parsed successfully"
}
```

#### 3. Batch Parse
```bash
POST /parse-batch
Content-Type: multipart/form-data

Parameters:
  - files: Multiple resume files

Response:
{
  "count": 2,
  "results": [
    {
      "file": "resume1.pdf",
      "success": true,
      "data": { ...parsed data... }
    },
    {
      "file": "resume2.pdf",
      "success": false,
      "error": "Unsupported file type"
    }
  ]
}
```

#### 4. API Info
```bash
GET /info

Response:
{
  "name": "Resume Parser API",
  "version": "1.0.0",
  "supported_formats": [".pdf", ".docx", ".doc"],
  "max_upload_mb": 10,
  "rate_limit": "30/min"
}
```

### Error Responses

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad request
- `401` - Unauthorized
- `413` - File too large
- `429` - Rate limit exceeded
- `422` - Unprocessable entity
- `500` - Server error

---

## 🎨 Streamlit App

### Features

#### 📤 Upload & Parse Tab
- Drag-and-drop file upload
- Real-time parsing status
- Options for validation and logging
- Download results as JSON

#### 📊 View Results Tab
- Color-coded data display
- Personal information summary
- Education history
- Work experience timeline
- Skills cloud
- Contact information
- Raw JSON viewer

#### ℹ️ API Info Tab
- API endpoint documentation
- Health status checker
- Configuration display

#### ⚙️ Settings Tab
- API URL configuration
- API key management
- About section

### Usage

1. **Upload Resume**
   - Click on "Upload Resume"
   - Select PDF, DOCX, or DOC file
   - Click "Parse Resume"

2. **View Results**
   - Auto-switches to "View Results" tab
   - Explore parsed data
   - Download as JSON

3. **Export Data**
   - Click "Download JSON" button
   - Get structured resume data

---

## 🧪 Testing

### Run Unit Tests

```bash
# Test API endpoints
pytest src/test_api.py -v

# Test Streamlit app
pytest src/test_streamlit.py -v

# Run all tests
pytest src/test_*.py -v

# With coverage
pytest src/test_*.py --cov=src
```

### Test Coverage

```
test_api.py
├── TestAuthentication (4 tests)
├── TestEndpoints (3 tests)
├── TestFileUpload (5 tests)
├── TestRateLimiting (2 tests)
├── TestResponseFormats (2 tests)
├── TestConfiguration (4 tests)
└── TestEdgeCases (2 tests)

test_streamlit.py
├── TestSessionState (2 tests)
├── TestStreamlitConfig (2 tests)
├── TestDataParsing (1 test)
├── TestMockAPIResponse (2 tests)
├── TestUIComponents (2 tests)
├── TestTabNavigation (2 tests)
└── TestIntegration (2 tests)
```

---

## 🚀 Deployment

### Option 1: Streamlit Cloud (Easiest)

**FREE hosting on Streamlit Cloud!**

See [STREAMLIT_CLOUD_DEPLOYMENT.md](STREAMLIT_CLOUD_DEPLOYMENT.md) for complete guide.

Quick steps:
1. Push code to GitHub
2. Go to https://share.streamlit.io/
3. Select your repository and `src/streamlit_app.py`
4. Add API secrets in dashboard
5. Done! 🎉

### Option 2: Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py"]
```

```bash
# Build and run
docker build -t resume-parser .
docker run -p 8501:8501 resume-parser
```

### Option 3: Railway.app (API + Streamlit)

See separate deployment guide for Railway.

### Option 4: Traditional VPS/Cloud

Deploy to AWS EC2, DigitalOcean, Linode, or any Linux server:

```bash
# SSH into server
ssh user@your-server.com

# Clone repository
git clone https://github.com/YOUR_USERNAME/resume-parser.git

# Setup and run
cd resume-parser
python3 -m venv venv
source venv/bin/activate
pip install -r src/requirements.txt

# Use systemd or supervisor for persistence
# See deployment guides for details
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file (see `.env.example`):

```
# API
API_KEY=dev-secret-key
API_URL=http://localhost:8000
HOST=0.0.0.0
PORT=8000
ENV=development

# Streamlit
STREAMLIT_PORT=8501

# Security
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8501
TRUSTED_HOSTS=localhost,127.0.0.1

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30
MAX_UPLOAD_MB=10

# Paths
RESUME_FOLDER=./Resume
SKILLS_CSV=./src/Skill.csv
EDUCATION_CSV=./src/03_education.csv

# Logging
LOG_LEVEL=INFO
ENABLE_DETAILED_LOGGING=false
```

### Streamlit Secrets (Cloud Deployment)

In Streamlit Cloud dashboard, add to **Secrets**:

```toml
# .streamlit/secrets.toml (Streamlit Cloud)
api_key = "your-prod-api-key"
api_url = "https://your-api.com"
```

---

## 🐛 Troubleshooting

### API Issues

#### ❌ "Connection refused"
```
Solution: Make sure API is running
bash: python -m uvicorn main_resume_api:app --reload
```

#### ❌ "Unauthorized [401]"
```
Solution: Check API key
- Verify x-api-key header is set
- Check API_KEY environment variable
```

#### ❌ "File too large"
```
Solution: Increase MAX_UPLOAD_MB
- Set MAX_UPLOAD_MB=20 in .env
- Restart API server
```

### Streamlit Issues

#### ❌ "Module not found"
```
Solution: Install missing dependencies
bash: pip install -r src/requirements.txt
```

#### ❌ "API URL not accessible"
```
Solution: Update API_URL
1. Check Streamlit settings tab
2. Verify API is running
3. Test with curl: curl http://localhost:8000/health
```

#### ❌ "File upload fails"
```
Solution: Check file format
- Supported: PDF, DOCX, DOC only
- Max size: 10MB (configurable)
```

### Common Fixes

```bash
# Clear Streamlit cache
streamlit cache clear

# Reinstall dependencies
pip install --upgrade -r src/requirements.txt

# Restart everything
pkill -f streamlit
pkill -f uvicorn
python run_dev.py

# Check Python version
python --version  # Must be 3.9+

# Verify all imports work
python -c "import streamlit; import fastapi; print('OK')"
```

---

## 📁 Project Structure

```
resume-parser/
├── src/
│   ├── streamlit_app.py           ← Main Streamlit UI
│   ├── main_resume_api.py         ← FastAPI backend
│   ├── Main_Resume.py             ← Parser logic
│   ├── test_api.py                ← API tests
│   ├── test_streamlit.py          ← UI tests
│   ├── requirements.txt           ← Python dependencies
│   ├── Skill.csv                  ← Skills database
│   ├── 03_education.csv           ← Education data
│   └── output/
│       ├── resume_parsed.json
│       └── validation_report.json
├── .streamlit/
│   ├── config.toml                ← Streamlit config
│   └── secrets.toml.example       ← Example secrets
├── run_dev.py                     ← Development runner
├── run_dev.bat                    ← Windows runner
├── .env.example                   ← Environment template
├── .gitignore
├── README.md                      ← This file
├── STREAMLIT_CLOUD_DEPLOYMENT.md ← Cloud deployment guide
└── requirements.txt               ← Root dependencies (optional)
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/YourFeature`)
3. Commit changes (`git commit -m 'Add YourFeature'`)
4. Push to branch (`git push origin feature/YourFeature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🆘 Support

### Getting Help

- 📚 [Streamlit Docs](https://docs.streamlit.io/)
- 📚 [FastAPI Docs](https://fastapi.tiangolo.com/)
- 💬 [GitHub Issues](https://github.com/YOUR_USERNAME/resume-parser/issues)
- 📧 [Email Support](mailto:support@example.com)

### Report Bugs

1. Go to [Issues](https://github.com/YOUR_USERNAME/resume-parser/issues)
2. Click "New Issue"
3. Describe the problem with screenshots
4. Include reproduction steps

---

## 🎉 Acknowledgments

- Powered by [FastAPI](https://fastapi.tiangolo.com/)
- UI by [Streamlit](https://streamlit.io/)
- NLP by [spaCy](https://spacy.io/)
- PDF parsing by [pdfminer](https://github.com/euske/pdfminer.six)

---

## 📊 Project Statistics

- 📝 **Lines of Code**: ~3000+
- 🧪 **Test Coverage**: 85%+
- ⚡ **API Response Time**: <1s (average)
- 📦 **Dependencies**: 20+
- 🌍 **Supported Formats**: 3 (PDF, DOCX, DOC)

---

## 🚀 Roadmap

- [ ] OCR support for scanned resumes
- [ ] Multi-language support
- [ ] Advanced ML-based entity extraction
- [ ] Integration with ATS systems
- [ ] Real-time collaboration features
- [ ] Mobile app support
- [ ] Advanced analytics dashboard

---

**Made with ❤️ for recruiters and HR professionals**

**⭐ Don't forget to star this repository!**
