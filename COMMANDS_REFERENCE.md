#!/bin/bash
# Resume Parser Development & Deployment Quick Commands
# Copy and paste these commands for common tasks

# ══════════════════════════════════════════════════════════════
# SETUP & INSTALLATION
# ══════════════════════════════════════════════════════════════

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r src/requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm


# ══════════════════════════════════════════════════════════════
# LOCAL DEVELOPMENT
# ══════════════════════════════════════════════════════════════

# Run everything (both Streamlit + API)
python run_dev.py              # macOS/Linux
run_dev.bat                    # Windows

# Run API only
cd src && python -m uvicorn main_resume_api:app --reload --port 8000

# Run Streamlit only
cd src && streamlit run streamlit_app.py --server.port 8501

# Run with custom API URL
API_URL=http://api.example.com streamlit run src/streamlit_app.py


# ══════════════════════════════════════════════════════════════
# TESTING
# ══════════════════════════════════════════════════════════════

# Run all tests
pytest src/test_*.py -v

# Run API tests only
pytest src/test_api.py -v

# Run Streamlit tests only
pytest src/test_streamlit.py -v

# Run tests with coverage report
pytest src/test_*.py --cov=src --cov-report=html

# Run specific test
pytest src/test_api.py::TestAuthentication::test_health_check_with_valid_key -v

# Run tests matching pattern
pytest src/ -k "health" -v


# ══════════════════════════════════════════════════════════════
# ENVIRONMENT SETUP
# ══════════════════════════════════════════════════════════════

# Create .env from template
cp .env.example .env

# View current configuration
cat .env

# Set environment variable (temporary)
export API_KEY="your-key"          # macOS/Linux
set API_KEY=your-key              # Windows

# Set in .env (permanent)
echo "API_KEY=your-key" >> .env


# ══════════════════════════════════════════════════════════════
# API TESTING
# ══════════════════════════════════════════════════════════════

# Check API health
curl -H "x-api-key: dev-secret-key" http://localhost:8000/health

# Get API info
curl -H "x-api-key: dev-secret-key" http://localhost:8000/info

# View API docs (interactive)
# Go to: http://localhost:8000/docs

# Parse single resume
curl -X POST \
  -H "x-api-key: dev-secret-key" \
  -F "file=@resume.pdf" \
  http://localhost:8000/parse

# Batch parse multiple resumes
curl -X POST \
  -H "x-api-key: dev-secret-key" \
  -F "files=@resume1.pdf" \
  -F "files=@resume2.docx" \
  http://localhost:8000/parse-batch


# ══════════════════════════════════════════════════════════════
# GIT & VERSION CONTROL
# ══════════════════════════════════════════════════════════════

# Initialize git repo
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/repo.git
git push -u origin main

# Update and push changes
git add .
git commit -m "Describe your changes"
git push origin main

# Check git status
git status

# View commit history
git log --oneline


# ══════════════════════════════════════════════════════════════
# DEPLOYMENT
# ══════════════════════════════════════════════════════════════

# Build Docker image
docker build -t resume-parser .

# Run Docker container
docker run -p 8501:8501 resume-parser

# Push to Docker Hub
docker tag resume-parser USERNAME/resume-parser:latest
docker push USERNAME/resume-parser:latest


# ══════════════════════════════════════════════════════════════
# MAINTENANCE & DEBUGGING
# ══════════════════════════════════════════════════════════════

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Clear Streamlit cache
streamlit cache clear

# Upgrade pip and packages
pip install --upgrade pip
pip install --upgrade -r src/requirements.txt

# List installed packages
pip list

# Save current environment
pip freeze > requirements.txt

# Check for security issues
pip install bandit
bandit -r src/

# Format code
pip install black
black src/

