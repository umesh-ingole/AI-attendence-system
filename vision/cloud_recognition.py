"""
cloud_recognition.py
────────────────────
Browser-based face recognition for Streamlit Cloud deployment.
Uses st.camera_input() instead of cv2.VideoCapture() so it works
on any device through a browser link — no local camera driver needed.
"""
import numpy as np
import cv2
import pickle
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return float(np.clip(np.dot(v1 / n1, v2 / n2), 0, 1))


def load_embeddings(path: str = "data/face_embeddings.pkl") -> dict:
    """Load face embeddings. Returns empty dict if file missing."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(p, "rb") as f:
            data = pickle.load(f)
        if not isinstance(data, dict) or len(data) == 0:
            return {}
        return data
    except Exception as e:
        logger.error(f"Failed to load embeddings: {e}")
        return {}


def get_face_analyzer():
    """Initialize InsightFace analyzer (cached in session state)."""
    import streamlit as st
    if "face_analyzer" not in st.session_state:
        try:
            import insightface
            analyzer = insightface.app.FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"]
            )
            analyzer.prepare(ctx_id=-1, det_size=(320, 320))
            st.session_state.face_analyzer = analyzer
            logger.info("InsightFace initialized for cloud mode")
        except Exception as e:
            logger.error(f"InsightFace init failed: {e}")
            st.session_state.face_analyzer = None
    return st.session_state.face_analyzer


def process_camera_frame(img_file_buffer, known_faces: dict,
                          threshold: float = 0.40) -> dict:
    """
    Process a single frame from st.camera_input().
    Returns recognition result dict or None.

    Args:
        img_file_buffer: bytes-like from st.camera_input()
        known_faces: dict from load_embeddings()
        threshold: cosine similarity threshold

    Returns:
        {roll_no, name, similarity, annotated_frame_rgb} or None
    """
    if img_file_buffer is None or not known_faces:
        return {"match": None, "annotated_frame": None, "face_count": 0}

    try:
        from PIL import Image
        import io
        img = Image.open(img_file_buffer).convert("RGB")
        frame_rgb = np.array(img)
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error(f"Frame decode error: {e}")
        return {"match": None, "annotated_frame": None, "face_count": 0}

    analyzer = get_face_analyzer()
    if analyzer is None:
        return {"match": None, "annotated_frame": frame_rgb, "face_count": 0}

    try:
        faces = analyzer.get(frame_bgr)
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        return {"match": None, "annotated_frame": frame_rgb, "face_count": 0}

    best_match = None
    annotated = frame_rgb.copy()

    for face in faces:
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = max(0, bbox[0]), max(0, bbox[1]), bbox[2], bbox[3]

        emb = face.embedding
        if emb is None:
            # Draw red box for unknown
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (220, 50, 50), 2)
            continue

        # Match against known faces
        top_roll, top_name, top_sim = None, None, -1
        for roll_no, student_data in known_faces.items():
            sim = cosine_similarity(emb, student_data["embedding"])
            if sim > top_sim:
                top_sim = sim
                top_roll = str(roll_no)
                top_name = student_data["name"]

        if top_sim >= threshold:
            # Green box for recognized
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (50, 220, 100), 2)
            label = f"{top_name} ({top_sim:.2f})"
            cv2.putText(annotated, label, (x1, max(y1 - 10, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 220, 100), 2)
            if best_match is None or top_sim > best_match["similarity"]:
                best_match = {"roll_no": top_roll, "name": top_name,
                              "similarity": top_sim}
        else:
            # Red box for unknown
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (220, 50, 50), 2)
            cv2.putText(annotated, "Unknown", (x1, max(y1 - 10, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 50, 50), 2)

    return {
        "match": best_match,
        "annotated_frame": annotated,
        "face_count": len(faces)
    }
