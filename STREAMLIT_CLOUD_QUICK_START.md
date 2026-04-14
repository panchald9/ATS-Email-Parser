"""
Quick Start Guide - Deploy Resume Parser to Streamlit Cloud
Complete step-by-step guide with screenshots and commands
"""

# ══════════════════════════════════════════════════════════════
# STEP 1: Prepare GitHub Repository
# ══════════════════════════════════════════════════════════════

# 1. Push code to GitHub (if not already done)
cd /your/project/path
git init
git add .
git commit -m "Initial: Resume Parser with Streamlit UI"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/resume-parser.git
git push -u origin main

# 2. Verify the file structure on GitHub:
#    ├── src/
#    │   ├── streamlit_app.py           ← Main entry point
#    │   ├── main_resume_api.py
#    │   ├── Main_Resume.py
#    │   ├── requirements.txt           ← MUST EXIST
#    │   ├── Skill.csv
#    │   ├── 03_education.csv
#    │   └── ...
#    ├── .streamlit/
#    │   └── config.toml
#    ├── README.md
#    └── .gitignore


# ══════════════════════════════════════════════════════════════
# STEP 2: Create Streamlit Cloud Account
# ══════════════════════════════════════════════════════════════

# 1. Go to: https://share.streamlit.io/
# 2. Click "Sign up with GitHub"
# 3. Authorize Streamlit to access your GitHub account
# 4. You're now logged in!


# ══════════════════════════════════════════════════════════════
# STEP 3: Deploy Your App
# ══════════════════════════════════════════════════════════════

# 1. On Streamlit Cloud dashboard, click "Create app"
# 2. Fill in deployment form:
#    - Repository: YOUR_USERNAME/resume-parser (or your repo)
#    - Branch: main
#    - Main file path: src/streamlit_app.py
# 3. Click "Deploy"
# 
# Streamlit will now:
# ✅ Clone your repository
# ✅ Install packages from requirements.txt
# ✅ Start your app
#
# Your app URL: https://share.streamlit.io/YOUR_USERNAME/resume-parser/src/streamlit_app.py


# ══════════════════════════════════════════════════════════════
# STEP 4: Add Secrets (API Configuration)
# ══════════════════════════════════════════════════════════════

# After deployment completes:
# 
# 1. Go to your app dashboard
# 2. Click the three dots (⋯) in top right
# 3. Select "Settings"
# 4. Click "Secrets" tab
# 5. Add your API configuration:

# Add this to the Secrets editor:
"""
api_key = "dev-secret-key"
api_url = "https://your-resume-parser-api.com"

# Or for local testing:
# api_url = "http://localhost:8000"
"""

# 6. Save and your app will auto-redeploy


# ══════════════════════════════════════════════════════════════
# STEP 5: Make Changes & Auto-Deploy
# ══════════════════════════════════════════════════════════════

# After your initial deployment, you can update your app by pushing
# changes to GitHub. Streamlit Cloud will automatically redeploy!

# Workflow:
# 1 Make code changes locally
# 2. Test locally: streamlit run src/streamlit_app.py
# 3. Commit and push: git push origin main
# 4. Streamlit automatically redeploys (give it ~30 seconds)
# 5. Visit your app URL to see changes


# ══════════════════════════════════════════════════════════════
# IMPORTANT: Handling API Connectivity
# ══════════════════════════════════════════════════════════════

# Your Streamlit app running on the cloud needs to connect to
# your Resume Parser API. You have several options:

# Option A: Deploy API Separately
# ────────────────────────────────
# 1. Deploy API to a service (Railway, AWS, Heroku, etc.)
# 2. Get the API URL (e.g., https://my-api.railway.app)
# 3. Add to Streamlit secrets:
#    api_url = "https://my-api.railway.app"
# 4. Your Streamlit Cloud app can now reach the API

# Option B: Use ngrok for Testing (NOT for production)
# ──────────────────────────────────────────────────
# 1. Install ngrok: https://ngrok.com/download
# 2. Start your API locally: 
#    python -m uvicorn main_resume_api:app --port 8000
# 3. In another terminal, expose it:
#    ngrok http 8000
# 4. Copy the ngrok URL (e.g., https://abc123.ngrok.io)
# 5. Add to Streamlit secrets:
#    api_url = "https://abc123.ngrok.io"

# Option C: Deploy API to Railway.app (Recommended for simple setup)
# ──────────────────────────────────────────────────────────────────
# See RAILWAY_DEPLOYMENT.md


# ══════════════════════════════════════════════════════════════
# TROUBLESHOOTING COMMON ISSUES
# ══════════════════════════════════════════════════════════════

# ❌ "requirements.txt not found"
# Solution: Ensure requirements.txt exists in src/ directory
#           Check GitHub repository structure
#           Make sure it's committed and pushed to main branch

# ❌ "ModuleNotFoundError: No module named 'main_resume_api'"
# Solution: Import might be wrong in streamlit_app.py
#           Update import path if needed

# ❌ "API connection failed"
# Solution: Check API secrets are set correctly
#           Verify API is actually running
#           Test with curl: curl -H "x-api-key: YOUR_KEY" https://api-url/health

# ❌ "File upload fails silently"
# Solution: Check Streamlit Cloud logs (⋯ → View logs)
#           Verify file size < 10MB (configurable in API)
#           Try different resume format

# ❌ "Secrets not working"
# Solution: Restart app after adding secrets
#           Verify secret names match your code
#           Check secret values don't have trailing spaces

# ❌ "App takes forever to load"
# Solution: Optimize heavy imports (use @st.cache_data)
#           Reduce package dependencies
#           Use faster parsing methods


