"""Thread-safe logger engine for RERA Scraper.

Matches exact format and behavior from Cell 2 of RERA_Scrapping_fixed_v3.ipynb,
with support for pluggable callbacks to stream logs to PostgreSQL or WebSockets.
"""
import os
import threading
from datetime import datetime
from typing import Callable, Optional


class ScraperLogger:
    def __init__(self, log_file: str = "run_log.txt", callback: Optional[Callable[[str, str], None]] = None):
        self.log_file = log_file
        self.callback = callback
        self._lock = threading.Lock()

    def log(self, msg: str, level: str = "INFO"):
        thread_name = threading.current_thread().name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{thread_name}] {msg}"
        
        with self._lock:
            try:
                print(line)
            except UnicodeEncodeError:
                print(line.encode("ascii", errors="replace").decode("ascii"))
            
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass

        if self.callback:
            try:
                self.callback(level, msg)
            except Exception:
                pass

    def info(self, msg: str):
        self.log(msg, level="INFO")

    def warning(self, msg: str):
        self.log(f"⚠️ {msg}", level="WARNING")

    def error(self, msg: str):
        self.log(f"❌ {msg}", level="ERROR")

    def debug(self, msg: str):
        self.log(msg, level="DEBUG")

