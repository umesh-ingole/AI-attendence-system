"""
init_data.py — Run once to bootstrap required data files.
Called automatically by app.py on startup if files are missing.
"""
import json
import os
from pathlib import Path

DEFAULT_DATA = {
    "students": [],
    "timetable": {},
    "period_attendance": [],
    "settings": {
        "late_grace_minutes": 10,
        "exit_timeout_seconds": 30,
        "recognition_threshold": 0.40
    }
}


def ensure_data_files():
    """Create required directories and default data files if missing."""
    # Directories
    Path("data").mkdir(exist_ok=True)
    Path("dataset").mkdir(exist_ok=True)
    Path(".streamlit").mkdir(exist_ok=True)

    # data.json
    if not Path("data.json").exists():
        with open("data.json", "w") as f:
            json.dump(DEFAULT_DATA, f, indent=2)

    # erp_attendance.json
    if not Path("data/erp_attendance.json").exists():
        with open("data/erp_attendance.json", "w") as f:
            json.dump({}, f)

    # face_embeddings.pkl — do NOT overwrite, just ensure dir exists
    Path("data").mkdir(exist_ok=True)


if __name__ == "__main__":
    ensure_data_files()
    print("✅ Data files initialized.")
