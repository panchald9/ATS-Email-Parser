"""
High-concurrency server launcher for Resume Parser API.
Configures Uvicorn server with multi-worker execution and high connection backlog for 1200+ concurrent requests.
"""

import os
import multiprocessing
import uvicorn


def main():
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    # Calculate optimal worker count based on CPU cores
    default_workers = max(2, multiprocessing.cpu_count())
    workers = int(os.getenv("API_WORKERS", str(default_workers)))
    
    # Backlog queue size for TCP connection handshakes during request bursts
    backlog = int(os.getenv("API_BACKLOG", "2048"))
    
    print("=" * 60)
    print("Starting Resume Parser API Server (High Concurrency Mode)")
    print(f" Listening on : http://{host}:{port}")
    print(f" Workers      : {workers}")
    print(f" TCP Backlog  : {backlog}")
    print("=" * 60)

    uvicorn.run(
        "main_resume_api:app",
        host=host,
        port=port,
        workers=workers,
        backlog=backlog,
        loop="auto",
        http="auto",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
