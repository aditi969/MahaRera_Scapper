"""CAPTCHA Health Check & Operational Metrics Service.

Diagnoses OCR engine availability (Tesseract, OpenCV, Pillow),
performs real-time synthetic OCR self-tests, and aggregates operational metrics
(attempts, successes, rejections, solve rate) from scrape logs.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.models.models import ScrapeLog

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


def find_tesseract_path() -> Optional[str]:
    """Locate the Tesseract OCR executable on Windows and common paths."""
    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        shutil.which("tesseract") or "",
    ]
    for path in candidate_paths:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def get_tesseract_version(tesseract_cmd: Optional[str]) -> Optional[str]:
    """Retrieve Tesseract version by executing tesseract --version."""
    if not tesseract_cmd:
        return None
    try:
        res = subprocess.run(
            [tesseract_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = res.stdout or res.stderr
        match = re.search(r"tesseract\s+([0-9\.\w\-]+)", output, re.IGNORECASE)
        if match:
            return match.group(1)
        return output.splitlines()[0] if output else "Installed"
    except Exception:
        return None


def run_synthetic_ocr_test(tesseract_cmd: Optional[str]) -> Dict[str, Any]:
    """Generate a clean synthetic CAPTCHA image in memory and test OCR latency."""
    if not tesseract_cmd or not pytesseract or not Image:
        return {
            "executed": False,
            "passed": False,
            "latency_ms": 0.0,
            "error": "Tesseract, PyTesseract, or Pillow not available",
        }

    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        # Generate a clean high-contrast test image with known text
        test_text = "MAHA89"
        font = None
        font_candidates = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            r"C:\Windows\Fonts\consola.ttf",
            "arial.ttf",
        ]
        for fpath in font_candidates:
            try:
                font = ImageFont.truetype(fpath, 32)
                break
            except Exception:
                continue

        if not font:
            font = ImageFont.load_default()

        img = Image.new("L", (200, 60), color=255)
        draw = ImageDraw.Draw(img)
        draw.text((20, 12), test_text, fill=0, font=font)

        # Scale up with border padding to mirror real captcha solver preprocessing
        img_resized = img.resize((img.width * 2, img.height * 2), resample=Image.Resampling.NEAREST)

        start_time = time.perf_counter()

        # Custom config matching scraper/core/captcha.py
        tess_config = "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        recognized = pytesseract.image_to_string(img_resized, config=tess_config).strip().upper()
        clean_recognized = re.sub(r"[^A-Z0-9]", "", recognized)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        passed = (test_text == clean_recognized or test_text in clean_recognized)

        return {
            "executed": True,
            "passed": passed,
            "latency_ms": elapsed_ms,
            "test_expected": test_text,
            "test_recognized": clean_recognized,
            "error": None if passed else f"Recognized '{clean_recognized}' instead of '{test_text}'",
        }
    except Exception as e:
        return {
            "executed": True,
            "passed": False,
            "latency_ms": 0.0,
            "error": str(e),
        }


def get_captcha_operational_metrics(db: Session) -> Dict[str, Any]:
    """Aggregate real-time CAPTCHA operational metrics from scrape_logs."""
    try:
        # OCR attempts
        attempts_count = db.query(func.count(ScrapeLog.id)).filter(
            ScrapeLog.message.ilike("%Captcha OCR attempt%")
        ).scalar() or 0

        # Accepted captchas
        accepted_count = db.query(func.count(ScrapeLog.id)).filter(
            ScrapeLog.message.ilike("%Captcha accepted%")
        ).scalar() or 0

        # Rejected captchas
        rejected_count = db.query(func.count(ScrapeLog.id)).filter(
            ScrapeLog.message.ilike("%Invalid captcha%")
        ).scalar() or 0

        # Blocked captchas
        blocked_count = db.query(func.count(ScrapeLog.id)).filter(
            ScrapeLog.message.ilike("%CAPTCHA_BLOCKED%")
        ).scalar() or 0

        # Canvas refreshes
        refreshes_count = db.query(func.count(ScrapeLog.id)).filter(
            ScrapeLog.message.ilike("%Refreshing captcha%")
        ).scalar() or 0

        # Last attempt timestamp
        last_attempt = db.query(ScrapeLog.created_at).filter(
            ScrapeLog.message.ilike("%Captcha%")
        ).order_by(desc(ScrapeLog.created_at)).first()

        last_attempt_at = last_attempt[0].isoformat() if last_attempt and last_attempt[0] else None

        # Last solved timestamp
        last_solved = db.query(ScrapeLog.created_at).filter(
            ScrapeLog.message.ilike("%Captcha accepted%")
        ).order_by(desc(ScrapeLog.created_at)).first()

        last_solved_at = last_solved[0].isoformat() if last_solved and last_solved[0] else None

        # Solve rate calculation:
        # Total solved sessions vs (solved sessions + blocked sessions)
        total_sessions = accepted_count + blocked_count
        if total_sessions > 0:
            solve_rate = round((accepted_count / total_sessions) * 100, 1)
        elif accepted_count > 0:
            solve_rate = 100.0
        else:
            solve_rate = 100.0 if attempts_count == 0 else 0.0

        # Average attempts per successful solve
        avg_attempts = (
            round(attempts_count / accepted_count, 2)
            if accepted_count > 0
            else (round(attempts_count, 2) if attempts_count > 0 else 1.0)
        )

        # Recent 10 CAPTCHA events
        recent_logs = (
            db.query(ScrapeLog)
            .filter(
                or_(
                    ScrapeLog.message.ilike("%Captcha%"),
                    ScrapeLog.message.ilike("%CAPTCHA%"),
                )
            )
            .order_by(desc(ScrapeLog.created_at))
            .limit(10)
            .all()
        )

        recent_events = [
            {
                "id": log.id,
                "job_id": log.job_id,
                "level": log.level,
                "message": log.message,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
            }
            for log in recent_logs
        ]

        return {
            "total_attempts": attempts_count,
            "total_accepted": accepted_count,
            "total_rejected": rejected_count,
            "total_blocked": blocked_count,
            "total_refreshes": refreshes_count,
            "solve_rate_percent": solve_rate,
            "avg_attempts_per_solve": avg_attempts,
            "last_attempt_at": last_attempt_at,
            "last_solved_at": last_solved_at,
            "recent_events": recent_events,
        }
    except Exception as e:
        return {
            "total_attempts": 0,
            "total_accepted": 0,
            "total_rejected": 0,
            "total_blocked": 0,
            "total_refreshes": 0,
            "solve_rate_percent": 100.0,
            "avg_attempts_per_solve": 1.0,
            "last_attempt_at": None,
            "last_solved_at": None,
            "recent_events": [],
            "error": str(e),
        }


def check_captcha_health(db: Session, run_self_test: bool = True) -> Dict[str, Any]:
    """Perform a complete health check of the CAPTCHA OCR subsystem and return operational metrics."""
    tess_path = find_tesseract_path()
    tess_version = get_tesseract_version(tess_path)
    tess_installed = bool(tess_path)

    cv2_installed = cv2 is not None
    cv2_version = getattr(cv2, "__version__", None) if cv2 else None
    clahe_supported = cv2_installed and hasattr(cv2, "createCLAHE")

    pil_installed = Image is not None
    pil_version = getattr(Image, "__version__", None) if Image else None

    # Determine status
    if tess_installed and cv2_installed:
        status = "healthy"
        status_label = "Operational (Dual-Engine: OpenCV + Tesseract)"
    elif tess_installed and pil_installed:
        status = "degraded"
        status_label = "Degraded (OpenCV missing; using PIL grayscale fallback)"
    else:
        status = "unhealthy"
        status_label = "Offline (Tesseract OCR executable not detected)"

    self_test_res = run_synthetic_ocr_test(tess_path) if run_self_test else None
    metrics = get_captcha_operational_metrics(db)

    return {
        "status": status,
        "status_label": status_label,
        "timestamp": datetime.now().isoformat(),
        "engine": {
            "tesseract": {
                "installed": tess_installed,
                "path": tess_path,
                "version": tess_version,
            },
            "opencv": {
                "installed": cv2_installed,
                "version": cv2_version,
                "clahe_supported": clahe_supported,
            },
            "pillow": {
                "installed": pil_installed,
                "version": pil_version,
            },
        },
        "self_test": self_test_res,
        "metrics": metrics,
    }
