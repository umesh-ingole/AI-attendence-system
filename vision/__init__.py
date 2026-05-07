"""
Vision module for AI Attendance System
======================================

This package contains all computer vision components for the AI attendance system,
including face detection, face embedding generation, and face recognition.

Components:
- dataset_collector: Collect student face datasets from webcam
- generate_embeddings: Generate InsightFace embeddings from datasets
- face_recognition: Real-time face recognition and attendance marking

Author: AI Attendance System
Version: 1.0.0
"""

from .dataset_collector import FaceDatasetCollector, collect_face_dataset
from .generate_embeddings import EmbeddingGenerator, generate_face_embeddings, load_known_faces

__all__ = [
    'FaceDatasetCollector',
    'collect_face_dataset',
    'EmbeddingGenerator',
    'generate_face_embeddings',
    'load_known_faces',
]

__version__ = '1.0.0'
