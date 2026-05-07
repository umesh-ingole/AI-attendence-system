"""
Production-Ready InsightFace Embedding Generator Module
=========================================================

This module generates facial embeddings from collected student datasets using
InsightFace and ONNXRuntime for the AI Smart Attendance System.

Key Features:
- Scans student dataset folders automatically
- Detects faces using InsightFace FaceAnalysis
- Generates high-quality facial embeddings
- Computes average embedding per student
- Handles corrupted images gracefully
- Comprehensive error logging
- Pickle-based persistence
- CPU-only execution (Raspberry Pi compatible)

The generated embeddings are used for:
- Real-time face recognition
- Attendance matching
- Student identification
- System training and validation

Author: AI Attendance System
Version: 1.0.0
"""

import os
import cv2
import numpy as np
import pickle
import logging
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import warnings

# Suppress TensorFlow and other warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('embedding_generation.log')
    ]
)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Production-ready embedding generator using InsightFace.
    
    This class handles the complete pipeline of generating facial embeddings
    from student face images collected via the dataset collector.
    
    Attributes:
        model_name: InsightFace model to use (default: buffalo_l)
        data_dir: Path to dataset directory
        output_dir: Path to save embeddings
        embedding_size: Dimension of generated embeddings (512 for buffalo_l)
    """
    
    def __init__(self, model_name='buffalo_l', data_dir='dataset', output_dir='data'):
        """
        Initialize the EmbeddingGenerator.
        
        Args:
            model_name (str): InsightFace model name (default: buffalo_l)
            data_dir (str): Path to dataset directory
            output_dir (str): Path to save embeddings
            
        Raises:
            ImportError: If InsightFace or required packages are not installed
            RuntimeError: If model cannot be loaded
        """
        logger.info(f"Initializing EmbeddingGenerator with model: {model_name}")
        
        # Verify required packages
        try:
            import insightface
        except ImportError:
            logger.error("InsightFace not installed. Install with: pip install insightface")
            raise ImportError("insightface package required")
        
        try:
            import onnxruntime
        except ImportError:
            logger.error("ONNXRuntime not installed. Install with: pip install onnxruntime")
            raise ImportError("onnxruntime package required")
        
        self.model_name = model_name
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory set to: {self.output_dir.absolute()}")
        
        # Verify dataset directory exists
        if not self.data_dir.exists():
            logger.error(f"Dataset directory not found: {self.data_dir}")
            raise FileNotFoundError(f"Dataset directory not found: {self.data_dir}")
        
        logger.info(f"Dataset directory: {self.data_dir.absolute()}")
        
        # Initialize InsightFace model
        try:
            # Use CPU provider only for compatibility
            import insightface
            self.face_analysis = insightface.app.FaceAnalysis(
                name=model_name,
                providers=['CPUExecutionProvider']  # CPU only for compatibility
            )
            self.face_analysis.prepare(ctx_id=-1, det_size=(640, 640))
            logger.info(f"InsightFace model '{model_name}' loaded successfully")
            logger.info("Using CPU execution provider for compatibility")
        except Exception as e:
            logger.error(f"Failed to load InsightFace model: {str(e)}")
            raise RuntimeError(f"Failed to load InsightFace model: {str(e)}")
        
        # Statistics tracking
        self.stats = {
            'total_students': 0,
            'total_images_processed': 0,
            'successful_embeddings': 0,
            'failed_images': 0,
            'students_processed': 0
        }
    
    def _load_image(self, image_path: Path) -> Optional[np.ndarray]:
        """
        Safely load an image from disk.
        
        Args:
            image_path (Path): Path to image file
            
        Returns:
            ndarray: Loaded image in BGR format, or None if failed
        """
        try:
            image = cv2.imread(str(image_path))
            
            if image is None:
                logger.warning(f"Failed to read image: {image_path}")
                self.stats['failed_images'] += 1
                return None
            
            return image
        except Exception as e:
            logger.warning(f"Error loading image {image_path}: {str(e)}")
            self.stats['failed_images'] += 1
            return None
    
    def _detect_and_embed_face(self, image: np.ndarray, image_path: Path) -> Optional[np.ndarray]:
        """
        Detect face in image and generate embedding.
        
        Args:
            image (ndarray): Image in BGR format
            image_path (Path): Path to image (for logging)
            
        Returns:
            ndarray: Face embedding vector (512-dim for buffalo_l), or None if no face detected
        """
        try:
            # Detect faces in image
            faces = self.face_analysis.get(image)
            
            if len(faces) == 0:
                logger.warning(f"No face detected in: {image_path.name}")
                self.stats['failed_images'] += 1
                return None
            
            if len(faces) > 1:
                logger.warning(f"Multiple faces detected in {image_path.name}, using first face")
            
            # Get embedding from first face
            face = faces[0]
            embedding = face.embedding
            
            # Normalize embedding (L2 normalization)
            embedding = embedding / np.linalg.norm(embedding)
            
            self.stats['successful_embeddings'] += 1
            return embedding
            
        except Exception as e:
            logger.warning(f"Error processing image {image_path.name}: {str(e)}")
            self.stats['failed_images'] += 1
            return None
    
    def _compute_average_embedding(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """
        Compute average embedding from multiple embeddings.
        
        Args:
            embeddings (List[ndarray]): List of embedding vectors
            
        Returns:
            ndarray: Average embedding vector (normalized)
        """
        if not embeddings:
            return None
        
        # Stack embeddings and compute mean
        embeddings_array = np.array(embeddings)
        average_embedding = np.mean(embeddings_array, axis=0)
        
        # Normalize average embedding
        average_embedding = average_embedding / np.linalg.norm(average_embedding)
        
        return average_embedding
    
    def _parse_folder_name(self, folder_name: str) -> Optional[Tuple[str, str]]:
        """
        Parse student folder name to extract roll_no and name.
        
        Expected format: <roll_no>_<name> (e.g., "101_Amit")
        
        Args:
            folder_name (str): Folder name
            
        Returns:
            Tuple[str, str]: (roll_no, name) or None if format invalid
        """
        try:
            parts = folder_name.split('_', 1)
            if len(parts) != 2:
                logger.warning(f"Invalid folder name format: {folder_name}")
                return None
            
            roll_no, name = parts
            
            # Validate roll_no is alphanumeric
            if not roll_no.isalnum():
                logger.warning(f"Invalid roll number (must be alphanumeric) in folder: {folder_name}")
                return None
            
            return roll_no, name
        except Exception as e:
            logger.warning(f"Error parsing folder name '{folder_name}': {str(e)}")
            return None
    
    def _process_student_folder(self, student_folder: Path) -> Optional[Dict]:
        """
        Process all images in a student's folder and generate average embedding.
        
        Args:
            student_folder (Path): Path to student's dataset folder
            
        Returns:
            dict: {
                'roll_no': str,
                'name': str,
                'embedding': ndarray,
                'image_count': int,
                'valid_images': int
            }
            or None if no valid embeddings generated
        """
        folder_name = student_folder.name
        
        # Parse folder name
        parse_result = self._parse_folder_name(folder_name)
        if parse_result is None:
            logger.error(f"Skipping invalid folder: {folder_name}")
            return None
        
        roll_no, name = parse_result
        logger.info(f"Processing student: {name} (Roll No: {roll_no})")
        
        # Find all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        image_files = [f for f in student_folder.iterdir() 
                      if f.suffix.lower() in image_extensions]
        
        if not image_files:
            logger.warning(f"No images found in: {folder_name}")
            return None
        
        logger.info(f"Found {len(image_files)} images for {name}")
        
        # Generate embeddings for each image
        embeddings = []
        valid_image_count = 0
        
        for image_path in sorted(image_files):
            # Load image
            image = self._load_image(image_path)
            if image is None:
                continue
            
            self.stats['total_images_processed'] += 1
            
            # Detect face and generate embedding
            embedding = self._detect_and_embed_face(image, image_path)
            if embedding is not None:
                embeddings.append(embedding)
                valid_image_count += 1
        
        # Compute average embedding
        if not embeddings:
            logger.error(f"No valid embeddings generated for {name}")
            return None
        
        average_embedding = self._compute_average_embedding(embeddings)
        
        logger.info(f"✓ Successfully processed {name}: "
                   f"{valid_image_count}/{len(image_files)} valid images")
        
        return {
            'roll_no': roll_no,
            'name': name,
            'embedding': average_embedding,
            'image_count': len(image_files),
            'valid_images': valid_image_count
        }
    
    def generate_face_embeddings(self, verbose: bool = True) -> Dict:
        """
        Main function to generate embeddings for all students in dataset.
        
        This function:
        1. Scans all student folders in dataset/
        2. Extracts roll_no and name from folder names
        3. Loads images safely (skips corrupted files)
        4. Detects faces using InsightFace
        5. Generates embeddings for each face
        6. Computes average embedding per student
        7. Saves embeddings to pickle file
        
        Args:
            verbose (bool): Whether to print progress information
            
        Returns:
            dict: Summary of embedding generation with keys:
                - status: 'success' or 'partial_success' or 'failed'
                - total_students: Number of student folders found
                - successful_students: Number of students with valid embeddings
                - total_images: Total images processed
                - successful_embeddings: Number of valid embeddings
                - failed_images: Number of failed images
                - output_path: Path to saved embeddings
                - timestamp: Generation timestamp
        """
        
        print("\n" + "="*70)
        print("INSIGHTFACE EMBEDDING GENERATOR")
        print("="*70)
        logger.info("Starting embedding generation process")
        
        # Find all student folders
        student_folders = sorted([d for d in self.data_dir.iterdir() 
                                 if d.is_dir() and '_' in d.name])
        
        if not student_folders:
            logger.error(f"No student folders found in {self.data_dir}")
            print("[ERROR] No student folders found in dataset directory")
            return {
                'status': 'failed',
                'total_students': 0,
                'successful_students': 0,
                'error': 'No student folders found'
            }
        
        logger.info(f"Found {len(student_folders)} student folders")
        print(f"[INFO] Found {len(student_folders)} student folders")
        
        self.stats['total_students'] = len(student_folders)
        
        # Process each student folder
        embeddings_data = {}
        
        for idx, student_folder in enumerate(student_folders, 1):
            print(f"\n[{idx}/{len(student_folders)}] Processing: {student_folder.name}")
            
            result = self._process_student_folder(student_folder)
            
            if result is not None:
                roll_no = result['roll_no']
                embeddings_data[roll_no] = {
                    'name': result['name'],
                    'embedding': result['embedding'],
                    'image_count': result['image_count'],
                    'valid_images': result['valid_images']
                }
                self.stats['students_processed'] += 1
        
        # Save embeddings to pickle
        output_path = self.output_dir / 'face_embeddings.pkl'
        
        if not embeddings_data:
            logger.error("No valid embeddings generated. Aborting save to prevent overwriting existing data.")
            print("\n[ERROR] No valid embeddings generated. Database was NOT overwritten.")
            return {
                'status': 'failed',
                'error': 'No valid embeddings found in dataset. Ensure images exist before training.'
            }
        
        try:
            with open(output_path, 'wb') as f:
                pickle.dump(embeddings_data, f)
            logger.info(f"Embeddings saved to: {output_path}")
            print(f"\n[SUCCESS] Embeddings saved to: {output_path.absolute()}")
        except Exception as e:
            logger.error(f"Failed to save embeddings: {str(e)}")
            print(f"[ERROR] Failed to save embeddings: {str(e)}")
            return {
                'status': 'failed',
                'error': f'Failed to save embeddings: {str(e)}'
            }
        
        # Print summary
        print("\n" + "="*70)
        print("EMBEDDING GENERATION SUMMARY")
        print("="*70)
        print(f"[SUMMARY] Total students processed: {self.stats['students_processed']}")
        print(f"[SUMMARY] Total images processed: {self.stats['total_images_processed']}")
        print(f"[SUMMARY] Successful embeddings: {self.stats['successful_embeddings']}")
        print(f"[SUMMARY] Failed images: {self.stats['failed_images']}")
        print(f"[SUMMARY] Output path: {output_path.absolute()}")
        print("="*70 + "\n")
        
        logger.info("Embedding generation completed successfully")
        
        # Determine status
        status = 'success' if self.stats['students_processed'] == len(student_folders) else 'partial_success'
        
        return {
            'status': status,
            'total_students': len(student_folders),
            'successful_students': self.stats['students_processed'],
            'total_images': self.stats['total_images_processed'],
            'successful_embeddings': self.stats['successful_embeddings'],
            'failed_images': self.stats['failed_images'],
            'output_path': str(output_path.absolute()),
            'embeddings_dict': embeddings_data
        }


def load_known_faces(embeddings_file: str = 'data/face_embeddings.pkl') -> Optional[Dict]:
    """
    Load previously generated face embeddings from pickle file.
    
    This function loads the embeddings generated by generate_face_embeddings()
    for use in real-time face recognition.
    
    Args:
        embeddings_file (str): Path to embeddings pickle file
        
    Returns:
        dict: {
            roll_no: {
                'name': student_name,
                'embedding': embedding_vector
            }
        }
        or None if file not found or error occurred
        
    Usage:
        known_faces = load_known_faces()
        if known_faces:
            for roll_no, data in known_faces.items():
                print(f"Loaded: {data['name']} (Roll No: {roll_no})")
    """
    embeddings_path = Path(embeddings_file)
    
    if not embeddings_path.exists():
        logger.error(f"Embeddings file not found: {embeddings_path}")
        return None
    
    try:
        with open(embeddings_path, 'rb') as f:
            embeddings_data = pickle.load(f)
        
        # Transform to required format
        known_faces = {}
        for roll_no, data in embeddings_data.items():
            known_faces[roll_no] = {
                'name': data['name'],
                'embedding': data['embedding']
            }
        
        logger.info(f"Loaded {len(known_faces)} embeddings from {embeddings_path}")
        return known_faces
        
    except Exception as e:
        logger.error(f"Failed to load embeddings: {str(e)}")
        return None


def generate_face_embeddings(model_name: str = 'buffalo_l', 
                            data_dir: str = 'dataset',
                            output_dir: str = 'data',
                            verbose: bool = True) -> Dict:
    """
    Convenience function to generate face embeddings.
    
    This is the main entry point for the embedding generation pipeline.
    
    Usage:
        result = generate_face_embeddings()
        print(f"Successfully processed: {result['successful_students']} students")
    
    Args:
        model_name (str): InsightFace model to use (default: buffalo_l)
        data_dir (str): Path to dataset directory (default: dataset)
        output_dir (str): Path to save embeddings (default: data)
        verbose (bool): Whether to print progress (default: True)
        
    Returns:
        dict: Generation summary with status and statistics
    """
    try:
        generator = EmbeddingGenerator(
            model_name=model_name,
            data_dir=data_dir,
            output_dir=output_dir
        )
        return generator.generate_face_embeddings(verbose=verbose)
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        print(f"[ERROR] {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }


# Main execution
if __name__ == "__main__":
    """
    Standalone execution for embedding generation.
    
    This runs the complete embedding generation pipeline for all
    student datasets found in the dataset/ directory.
    
    Usage:
        python vision/generate_embeddings.py
    """
    
    print("\n" + "="*70)
    print("FACE EMBEDDING GENERATION - STANDALONE MODE")
    print("="*70 + "\n")
    
    try:
        # Generate embeddings
        result = generate_face_embeddings()
        
        # Print result
        print("\n[RESULT] Embedding Generation Complete")
        print(f"  Status: {result['status'].upper()}")
        print(f"  Students Processed: {result.get('successful_students', 0)}/{result.get('total_students', 0)}")
        print(f"  Total Images: {result.get('total_images', 0)}")
        print(f"  Successful Embeddings: {result.get('successful_embeddings', 0)}")
        print(f"  Failed Images: {result.get('failed_images', 0)}")
        print(f"  Output: {result.get('output_path', 'N/A')}")
        
        # Test loading embeddings
        print("\n[TEST] Loading generated embeddings...")
        known_faces = load_known_faces()
        if known_faces:
            print(f"[SUCCESS] Loaded {len(known_faces)} student embeddings")
            print("\nSample students:")
            for roll_no, data in list(known_faces.items())[:3]:
                print(f"  - {data['name']} (Roll No: {roll_no})")
        else:
            print("[WARNING] Could not load embeddings")
    
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Embedding generation cancelled by user")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
