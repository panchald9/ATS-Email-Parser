#!/usr/bin/env python
"""
Resume Parser - Development Server Runner
Starts both the FastAPI backend and Streamlit frontend
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Load environment variables

env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    print("⚠️  .env file not found. Creating from .env.example...")
    example_path = Path(__file__).parent / ".env.example"
    if example_path.exists():
        import shutil
        shutil.copy(example_path, env_path)
        print(f"✅ Created .env at {env_path}")
    else:
        print("❌ .env.example not found either")

load_dotenv(env_path)

import argparse

# ──────────────────────────────────────────────────────────────
# Configuration & CLI Arguments
# ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Resume Parser Development / Production Server Runner")
    parser.add_argument("--workers", type=int, default=int(os.getenv("WORKERS", "1")), help="Number of API worker processes for high concurrency")
    parser.add_argument("--limit-concurrency", type=int, default=int(os.getenv("LIMIT_CONCURRENCY", "1000")), help="Maximum concurrent connections allowed per worker")
    parser.add_argument("--prod", action="store_true", help="Run in high-throughput production mode (multi-worker, no reload)")
    parser.add_argument("--no-streamlit", action="store_true", help="Skip launching Streamlit app (API only)")
    return parser.parse_args()

args = parse_args() if __name__ == "__main__" else argparse.Namespace(workers=1, limit_concurrency=1000, prod=False, no_streamlit=False)

API_HOST = os.getenv("API_HOST", os.getenv("HOST", "127.0.0.1"))
API_PORT = int(os.getenv("PORT", "8000"))
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
SRC_DIR = Path(__file__).parent / "src"
WORKERS = args.workers if args.prod or args.workers > 1 else int(os.getenv("WORKERS", "1"))
LIMIT_CONCURRENCY = args.limit_concurrency
USE_RELOAD = not (args.prod or WORKERS > 1)


# ──────────────────────────────────────────────────────────────
# Utility Functions
# ──────────────────────────────────────────────────────────────
def print_banner():
    """Print startup banner"""
    mode = "PRODUCTION (High-Concurrency)" if (args.prod or WORKERS > 1) else "DEVELOPMENT"
    print("\n" + "="*60)
    print(f"🚀 Resume Parser - {mode} Server")
    print("="*60)
    print(f"📁 Working directory:    {Path.cwd()}")
    print(f"🔧 Source directory:     {SRC_DIR}")
    print(f"📊 API Host & Port:      http://{API_HOST}:{API_PORT}")
    print(f"⚡ API Workers:          {WORKERS} process(es)")
    print(f"🔥 Max Concurrency:      {LIMIT_CONCURRENCY} concurrent requests")
    if not args.no_streamlit:
        print(f"🎨 Streamlit App:        http://localhost:{STREAMLIT_PORT}")
    print("="*60 + "\n")


def start_api():
    """Start FastAPI server"""
    print(f"🔌 Starting API server ({WORKERS} worker(s), concurrency limit: {LIMIT_CONCURRENCY})...")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main_resume_api:app",
        f"--host={API_HOST}",
        f"--port={API_PORT}",
        f"--limit-concurrency={LIMIT_CONCURRENCY}",
    ]
    
    if USE_RELOAD:
        cmd.append("--reload")
    else:
        cmd.extend(["--workers", str(WORKERS)])
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)
    
    try:
        return subprocess.Popen(
            cmd,
            cwd=str(SRC_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
    except Exception as e:
        print(f"❌ Failed to start API: {e}")
        return None



def start_streamlit():
    """Start Streamlit app"""
    print("🎨 Starting Streamlit app...")
    time.sleep(2)  # Give API time to start
    
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(SRC_DIR / "streamlit_app.py"),
        f"--server.port={STREAMLIT_PORT}",
        "--server.headless=false",
        "--logger.level=info",
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)
    
    try:
        return subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")
        return None


def print_process_output(process, name):
    """Print process output in real-time"""
    if process and process.stdout:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{name}] {line.rstrip()}")


# ──────────────────────────────────────────────────────────────
# Signal Handlers
# ──────────────────────────────────────────────────────────────
def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("\n\n⏹️  Shutting down servers...")
    if api_process:
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
    
    if streamlit_process:
        streamlit_process.terminate()
        try:
            streamlit_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            streamlit_process.kill()
    
    print("✅ Servers stopped")
    sys.exit(0)


# ──────────────────────────────────────────────────────────────
# Main Execution
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print_banner()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start servers
    api_process = start_api()
    streamlit_process = None if args.no_streamlit else start_streamlit()
    
    if not api_process or (not args.no_streamlit and not streamlit_process):
        print("❌ Failed to start servers")
        sys.exit(1)
    
    print("\n✅ Server environment running!")
    print("\n📋 Quick Links:")
    print(f"   🔗 API Docs:        http://{API_HOST}:{API_PORT}/docs")
    if not args.no_streamlit:
        print(f"   🔗 Streamlit App:   http://localhost:{STREAMLIT_PORT}")
    print(f"   🔗 API Health:      http://{API_HOST}:{API_PORT}/health")
    print("\n📝 Press Ctrl+C to stop servers\n")
    
    # Monitor processes
    try:
        while True:
            if api_process and api_process.poll() is not None:
                print("❌ API process died")
                break
            if streamlit_process and streamlit_process.poll() is not None:
                print("⚠️  Streamlit process exited")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

