import cv2
import numpy as np
import insightface
import onnxruntime
import pickle
import time
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

# Import Attendance Engine
from logic.attendance_engine import AttendanceLogicEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec1: First embedding vector
        vec2: Second embedding vector
    
    Returns:
        Cosine similarity score (0 to 1)
    """
    # Normalize vectors to unit length
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    vec1_normalized = vec1 / norm1
    vec2_normalized = vec2 / norm2
    
    # Compute cosine similarity (dot product of normalized vectors)
    similarity = np.dot(vec1_normalized, vec2_normalized)
    
    # Clamp to [0, 1] range for robustness
    return float(np.clip(similarity, 0, 1))


class RealTimeFaceRecognitionEngine:
    """
    Production-ready real-time face recognition engine for student attendance.
    
    Features:
    - Real-time face detection and recognition via webcam
    - Cosine similarity matching against pre-generated embeddings
    - Cooldown system to prevent duplicate recognition spam
    - Performance optimized for CPU execution (Raspberry Pi compatible)
    - Visual UI with FPS counter, face count, bounding boxes, confidence scores
    - Robust error handling for webcam and model failures
    - Future-ready architecture for Streamlit and event logging integration
    
    Example:
        engine = RealTimeFaceRecognitionEngine()
        engine.start_recognition()
    """
    
    def __init__(self, 
                 embeddings_path: str = "data/face_embeddings.pkl",
                 similarity_threshold: float = 0.40,
                 recognition_cooldown: int = 10):
        """
        Initialize the face recognition engine.
        
        Args:
            embeddings_path: Path to pickled face embeddings dictionary
            similarity_threshold: Minimum cosine similarity for recognition (default: 0.40)
            recognition_cooldown: Cooldown period in seconds between recognitions (default: 10s)
        
        Raises:
            FileNotFoundError: If embeddings file not found
            ValueError: If embeddings are corrupted or invalid format
        """
        self.embeddings_path = Path(embeddings_path)
        self.similarity_threshold = similarity_threshold
        self.recognition_cooldown = recognition_cooldown
        
        logger.info("=" * 60)
        logger.info("Real-Time Face Recognition Engine Initialization")
        logger.info("=" * 60)
        
        # Initialize InsightFace model (buffalo_l for best accuracy)
        logger.info("Initializing InsightFace model (buffalo_l)...")
        try:
            self.face_analyzer = insightface.app.FaceAnalysis(
                name='buffalo_l',
                providers=['CPUExecutionProvider']  # CPU only
            )
            self.face_analyzer.prepare(ctx_id=-1, det_size=(320, 320))  # -1 for CPU, small det_size for maximum speed
            logger.info("✓ InsightFace initialized successfully")
            logger.info(f"  Model: buffalo_l | Provider: CPUExecutionProvider")
        except Exception as e:
            logger.error(f"✗ Failed to initialize InsightFace: {e}")
            raise RuntimeError(f"InsightFace initialization failed: {e}")
        
        # Load known embeddings
        logger.info(f"Loading pre-generated embeddings from {self.embeddings_path}...")
        try:
            self.known_faces = self._load_known_embeddings()
            logger.info(f"✓ Loaded {len(self.known_faces)} student embeddings")
            for roll_no, data in list(self.known_faces.items())[:3]:
                logger.debug(f"  - {roll_no}: {data['name']} (embedding shape: {data['embedding'].shape})")
        except Exception as e:
            logger.error(f"✗ Failed to load embeddings: {e}")
            raise
        
        # Initialize webcam-related attributes
        self.cap = None
        self.frame_width = None
        self.frame_height = None
        
        # Initialize Attendance Engine
        logger.info("Initializing Attendance Logic Engine...")
        try:
            self.attendance_engine = AttendanceLogicEngine()
        except Exception as e:
            logger.error(f"✗ Failed to initialize Attendance Engine: {e}")
            self.attendance_engine = None

        # State for auto-marking and feedback
        self.last_auto_mark_time = time.time()
        self.feedback_text = ""
        self.feedback_expiry = 0
        self.last_detected_student = None
        self.last_detected_time = 0
        
        # Cooldown tracking to prevent repeated recognition spam
        self.last_recognized_times = defaultdict(lambda: datetime.min)
        
        # Performance metrics
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0.0
        
        logger.info(f"Configuration: threshold={self.similarity_threshold}, cooldown={self.recognition_cooldown}s")
        logger.info("=" * 60)
    
    def _load_known_embeddings(self) -> dict:
        """
        Load pre-generated face embeddings from pickle file.
        
        Expected format:
        {
            "roll_no_1": {"name": "Student Name", "embedding": np.ndarray(512,)},
            "roll_no_2": {"name": "Another Name", "embedding": np.ndarray(512,)},
            ...
        }
        
        Returns:
            Dictionary mapping roll numbers to {name, embedding}
        
        Raises:
            FileNotFoundError: If embeddings file doesn't exist
            ValueError: If file is corrupted or has invalid format
        """
        if not self.embeddings_path.exists():
            raise FileNotFoundError(
                f"Embeddings file not found at: {self.embeddings_path}\n"
                f"Please run generate_embeddings.py first."
            )
        
        try:
            with open(self.embeddings_path, 'rb') as f:
                embeddings_data = pickle.load(f)
            
            # Validate format
            if not isinstance(embeddings_data, dict):
                raise ValueError(f"Expected dict, got {type(embeddings_data)}")
            
            if len(embeddings_data) == 0:
                logger.warning("Embeddings dictionary is empty. Engine will start but recognize no one.")
                return {}
            
            # Validate sample entry
            sample_key = next(iter(embeddings_data))
            sample_value = embeddings_data[sample_key]
            
            if not isinstance(sample_value, dict) or 'embedding' not in sample_value:
                raise ValueError(
                    f"Invalid embedding format. Expected dict with 'embedding' key, got: {sample_value.keys()}"
                )
            
            return embeddings_data
        
        except pickle.UnpicklingError as e:
            raise ValueError(f"Embeddings file is corrupted: {e}")
        except Exception as e:
            raise ValueError(f"Error loading embeddings: {e}")
    
    def match_face(self, face_embedding: np.ndarray) -> dict:
        """
        Match detected face against known embeddings using cosine similarity.
        
        Performs exhaustive search against all known students and returns
        the best match if similarity exceeds threshold.
        
        Args:
            face_embedding: Embedding vector from detected face (typically 512-dim)
        
        Returns:
            Match result: {"roll_no": str, "name": str, "similarity": float}
            Returns None if no match meets the similarity threshold
        """
        if not isinstance(face_embedding, np.ndarray):
            logger.warning(f"Invalid embedding type: {type(face_embedding)}")
            return None
        
        if face_embedding.size == 0:
            logger.warning("Empty face embedding received")
            return None
        
        best_match = None
        best_similarity = -1
        
        # Compare against all known embeddings
        for roll_no, student_data in self.known_faces.items():
            try:
                known_embedding = student_data['embedding']
                
                # Compute cosine similarity
                similarity = cosine_similarity(face_embedding, known_embedding)
                
                # Track best match
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        'roll_no': str(roll_no),
                        'name': student_data['name'],
                        'similarity': similarity
                    }
            
            except Exception as e:
                logger.debug(f"Error matching against {roll_no}: {e}")
                continue
        
        # Return match only if above threshold
        if best_match and best_similarity >= self.similarity_threshold:
            return best_match
        
        return None
    
    def _should_recognize(self, roll_no: str) -> bool:
        """
        Check if student should be recognized (cooldown-based duplicate prevention).
        
        Implements cooldown system to prevent spam of same student recognition.
        Once a student is recognized, they are ignored for the next 10 seconds.
        
        Args:
            roll_no: Student roll number
        
        Returns:
            True if student can be recognized (outside cooldown)
            False if student is in cooldown period
        """
        last_recognition_time = self.last_recognized_times[roll_no]
        current_time = datetime.now()
        
        time_since_last = current_time - last_recognition_time
        
        if time_since_last >= timedelta(seconds=self.recognition_cooldown):
            # Update last recognition time
            self.last_recognized_times[roll_no] = current_time
            return True
        
        return False
    
    def _calculate_fps(self) -> float:
        """
        Calculate and update FPS metric.
        
        Returns:
            Current frames per second
        """
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        
        if elapsed > 0:
            self.fps = self.frame_count / elapsed
        
        return self.fps
    
    def _draw_ui_overlay(self, frame: np.ndarray, 
                        faces_detected: int) -> np.ndarray:
        """
        Draw UI overlay elements on frame.
        
        Displays:
        - Top-left: FPS counter and faces detected count
        - Right-side: Attendance Status Panel (active students, daily total)
        - Top-center: Feedback message (temporary)
        - Bottom: Keyboard instructions (Q=Quit, S=Screenshot)
        
        Args:
            frame: Current video frame
            faces_detected: Number of faces detected in current frame
        
        Returns:
            Frame with UI overlay drawn
        """
        height, width = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # 1. Top-left: Performance metrics
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 30),
                   font, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Faces Detected: {faces_detected}", (10, 60),
                   font, 0.7, (0, 255, 0), 2)
        
        # 2. Right-side: Attendance Status Panel
        if self.attendance_engine:
            try:
                # Panel dimensions
                panel_width = 250
                panel_x = width - panel_width
                
                # Draw semi-transparent background for panel
                overlay = frame.copy()
                cv2.rectangle(overlay, (panel_x, 0), (width, height), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
                
                # Panel Header
                cv2.putText(frame, "LIVE ATTENDANCE", (panel_x + 10, 30),
                           font, 0.6, (255, 255, 0), 2)
                
                # Total Records Today
                summary = self.attendance_engine.get_attendance_summary()
                total_today = summary.get('total_records', 0)
                cv2.putText(frame, f"Total Today: {total_today}", (panel_x + 10, 60),
                           font, 0.5, (255, 255, 255), 1)
                
                # Active Students
                active_summary = self.attendance_engine.get_active_students_summary()
                active_count = active_summary.get('count', 0)
                cv2.putText(frame, f"Active Now: {active_count}", (panel_x + 10, 90),
                           font, 0.5, (0, 255, 0), 1)
                
                # List active names
                cv2.putText(frame, "Active List:", (panel_x + 10, 120),
                           font, 0.5, (200, 200, 200), 1)
                
                y_offset = 145
                for i, student in enumerate(active_summary.get('students', [])[:10]):
                    name = student['name']
                    # Truncate long names for panel
                    if len(name) > 18: name = name[:15] + "..."
                    cv2.putText(frame, f"- {name}", (panel_x + 15, y_offset),
                               font, 0.4, (255, 255, 255), 1)
                    y_offset += 25
                
                if active_count > 10:
                    cv2.putText(frame, f"...and {active_count-10} more", (panel_x + 15, y_offset),
                               font, 0.4, (200, 200, 200), 1)
                
            except Exception as e:
                logger.debug(f"UI Overlay Error: {e}")

        # 3. Top-center: Feedback Message
        if self.feedback_text and time.time() < self.feedback_expiry:
            (tw, th), _ = cv2.getTextSize(self.feedback_text, font, 0.8, 2)
            tx = (width - tw) // 2
            # Draw feedback background
            cv2.rectangle(frame, (tx - 10, 20), (tx + tw + 10, 60), (0, 200, 0), -1)
            cv2.putText(frame, self.feedback_text, (tx, 50),
                       font, 0.8, (255, 255, 255), 2)
        
        return frame
    
    def _draw_face_boxes(self, frame: np.ndarray, 
                        faces: list,
                        recognition_results: dict) -> np.ndarray:
        """
        Draw bounding boxes and labels on detected faces.
        
        Visual coding:
        - Green box: Recognized student (name, roll number, confidence)
        - Red box: Unknown/unrecognized face
        
        Args:
            frame: Current video frame
            faces: List of detected face objects from InsightFace
            recognition_results: Dict mapping face index to recognition info
        
        Returns:
            Frame with boxes and labels drawn
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        for idx, face in enumerate(faces):
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            
            # Ensure coordinates are within frame bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)
            
            recognition = recognition_results.get(idx)
            
            if recognition:
                # Recognized face: GREEN
                color = (0, 255, 0)
                name = recognition['name']
                roll_no = recognition['roll_no']
                similarity = recognition['similarity']
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw student info label
                label_text = f"{name} ({roll_no})"
                confidence_text = f"Conf: {similarity:.3f}"
                
                # Calculate text size for background
                (text_width, text_height) = cv2.getTextSize(
                    label_text, font, 0.6, 1
                )[0]
                
                # Draw label background
                cv2.rectangle(frame, 
                            (x1, y1 - 35), 
                            (x1 + text_width + 10, y1 - 5), 
                            color, -1)
                
                # Draw text
                cv2.putText(frame, label_text, (x1 + 5, y1 - 12),
                           font, 0.6, (0, 0, 0), 1)
                cv2.putText(frame, confidence_text, (x1, y2 + 20),
                           font, 0.5, color, 1)
            else:
                # Unknown face: RED
                color = (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw unknown label
                label_text = "Unknown"
                (text_width, text_height) = cv2.getTextSize(
                    label_text, font, 0.6, 1
                )[0]
                
                cv2.rectangle(frame,
                            (x1, y1 - 30),
                            (x1 + text_width + 10, y1),
                            color, -1)
                cv2.putText(frame, label_text, (x1 + 5, y1 - 10),
                           font, 0.6, (255, 255, 255), 1)
        
        return frame
    
    def start_recognition(self, camera_index: int = 0,
                         frame_resize_scale: float = 0.35,
                         show_window: bool = False) -> None:
        """
        Start real-time face recognition from webcam.
        
        Main engine loop:
        1. Capture frame from webcam
        2. Detect faces using InsightFace
        3. Generate embeddings for detected faces
        4. Match against known embeddings using cosine similarity
        5. Apply cooldown to prevent spam
        6. Draw visual overlays
        7. Handle keyboard input (Q=quit, S=screenshot)
        
        Performance optimizations:
        - Frame resizing for faster inference
        - Single model initialization
        - Efficient numpy operations
        
        Args:
            camera_index: Index of camera device (default: 0 for built-in)
            frame_resize_scale: Scale factor for frame (0-1, lower = faster)
                              Recommended: 0.5-0.7 for good balance
        
        Returns:
            None
        """
        logger.info("\n" + "=" * 60)
        logger.info("STARTING REAL-TIME FACE RECOGNITION")
        logger.info("=" * 60)
        
        # Initialize webcam
        logger.info(f"Opening webcam (index: {camera_index})...")
        self.cap = cv2.VideoCapture(camera_index)
        
        if not self.cap.isOpened():
            logger.error(f"✗ Failed to open webcam at index {camera_index}")
            logger.error("  Check camera connection or try different index")
            return
        
        # Set camera properties for optimal performance
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for low latency
        
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"✓ Webcam opened successfully")
        logger.info(f"  Resolution: {self.frame_width}x{self.frame_height}")
        logger.info(f"  Frame resize scale: {frame_resize_scale}")
        logger.info(f"  Similarity threshold: {self.similarity_threshold}")
        logger.info(f"  Recognition cooldown: {self.recognition_cooldown}s")
        logger.info("\nControls:")
        logger.info("  Q = Quit application")
        logger.info("  S = Save screenshot")
        logger.info("\n" + "=" * 60 + "\n")
        
        import threading
        
        self.latest_raw_frame = None
        self.cam_running = True
        
        def cam_reader():
            while self.cam_running and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.latest_raw_frame = frame
                else:
                    break
                    
        reader_thread = threading.Thread(target=cam_reader, daemon=True)
        reader_thread.start()
        
        last_processed_frame = None
        
        # Performance boosting variables for frame skipping
        frame_counter = 0
        cached_faces = []
        cached_recognition_results = {}
        
        try:
            while self.cam_running:
                frame = self.latest_raw_frame
                # Skip if there's no frame or we already processed this exact frame
                if frame is None or frame is last_processed_frame:
                    time.sleep(0.01)
                    continue
                
                last_processed_frame = frame
                
                # Create a copy for display and resize for inference
                display_frame = frame.copy()
                
                if frame_resize_scale < 1.0:
                    inference_frame = cv2.resize(
                        frame,
                        (int(frame.shape[1] * frame_resize_scale),
                         int(frame.shape[0] * frame_resize_scale))
                    )
                else:
                    inference_frame = frame
                
                # Increment frame counter and determine if we should run heavy inference
                frame_counter += 1
                run_inference = (frame_counter % 4 == 0) or (frame_counter == 1)
                
                # Auto-marking for active students (every 30 seconds)
                current_time = time.time()
                if self.attendance_engine and (current_time - self.last_auto_mark_time >= 30):
                    try:
                        self.attendance_engine.trigger_auto_transition()
                        self.last_auto_mark_time = current_time
                    except Exception as e:
                        logger.error(f"[ERROR] Auto-transition failed: {e}")
                
                if run_inference:
                    # Detect faces using InsightFace
                    try:
                        faces = self.face_analyzer.get(inference_frame)
                    except Exception as e:
                        logger.debug(f"Face detection error: {e}")
                        faces = []
                    
                    # Process each detected face
                    recognition_results = {}
                    
                    for idx, face in enumerate(faces):
                        try:
                            # Get embedding for this face
                            face_embedding = face.embedding
                            
                            # Match against known faces
                            match = self.match_face(face_embedding)
                            
                            if match:
                                self.last_detected_student = match
                                self.last_detected_time = time.time()
                                # Check if student should be recognized (cooldown)
                                if self._should_recognize(match['roll_no']):
                                    recognition_results[idx] = match
                                    
                                    # Log recognition event
                                    logger.info(
                                        f"[RECOGNIZED] Name: {match['name']} | "
                                        f"Roll: {match['roll_no']} | "
                                        f"Similarity: {match['similarity']:.4f} | "
                                        f"Time: {datetime.now().strftime('%H:%M:%S')}"
                                    )

                                    # Process Attendance Event
                                    if self.attendance_engine:
                                        try:
                                            self.attendance_engine.process_recognition_event(
                                                roll_no=match['roll_no'],
                                                name=match['name']
                                            )
                                            self.feedback_text = "✓ Attendance Logged"
                                            self.feedback_expiry = time.time() + 2.0
                                        except Exception as e:
                                            logger.error(f"[ERROR] Attendance processing failed: {e}")
                                else:
                                    # In cooldown but still show on display
                                    recognition_results[idx] = match
                            
                        except Exception as e:
                            logger.debug(f"Error processing face {idx}: {e}")
                            continue
                    
                    # Scale face boxes back to original frame size if resized
                    if frame_resize_scale < 1.0:
                        for face in faces:
                            face.bbox = face.bbox / frame_resize_scale
                            
                    # Cache the results for skipped frames
                    cached_faces = faces
                    cached_recognition_results = recognition_results
                else:
                    # Reuse cached results on skipped frames to bypass expensive face analysis
                    faces = cached_faces
                    recognition_results = cached_recognition_results
                
                # Update FPS
                self._calculate_fps()
                
                # Draw visual overlays on display frame
                display_frame = self._draw_face_boxes(
                    display_frame, faces, recognition_results
                )
                display_frame = self._draw_ui_overlay(
                    display_frame, len(faces)
                )
                
                # Store latest frame for Streamlit
                self.latest_frame = display_frame
                
                # Display the frame (wrap in try/except for headless environments)
                if show_window:
                    try:
                        cv2.imshow('Real-Time Face Recognition Engine', display_frame)
                        # Handle keyboard input
                        key = cv2.waitKey(1) & 0xFF
                        
                        if key == ord('q') or key == ord('Q'):
                            logger.info("\n[USER INPUT] Quit requested")
                            break
                        
                        elif key == ord('s') or key == ord('S'):
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            filename = f"screenshot_{timestamp}.jpg"
                            cv2.imwrite(filename, display_frame)
                            logger.info(f"[USER INPUT] Screenshot saved: {filename}")
                    except cv2.error:
                        # Fallback to simple sleep to prevent 100% CPU usage
                        time.sleep(0.01)
                else:
                    # Bypassing cv2.imshow for Streamlit environment to fully eliminate window paint blinking
                    time.sleep(0.01)
        
        except KeyboardInterrupt:
            logger.info("\n[INTERRUPT] Ctrl+C received")
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        
        finally:
            # Cleanup
            self.cam_running = False
            if self.cap:
                self.cap.release()
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass
            
            # Final statistics
            logger.info("\n" + "=" * 60)
            logger.info("Face Recognition Engine Stopped")
            logger.info("=" * 60)
            logger.info(f"Total frames processed: {self.frame_count}")
            if self.frame_count > 0:
                logger.info(f"Average FPS: {self.fps:.1f}")
            logger.info(f"Recognition threshold: {self.similarity_threshold}")
            logger.info(f"Total students tracked: {len(self.known_faces)}")
            logger.info("=" * 60 + "\n")


if __name__ == "__main__":
    """
    Standalone execution entry point.
    
    Run directly: python face_recognition_engine.py
    """
    try:
        engine = RealTimeFaceRecognitionEngine()
        engine.start_recognition(show_window=True)
    
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        logger.error("Please ensure data/face_embeddings.pkl exists")
    
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        logger.error("Check InsightFace installation and model availability")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
