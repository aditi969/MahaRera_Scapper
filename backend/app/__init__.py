"""RERA Insight backend application package."""
import os
import sys
from pathlib import Path

# Ensure both project root and backend directory are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