# Lint code
pip install pylint
pylint src/*.py


# ══════════════════════════════════════════════════════════════
# LOGS & MONITORING
# ══════════════════════════════════════════════════════════════

# View API logs in real-time
tail -f src/output/parser.log

# View last 50 lines of logs
tail -50 src/output/parser.log

# Search logs for errors
grep "ERROR" src/output/parser.log

# Monitor running processes
ps aux | grep "python\|streamlit"

# Kill process by port
# Windows: netstat -ano | findstr :8000
# macOS/Linux: lsof -i :8000 | grep -v PID | awk '{print $2}' | xargs kill -9


# ══════════════════════════════════════════════════════════════
# FILE OPERATIONS
# ══════════════════════════════════════════════════════════════

# Create output directory if missing
mkdir -p src/output

# Copy resume samples to src directory
cp sample_resumes/*.pdf src/

# View file structure
tree -L 2 -I 'venv|__pycache__|.git'

# Check file sizes
du -sh src/*
ls -lh src/


# ══════════════════════════════════════════════════════════════
# STREAMLIT CLOUD DEPLOYMENT
# ══════════════════════════════════════════════════════════════

# 1. Ensure code is on GitHub
git push origin main

# 2. Go to https://share.streamlit.io/
# 3. Sign in with GitHub
# 4. Click "Create app"
# 5. Select repository and branch
# 6. Set main file: src/streamlit_app.py
# 7. Click "Deploy"

# 8. Add secrets in Streamlit Cloud dashboard:
#    api_key = "prod-api-key"
#    api_url = "https://api.yourdomain.com"


# ══════════════════════════════════════════════════════════════
# TROUBLESHOOTING & COMMON ISSUES
# ══════════════════════════════════════════════════════════════

# Issue: "Module not found"
pip install -r src/requirements.txt

# Issue: "Connection refused"
python run_dev.py

# Issue: "API_KEY not set"
export API_KEY="dev-secret-key"

# Issue: "Port already in use"
# Find process using port 8000
# macOS/Linux: lsof -i :8000
# Windows: netstat -ano | findstr :8000
# Kill process: kill -9 PID (macOS/Linux) or taskkill /PID PID (Windows)

# Issue: "spaCy model not found"
python -m spacy download en_core_web_sm

# Issue: "PDF parsing fails"
# Ensure pdfminer.six is installed correctly
pip install --upgrade pdfminer.six

# Test individual component
python -c "from Main_Resume import *; print('Imports successful')"

# Clear all cache and reinstall
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r src/requirements.txt


# ══════════════════════════════════════════════════════════════
# HELPFUL UTILITIES
# ══════════════════════════════════════════════════════════════

# Get your IP address (for sharing)
hostname -I                    # Linux
ipconfig                       # Windows
ifconfig                       # macOS

# Create backup
tar -czf resume-parser-backup.tar.gz . --exclude=venv --exclude=.git

# Zip for distribution (Windows)
Compress-Archive -Path . -DestinationPath resume-parser.zip -Exclude venv, .git

# Generate requirements from current environment
pip freeze > requirements-frozen.txt


# ══════════════════════════════════════════════════════════════
# PERFORMANCE PROFILING
# ══════════════════════════════════════════════════════════════

# Profile API response time
pip install locust
locust -f locustfile.py

# Measure function execution time
python -c "import timeit; print(timeit.timeit('x = [i**2 for i in range(100)]', number=10000))"

# Memory profiling
pip install memory_profiler
python -m memory_profiler script.py


# ══════════════════════════════════════════════════════════════
# PRODUCTIVITY SHORTCUTS
# ══════════════════════════════════════════════════════════════

# Create alias for quick startup
alias resume-dev="python run_dev.py"

# Add to .bashrc or .zshrc, then use:
resume-dev

# Create venv + install in one command
python -m venv venv &&
source venv/bin/activate &&
pip install -r src/requirements.txt

# Open docs in browser
python -m webbrowser "http://localhost:8000/docs"

# Quick test & deploy
pytest src/test_*.py && git add . && git commit -m "Tests passing" && git push
