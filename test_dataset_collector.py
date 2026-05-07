"""
Test/Demo Script for Face Dataset Collector
=============================================

This script demonstrates how to use the FaceDatasetCollector module
and validates that all components are working correctly.

Usage:
    python test_dataset_collector.py
"""

import sys
import os
from pathlib import Path


def test_imports():
    """Test if all required modules can be imported."""
    print("=" * 70)
    print("TEST 1: Checking Required Imports")
    print("=" * 70)
    
    try:
        import cv2
        print("✓ OpenCV (cv2) imported successfully")
        print(f"  Version: {cv2.__version__}")
    except ImportError as e:
        print(f"✗ OpenCV import failed: {e}")
        print("  Install with: pip install opencv-python")
        return False
    
    try:
        import numpy
        print("✓ NumPy imported successfully")
        print(f"  Version: {numpy.__version__}")
    except ImportError as e:
        print(f"✗ NumPy import failed: {e}")
        print("  Install with: pip install numpy")
        return False
    
    print()
    return True


def test_module_import():
    """Test if the dataset_collector module can be imported."""
    print("=" * 70)
    print("TEST 2: Checking Dataset Collector Module")
    print("=" * 70)
    
    try:
        from vision.dataset_collector import FaceDatasetCollector, collect_face_dataset
        print("✓ FaceDatasetCollector class imported successfully")
        print("✓ collect_face_dataset function imported successfully")
    except ImportError as e:
        print(f"✗ Module import failed: {e}")
        return False
    
    print()
    return True


def test_face_detector_initialization():
    """Test if face detector can be initialized."""
    print("=" * 70)
    print("TEST 3: Checking Face Detection Initialization")
    print("=" * 70)
    
    try:
        from vision.dataset_collector import FaceDatasetCollector
        
        print("Initializing FaceDatasetCollector...")
        collector = FaceDatasetCollector(target_images=30)
        print("✓ FaceDatasetCollector initialized successfully")
        print(f"  Target images: {collector.target_images}")
        print(f"  Image size: {collector.image_size}")
        print(f"  Blur threshold: {collector.blur_threshold}")
        print(f"  Capture interval: {collector.capture_interval}")
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False
    
    print()
    return True


def test_directory_structure():
    """Test if directory structure is created correctly."""
    print("=" * 70)
    print("TEST 4: Checking Directory Structure")
    print("=" * 70)
    
    base_dir = Path("dataset")
    
    if base_dir.exists():
        print(f"✓ Dataset directory exists: {base_dir.absolute()}")
    else:
        print(f"✗ Dataset directory not found: {base_dir.absolute()}")
        return False
    
    vision_dir = Path("vision")
    if vision_dir.exists():
        print(f"✓ Vision directory exists: {vision_dir.absolute()}")
    else:
        print(f"✗ Vision directory not found: {vision_dir.absolute()}")
        return False
    
    print()
    return True


def test_camera_availability():
    """Test if camera is available."""
    print("=" * 70)
    print("TEST 5: Checking Camera Availability")
    print("=" * 70)
    
    try:
        import cv2
        print("Attempting to access webcam...")
        cap = cv2.VideoCapture(0)
        
        if cap.isOpened():
            print("✓ Webcam is available and accessible")
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret:
                print(f"✓ Successfully captured frame")
                print(f"  Frame dimensions: {frame.shape[1]}×{frame.shape[0]} pixels")
            else:
                print("⚠ Webcam is accessible but failed to capture frame")
            
            cap.release()
        else:
            print("✗ Webcam is NOT available or NOT accessible")
            print("  Possible causes:")
            print("  - Camera not connected")
            print("  - Camera already in use by another application")
            print("  - Insufficient permissions")
            return False
            
    except Exception as e:
        print(f"✗ Camera check failed: {e}")
        return False
    
    print()
    return True


def display_usage_examples():
    """Display usage examples."""
    print("=" * 70)
    print("USAGE EXAMPLES")
    print("=" * 70)
    
    print("\n1. STANDALONE EXECUTION:")
    print("   $ python vision/dataset_collector.py")
    print("   Then enter student name and roll number when prompted")
    
    print("\n2. IMPORT IN PYTHON:")
    print("   from vision.dataset_collector import collect_face_dataset")
    print("   result = collect_face_dataset('Amit Kumar', 101)")
    print("   print(result)")
    
    print("\n3. CUSTOM CONFIGURATION:")
    print("   from vision.dataset_collector import FaceDatasetCollector")
    print("   collector = FaceDatasetCollector(")
    print("       target_images=50,")
    print("       image_size=(256, 256),")
    print("       blur_threshold=80,")
    print("       capture_interval=3")
    print("   )")
    print("   result = collector.collect_face_dataset('Priya Singh', 102)")
    
    print("\n4. BATCH COLLECTION:")
    print("   students = [")
    print("       ('Amit Kumar', 101),")
    print("       ('Priya Singh', 102),")
    print("       ('Rohan Patel', 103)")
    print("   ]")
    print("   for name, roll_no in students:")
    print("       result = collect_face_dataset(name, roll_no)")
    print("       print(f'Collected {result[\"total_images\"]} images')")
    
    print()


def display_quick_checklist():
    """Display quick checklist for first-time users."""
    print("=" * 70)
    print("PRE-COLLECTION CHECKLIST")
    print("=" * 70)
    
    checklist = [
        ("Webcam is connected and working", "TEST 5"),
        ("Good lighting in the room", "Manual check"),
        ("Clean webcam lens", "Manual check"),
        ("Sufficient disk space (~3-5 MB per student)", "Manual check"),
        ("No other apps using webcam", "Manual check"),
        ("All dependencies installed", "TEST 1"),
        ("Module can be imported", "TEST 2"),
    ]
    
    for item, source in checklist:
        print(f"  ☐ {item}")
        print(f"    (Verified by: {source})")
    
    print()


def main():
    """Run all tests."""
    print("\n")
    print("█" * 70)
    print("FACE DATASET COLLECTOR - DIAGNOSTIC TEST SUITE")
    print("█" * 70)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Module", test_module_import),
        ("Initialization", test_face_detector_initialization),
        ("Directories", test_directory_structure),
        ("Camera", test_camera_availability),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ Test '{test_name}' encountered an error: {e}\n")
            results[test_name] = False
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print()
    print(f"Total: {passed_tests}/{total_tests} tests passed")
    print()
    
    if passed_tests == total_tests:
        print("✓ ALL TESTS PASSED!")
        print("Your system is ready to collect face datasets.")
        display_usage_examples()
        display_quick_checklist()
        return 0
    else:
        print("✗ SOME TESTS FAILED!")
        print("Please fix the issues before collecting datasets.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
