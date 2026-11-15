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
    import uvicorn
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
        reload=False,
        log_level="info",
    )