# ══════════════════════════════════════════════════════════════
# MONITORING YOUR DEPLOYED APP
# ══════════════════════════════════════════════════════════════

# View Logs
# 1. Go to your app dashboard
# 2. Click ⋯ (three dots)
# 3. Select "View logs"
# 4. See real-time logs of app

# View Analytics
# 1. Click "Analytics" tab on dashboard
# 2. See engagement metrics:
#    - Active users
#    - Sessions
#    - Page views
#    - Performance data

# Redeploy Manually
# 1. Click ⋯ (three dots)
# 2. Select "Reboot app"
# (Usually not needed - happens automatically on git push)


# ══════════════════════════════════════════════════════════════
# EXAMPLES: Real-World Deployment Scenarios
# ══════════════════════════════════════════════════════════════

# Scenario 1: Complete Cloud Deployment
# ──────────────────────────────────────
# Goal: Everything on cloud (Streamlit + API)
#
# Steps:
# 1. Deploy Streamlit app to share.streamlit.io ✓ (you're here)
# 2. Deploy API to Railway.app:
#    - git push to GitHub
#    - Railway auto-deploys
#    - Get Railway app URL
# 3. Add Railway URL to Streamlit secrets
# 4. Done! Fully cloud-hosted system
#
# Cost: Free tier available on both


# Scenario 2: Hybrid Deployment (Recommended for Development)
# ────────────────────────────────────────────────────────────
# Goal: Streamlit in cloud, API running locally for testing
#
# Steps:
# 1. Deploy Streamlit to share.streamlit.io ✓
# 2. Run API locally: python -m uvicorn main_resume_api:app --port 8000
# 3. Expose locally with ngrok: ngrok http 8000
# 4. Add ngrok URL to Streamlit secrets
# 5. Test changes instantly
#
# Best for: Development and testing


# Scenario 3: Enterprise Deployment
# ──────────────────────────────────
# Goal: Secure, scalable, production-ready
#
# Steps:
# 1. Deploy Streamlit to share.streamlit.io OR self-hosted
# 2. Deploy API to enterprise cloud (AWS, Azure, GCP)
# 3. Use environment-specific secrets
# 4. Implement logging and monitoring
# 5. Add SSL/TLS certificates
# 6. Set up backups and disaster recovery
#
# Best for: Production use with many users


# ══════════════════════════════════════════════════════════════
# NEXT STEPS AFTER DEPLOYMENT
# ══════════════════════════════════════════════════════════════

# 1. Share your app link with others
#    https://share.streamlit.io/YOUR_USERNAME/resume-parser/src/streamlit_app.py

# 2. Add to portfolio/resume
#    "Deployed AI-powered Resume Parser using Streamlit Cloud"

# 3. Monitor usage and logs
#    Check Streamlit Cloud dashboard regularly

# 4. Iterate and improve
#    Make changes locally, push to GitHub
#    Streamlit auto-deploys in ~30 seconds

# 5. Scale as needed
#    Move to self-hosted if you need more resources
#    Upgrade API hosting if needed


# ══════════════════════════════════════════════════════════════
# COST BREAKDOWN
# ══════════════════════════════════════════════════════════════

# Streamlit Cloud (Hosting Streamlit App)
# ├─ FREE tier: Perfect for development
# ├─ 1 GB per deployed app
# └─ Unlimited public apps

# Railway.app (Hosting API) - RECOMMENDED
# ├─ FREE tier: $5/month included
# ├─ Includes runs, storage, bandwidth
# └─ Very beginner friendly

# Alternative APIs Hosting:
# • Heroku: Deprecated free tier, ~$7/month
# • AWS Lambda: ~$0.20 per 1M requests
# • DigitalOcean App Platform: ~$5-12/month
# • Azure App Service: ~$5-20/month

# TOTAL COST: $0-5/month (can be free!)


# ══════════════════════════════════════════════════════════════
# QUICK REFERENCE: Important Links
# ══════════════════════════════════════════════════════════════

# 🚀 Deployment:
# - Streamlit Cloud: https://share.streamlit.io/
# - Railway.app: https://railway.app/
# - GitHub: https://github.com/

# 📚 Documentation:
# - Streamlit Docs: https://docs.streamlit.io/
# - FastAPI Docs: https://fastapi.tiangolo.com/
# - Railway Docs: https://docs.railway.app/

# 🆘 Support:
# - Streamlit Community: https://discuss.streamlit.io/
# - FastAPI Discussions: https://github.com/tiangolo/fastapi/discussions
# - Railway Support: https://railway.app/support


# ══════════════════════════════════════════════════════════════
# COMMON GIT COMMANDS DURING DEPLOYMENT
# ══════════════════════════════════════════════════════════════

# After making changes locally and want to redeploy:
git status              # See what changed
git add .               # Stage changes
git commit -m "Update: add new feature"  # Commit
git push origin main    # Push to GitHub

# Streamlit will auto-detect the change and redeploy!
# Wait ~30 seconds for deployment to complete
# Refresh app URL to see changes

# View deployment history:
git log --oneline

# Compare changes:
git diff


# ══════════════════════════════════════════════════════════════
# YOU'RE DONE! 🎉
# ══════════════════════════════════════════════════════════════

# Your Resume Parser is now live and accessible to anyone!
# 
# Next: Deploy the API to a cloud service for full automation.
# See RAILWAY_DEPLOYMENT.md or choose your preferred platform.
#
# Questions? Check the main README.md or STREAMLIT_CLOUD_DEPLOYMENT.md
