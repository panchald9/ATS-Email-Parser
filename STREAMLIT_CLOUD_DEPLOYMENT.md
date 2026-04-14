# Resume Parser - Streamlit Cloud Deployment Guide

This guide provides step-by-step instructions to deploy the Resume Parser Streamlit app to Streamlit Cloud (https://share.streamlit.io/).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Prepare Your Repository](#prepare-your-repository)
3. [Deploy to Streamlit Cloud](#deploy-to-streamlit-cloud)
4. [Configure Secrets](#configure-secrets)
5. [Monitor & Manage](#monitor--manage)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, you'll need:

- ✅ GitHub account (free at https://github.com)
- ✅ Streamlit Cloud account (free at https://share.streamlit.io/)
- ✅ This project pushed to a GitHub repository
- ✅ Running instance of the Resume Parser API (or know the API URL)

---

## Prepare Your Repository

### 1. Create/Update GitHub Repository

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Make initial commit
git commit -m "Initial commit: Resume Parser Streamlit App"

# Add GitHub remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/your-repo-name.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 2. Create `.gitignore` (if not exists)

```bash
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# Streamlit
.streamlit/secrets.toml
.streamlit/uploads

# Output
output/
logs/

# OS
.DS_Store
Thumbs.db
```

### 3. Verify File Structure

Ensure your repository has this structure:

```
your-repo/
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── src/
│   ├── streamlit_app.py          ← Main app
│   ├── main_resume_api.py        ← Optional (if deploying API too)
│   ├── Main_Resume.py
│   ├── requirements.txt          ← REQUIRED
│   ├── Skill.csv
│   ├── 03_education.csv
│   └── ...other files
├── .gitignore
├── README.md
├── requirements.txt              ← Root level (optional)
└── .github/
    └── workflows/               ← Optional: CI/CD
```

### 4. Create/Update Root `requirements.txt`

If you don't have a root `requirements.txt`, create one that mirrors `src/requirements.txt`:

```bash
# Copy from src to root
cp src/requirements.txt requirements.txt
```

---

## Deploy to Streamlit Cloud

### Step 1: Sign Up/Login to Streamlit Cloud

1. Visit https://share.streamlit.io/
2. Click **"Sign up with GitHub"** or login with your GitHub account
3. Allow Streamlit to access your GitHub repositories

### Step 2: Create New App

1. Click **"Create app"** button
2. Select your GitHub repository
3. Select the branch (usually `main`)
4. Set the main file path: `src/streamlit_app.py`

### Step 3: Configure Settings

On the app creation screen:

- **Repository**: Select your repo
- **Branch**: `main`
- **Main file path**: `src/streamlit_app.py`
- Click **"Deploy"**

Streamlit will now:
- ✅ Clone your repository
- ✅ Install dependencies from `src/requirements.txt`
- ✅ Launch your Streamlit app

**Your app URL will be:** `https://share.streamlit.io/YOUR_USERNAME/your-repo-name/src/streamlit_app.py`

---

## Configure Secrets

Your Streamlit app needs API credentials. Add them securely:

### Step 1: Access App Settings

1. Go to your deployed app dashboard
2. Click the **three dots** (⋯) in the top right
3. Select **"Settings"** → **"Secrets"**

### Step 2: Add Secrets

Add your API configuration in the Secrets editor:

```toml
# Resume Parser API Configuration
api_key = "dev-secret-key"
api_url = "https://your-resume-parser-api.com"

# Or if hosting locally, use your domain
# api_url = "https://api.yourdomain.com"
```

### Step 3: Update Streamlit App

Modify `streamlit_app.py` to use secrets:

```python
import streamlit as st

# Read from Streamlit secrets
if "api_key" in st.secrets:
    API_KEY = st.secrets["api_key"]
else:
    API_KEY = "dev-secret-key"

if "api_url" in st.secrets:
    API_URL = st.secrets["api_url"]
else:
    API_URL = "http://localhost:8000"
```

The app already has this logic at the top! Just add your secrets in Streamlit Cloud.

---

## Advanced: Deploy API Alongside (Optional)

If you want to deploy the API to the cloud too, consider:

### Option 1: Use Railway.app (Recommended)
- https://railway.app/
- Free tier available
- Easy Python deployments
- Simple environment variable management

### Option 2: Use Heroku
- https://www.heroku.com/
- Free tier deprecated, but plan options available
- Can `Procfile` for Python

### Option 3: Use AWS, GCP, or Azure
- More complex setup
- Better for production
- Cost varies

**For Testing:** You can temporarily expose your local API:
```bash
# Install ngrok: https://ngrok.com/
ngrok http 8000

# Use the provided URL in Streamlit Cloud secrets:
# api_url = "https://abc123.ngrok.io"
```

---

## Monitor & Manage

### View Logs

1. Go to your app on Streamlit Cloud
2. Click **three dots** (⋯) → **"View logs"**
3. View real-time logs of your running app

### Redeploy

Changes are automatically redeployed when you push to GitHub:

```bash
git add .
git commit -m "Fix: update API endpoint"
git push origin main

# Streamlit Cloud will automatically detect and redeploy
```

### Usage Analytics

1. Go to app dashboard
2. Click **"Analytics"** tab
3. View:
   - User sessions
   - Page views
   - Performance metrics

---

## Troubleshooting

### ❌ "requirements.txt not found"

**Solution:** Ensure `requirements.txt` exists in `src/` directory or root

```bash
# Check if it exists
ls src/requirements.txt        # Should exist

# If not, create it from scratch
pip freeze > requirements.txt
```

### ❌ "Import error for Main_Resume"

**Solutions:**

1. Ensure all dependencies are in `requirements.txt`
2. Check that all CSV files (Skill.csv, 03_education.csv) are committed to GitHub
3. Add diagnostic logging:

```python
import sys
print(sys.path)
print(os.listdir('.'))
```

### ❌ "API Connection Failed"

**Check:**

1. ✅ API URL is correct in secrets
2. ✅ API is actually running and accessible
3. ✅ API key is correct
4. ✅ CORS is enabled on API
5. ✅ No firewall blocking requests

**Test Connection:**
```python
import requests
try:
    r = requests.get("https://your-api-url/health", 
                     headers={"x-api-key": API_KEY})
    st.write(f"API Status: {r.status_code}")
except Exception as e:
    st.error(f"Connection failed: {e}")
```

### ❌ "File size limit exceeded"

**Issue:** Streamlit Cloud has a 1GB limit

**Solutions:**
1. Compress large files
2. Remove unnecessary data files
3. Use external storage (S3, etc.)

### ❌ "Timeout during deployment"

**Solutions:**
1. Reduce large dependencies
2. Check internet connection
3. Wait a few minutes and retry
4. Contact Streamlit Cloud support

---

## Example Deployment Workflow

```bash
# 1. Make changes locally
nano src/streamlit_app.py

# 2. Test locally
streamlit run src/streamlit_app.py

# 3. Commit changes
git add src/streamlit_app.py
git commit -m "Add new feature"

# 4. Push to GitHub
git push origin main

# 5. Streamlit Cloud automatically redeploys!
# Visit your app URL to see the changes
```

---

## Performance Tips

### 1. Cache Data
```python
@st.cache_data
def load_resume_parser():
    return Main_Resume.load_parser()
```

### 2. Lazy Load Heavy Dependencies
```python
if should_use_feature:
    import heavy_lib  # Only import when needed
```

### 3. Optimize File Uploads
```python
st.file_uploader("Upload resume", type=["pdf", "docx", "doc"])
```

### 4. Use Session State Wisely
```python
if "cache" not in st.session_state:
    st.session_state.cache = {}
```

---

## Example `.github/workflows/deploy.yml` (Optional)

For automated testing before deployment:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r src/requirements.txt
      - run: pip install pytest
      - run: pytest src/test_*.py
```

---

## Support & Resources

- 📖 Streamlit Docs: https://docs.streamlit.io/
- 🐛 Report Issues: https://github.com/streamlit/streamlit/issues
- 💬 Community Forum: https://discuss.streamlit.io/
- 🆘 Streamlit Support: https://docs.streamlit.io/library/get-help

---

## Summary

✅ **Your Resume Parser is now live on Streamlit Cloud!**

- 🔗 Access your app at: `https://share.streamlit.io/YOUR_USERNAME/your-repo/src/streamlit_app.py`
- 🔒 Secrets stored securely
- 🔄 Auto-deploys on GitHub push
- 📊 View analytics and logs
- 🎯 Share with colleagues/clients

Happy deploying! 🚀
