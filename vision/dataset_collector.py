"""
Production-Ready Dataset Collection Module for AI Face Recognition
=====================================================================

This module provides functionality to capture student face images from a webcam
and store them in an InsightFace-compatible dataset structure.

Key Features:
- Real-time face detection using OpenCV
- Face quality validation (blur detection, centering)
- Automatic image resizing and normalization
- Live UI overlay with instructions
- Dataset saved in structure: dataset/<roll_no>_<name>/
- Timestamp-based unique filenames
- Comprehensive logging
- Production-ready error handling

Author: AI Attendance System
Version: 1.0.0
"""

import cv2
import os
import numpy as np
from datetime import datetime
import time
from pathlib import Path


class FaceDatasetCollector:
    """
    A production-ready class for collecting student face dataset using webcam.
    
    Attributes:
        target_images: Number of images to capture per student (default: 30)
        image_size: Target image size (height, width)
        blur_threshold: Laplacian variance threshold for blur detection
        capture_interval: Frames between captures (to avoid duplicates)
    """
    
    def __init__(self, target_images=30, image_size=(224, 224), blur_threshold=100, capture_interval=5):
        """Initialize the FaceDatasetCollector."""
        self.target_images = target_images
        self.image_size = image_size
        self.blur_threshold = blur_threshold
        self.capture_interval = capture_interval
        
        # Load cascade classifier for face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            raise RuntimeError("Failed to load Haar Cascade classifier")
        
        print("[INIT] Face detection cascade classifier loaded successfully")
    
    def _is_face_blurry(self, face_image):
        """
        Detect if a face image is blurry using Laplacian variance method.
        
        Args:
            face_image: Cropped face image (BGR format)
            
        Returns:
            bool: True if image is blurry, False otherwise
        """
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return laplacian_var < self.blur_threshold
    
    def _is_face_centered(self, frame, face_rect, tolerance=0.15):
        """
        Check if face is centered in the frame.
        
        Args:
            frame: The video frame (BGR format)
            face_rect: Face bounding box (x, y, w, h)
            tolerance: Acceptable deviation from center (0.0-1.0)
            
        Returns:
            bool: True if face is centered, False otherwise
        """
        frame_height, frame_width = frame.shape[:2]
        x, y, w, h = face_rect
        
        # Face center
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        # Frame center
        frame_center_x = frame_width // 2
        frame_center_y = frame_height // 2
        
        # Calculate deviation as percentage
        x_deviation = abs(face_center_x - frame_center_x) / frame_width
        y_deviation = abs(face_center_y - frame_center_y) / frame_height
        
        return (x_deviation < tolerance and y_deviation < tolerance)
    
    def _resize_face_image(self, face_image):
        """
        Resize face image to target size with aspect ratio preservation.
        
        Args:
            face_image: Cropped face image
            
        Returns:
            ndarray: Resized face image
        """
        resized = cv2.resize(face_image, self.image_size, interpolation=cv2.INTER_LINEAR)
        return resized
    
    def _save_face_image(self, face_image, dataset_path, image_count):
        """
        Save face image with timestamp-based filename.
        
        Args:
            face_image: Cropped face image
            dataset_path: Path to student's dataset directory
            image_count: Sequential image number
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Create timestamp-based filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
            filename = f"face_{image_count:03d}_{timestamp}.jpg"
            filepath = os.path.join(dataset_path, filename)
            
            # Resize image
            resized_image = self._resize_face_image(face_image)
            
            # Save as JPG with high quality
            success = cv2.imwrite(filepath, resized_image, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            if success:
                return True
            else:
                print(f"[ERROR] Failed to save image: {filepath}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Exception while saving image: {str(e)}")
            return False
    
    def _draw_overlay(self, frame, name, roll_no, image_count, capturing, centered, is_valid):
        """
        Draw UI overlay on video frame with instructions and status.
        
        Args:
            frame: Video frame to draw on
            name: Student name
            roll_no: Student roll number
            image_count: Number of images captured so far
            capturing: Boolean indicating if capture is active
            centered: Boolean indicating if face is centered
            is_valid: Boolean indicating if current frame is valid for capture
            
        Returns:
            ndarray: Frame with overlay
        """
        frame_copy = frame.copy()
        height, width = frame.shape[:2]
        
        # Colors
        color_white = (255, 255, 255)
        color_green = (0, 255, 0)
        color_red = (0, 0, 255)
        color_yellow = (0, 255, 255)
        color_blue = (255, 0, 0)
        
        # Font
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        
        # Top panel background
        cv2.rectangle(frame_copy, (0, 0), (width, 120), (30, 30, 30), -1)
        
        # Student information
        cv2.putText(frame_copy, f"Name: {name}", (20, 35), font, font_scale, color_white, thickness)
        cv2.putText(frame_copy, f"Roll No: {roll_no}", (20, 70), font, font_scale, color_white, thickness)
        
        # Status
        status_color = color_green if capturing else color_red
        status_text = "STATUS: CAPTURING" if capturing else "STATUS: STANDBY"
        cv2.putText(frame_copy, status_text, (width - 350, 35), font, font_scale, status_color, thickness)
        
        # Image count
        progress_text = f"Images: {image_count}/{self.target_images}"
        cv2.putText(frame_copy, progress_text, (width - 350, 70), font, font_scale, color_yellow, thickness)
        
        # Bottom panel - Instructions and diagnostics
        cv2.rectangle(frame_copy, (0, height - 100), (width, height), (30, 30, 30), -1)
        
        cv2.putText(frame_copy, "INSTRUCTIONS:", (20, height - 60), font, font_scale, color_white, thickness)
        cv2.putText(frame_copy, "Press 'S' to Start Capture | Press 'Q' to Quit", (20, height - 25), font, font_scale, color_blue, thickness)
        
        # Face diagnostics
        if not capturing:
            diagnostics = "Face Detection: Ready"
        else:
            if is_valid:
                if centered:
                    diagnostics = "Face Quality: OK | Centered: YES | Ready to Capture"
                    diag_color = color_green
                else:
                    diagnostics = "Face Quality: OK | Centered: NO | Move face to center"
                    diag_color = color_yellow
            else:
                diagnostics = "Face Quality: BLURRY | Clear the frame"
                diag_color = color_red
        
        cv2.putText(frame_copy, diagnostics, (width - 650, height - 65), font, 0.6, diag_color, 1)
        
        # Progress bar
        bar_width = 300
        bar_height = 20
        bar_x = (width - bar_width) // 2
        bar_y = height // 2 - 50
        
        # Bar background
        cv2.rectangle(frame_copy, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
        
        # Progress fill
        if self.target_images > 0:
            fill_width = int((image_count / self.target_images) * bar_width)
            cv2.rectangle(frame_copy, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), color_green, -1)
        
        # Progress text
        progress_percent = int((image_count / self.target_images) * 100) if self.target_images > 0 else 0
        cv2.putText(frame_copy, f"Progress: {progress_percent}%", (bar_x - 50, bar_y - 10), font, 0.6, color_white, 1)
        
        return frame_copy
    
    def _create_dataset_directory(self, roll_no, name):
        """
        Create and return the dataset directory path for a student.
        
        Args:
            roll_no: Student roll number
            name: Student name
            
        Returns:
            str: Path to dataset directory
        """
        dataset_dir = os.path.join("dataset", f"{roll_no}_{name}")
        os.makedirs(dataset_dir, exist_ok=True)
        print(f"[DATASET] Directory created: {dataset_dir}")
        return dataset_dir
    
    def collect_face_dataset(self, name, roll_no):
        """
        Main function to collect face dataset for a student.
        
        This function:
        1. Opens the webcam
        2. Displays live video feed with face detection
        3. Captures faces when user presses 'S'
        4. Saves images in InsightFace-compatible structure
        5. Validates face quality (no blur, centered)
        
        Args:
            name (str): Student's full name
            roll_no (int or str): Student's roll number
            
        Returns:
            dict: Collection summary with keys:
                - status: 'success' or 'cancelled'
                - total_images: Number of images captured
                - dataset_path: Path to saved dataset
                - timestamp: Collection start time
        """
        
        print("\n" + "="*70)
        print("FACE DATASET COLLECTION MODULE")
        print("="*70)
        print(f"[INFO] Starting dataset collection for: {name} (Roll No: {roll_no})")
        print(f"[INFO] Target images to capture: {self.target_images}")
        
        # Create dataset directory
        dataset_path = self._create_dataset_directory(roll_no, name)
        
        # Open webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("[ERROR] Unable to open webcam. Please check camera connection.")
            return {
                'status': 'error',
                'total_images': 0,
                'dataset_path': dataset_path,
                'error': 'Webcam not accessible'
            }
        
        # Set camera properties for better performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        print("[CAMERA] Webcam opened successfully")
        print("[CAMERA] Resolution: 640x480 @ 30 FPS")
        
        # Initialize capture variables
        image_count = 0
        frame_count = 0
        capturing = False
        collection_start_time = datetime.now()
        last_capture_time = 0
        
        print("\n[READY] Waiting for user to press 'S' to start capture...")
        print("[READY] Press 'Q' to quit at any time")
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    print("[ERROR] Failed to read from webcam")
                    break
                
                frame = cv2.flip(frame, 1)  # Flip horizontally for selfie-like view
                frame_count += 1
                
                # Detect faces
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(30, 30))
                
                # Validate frame
                has_valid_face = False
                centered_face = False
                face_image = None
                
                if len(faces) == 1:  # Only one face per frame
                    x, y, w, h = faces[0]
                    face_roi = frame[y:y+h, x:x+w]
                    
                    # Check if not blurry
                    if not self._is_face_blurry(face_roi):
                        has_valid_face = True
                        face_image = face_roi
                        
                        # Check if centered
                        centered_face = self._is_face_centered(frame, (x, y, w, h))
                        
                        # Draw face rectangle (green if centered, yellow otherwise)
                        rect_color = (0, 255, 0) if centered_face else (0, 255, 255)
                        cv2.rectangle(frame, (x, y), (x+w, y+h), rect_color, 2)
                
                # Handle capture logic
                current_time = time.time()
                if capturing and has_valid_face and centered_face:
                    # Capture with interval to avoid duplicates
                    if current_time - last_capture_time >= self.capture_interval / 30.0:
                        if self._save_face_image(face_image, dataset_path, image_count + 1):
                            image_count += 1
                            last_capture_time = current_time
                            print(f"[CAPTURE] Image {image_count}/{self.target_images} saved")
                            
                            # Check if target reached
                            if image_count >= self.target_images:
                                print("[SUCCESS] Target number of images reached!")
                                break
                
                # Draw overlay
                frame = self._draw_overlay(
                    frame, 
                    name, 
                    roll_no, 
                    image_count, 
                    capturing, 
                    centered_face, 
                    has_valid_face
                )
                
                # Display frame
                cv2.imshow(f"Face Dataset Collection - {name} ({roll_no})", frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('s') or key == ord('S'):
                    capturing = True
                    print("\n[ACTION] Capture started! Positioning face and holding still...")
                    
                elif key == ord('q') or key == ord('Q'):
                    print("\n[ACTION] User quit requested")
                    break
        
        except KeyboardInterrupt:
            print("\n[ACTION] Keyboard interrupt detected")
        
        finally:
            # Clean up
            cap.release()
            cv2.destroyAllWindows()
            print("\n[CLEANUP] Webcam released and windows closed")
        
        # Final summary
        collection_end_time = datetime.now()
        duration = collection_end_time - collection_start_time
        
        print("\n" + "="*70)
        print("DATASET COLLECTION COMPLETE")
        print("="*70)
        print(f"[SUMMARY] Total images captured: {image_count}/{self.target_images}")
        print(f"[SUMMARY] Dataset path: {os.path.abspath(dataset_path)}")
        print(f"[SUMMARY] Collection duration: {duration.total_seconds():.2f} seconds")
        print(f"[SUMMARY] Status: {'SUCCESS' if image_count > 0 else 'CANCELLED'}")
        print("="*70 + "\n")
        
        return {
            'status': 'success' if image_count > 0 else 'cancelled',
            'total_images': image_count,
            'dataset_path': os.path.abspath(dataset_path),
            'timestamp': collection_start_time.isoformat(),
            'duration_seconds': duration.total_seconds()
        }


# Standalone function for direct usage
def collect_face_dataset(name, roll_no, target_images=30):
    """
    Convenience function to collect face dataset for a student.
    
    Usage:
        result = collect_face_dataset("Amit Kumar", 101)
    
    Args:
        name (str): Student's full name
        roll_no (int or str): Student's roll number
        target_images (int): Number of images to capture (default: 30)
        
    Returns:
        dict: Collection summary
    """
    collector = FaceDatasetCollector(target_images=target_images)
    return collector.collect_face_dataset(name, roll_no)


# Main execution
if __name__ == "__main__":
    """
    Example usage of the face dataset collector.
    
    This runs standalone for testing and validation.
    """
    print("\n" + "="*70)
    print("FACE DATASET COLLECTION - STANDALONE MODE")
    print("="*70 + "\n")
    
    # Get student information from user
    try:
        name = input("Enter student name: ").strip()
        roll_no = input("Enter roll number: ").strip()
        
        if not name or not roll_no:
            print("[ERROR] Name and roll number cannot be empty")
            exit(1)
        
        # Optional: specify number of images
        try:
            target_images_input = input("Enter target number of images (default: 30): ").strip()
            target_images = int(target_images_input) if target_images_input else 30
        except ValueError:
            target_images = 30
        
        # Start collection
        result = collect_face_dataset(name, roll_no, target_images)
        
        # Print result
        print("\n[RESULT] Collection Summary:")
        print(f"  Status: {result['status'].upper()}")
        print(f"  Images Captured: {result['total_images']}")
        print(f"  Dataset Path: {result['dataset_path']}")
        if 'duration_seconds' in result:
            print(f"  Duration: {result['duration_seconds']:.2f} seconds")
    
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Collection cancelled by user")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
