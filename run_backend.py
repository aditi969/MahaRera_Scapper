"""RERA INSIGHT - Backend Server Launcher.

Run this script from the project root:
    python run_backend.py
"""
import os
import sys
from pathlib import Path

# Add project root and backend directory to Python sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

if __name__ == "__main__":
    import socket
    import subprocess
    import time
    import uvicorn

    # Ensure port 8000 is free before starting
    for _ in range(5):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", 8000)) == 0:
                cmd = 'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :8000 ^| findstr LISTENING\') do taskkill /F /T /PID %a'
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
            else:
                break

    print("=" * 60)
    print("  RERA INSIGHT - Starting FastAPI Backend Server")
    print(f"  Project Root: {PROJECT_ROOT}")
    print(f"  Backend Dir:  {BACKEND_DIR}")
    print("  API Docs:     http://127.0.0.1:8000/docs")
    print("  Health Check: http://127.0.0.1:8000/api/health")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )

