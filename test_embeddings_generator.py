"""
Test/Demo Script for Embedding Generator
========================================

This script demonstrates how to use the EmbeddingGenerator module
and validates that all components are working correctly.

Usage:
    python test_embeddings_generator.py
"""

import sys
from pathlib import Path


def test_imports():
    """Test if all required modules can be imported."""
    print("=" * 70)
    print("TEST 1: Checking Required Imports")
    print("=" * 70)
    
    try:
        import cv2
        print("✓ OpenCV (cv2) imported successfully")
    except ImportError as e:
        print(f"✗ OpenCV import failed: {e}")
        print("  Install with: pip install opencv-python")
        return False
    
    try:
        import numpy
        print("✓ NumPy imported successfully")
    except ImportError as e:
        print(f"✗ NumPy import failed: {e}")
        print("  Install with: pip install numpy")
        return False
    
    try:
        import insightface
        print("✓ InsightFace imported successfully")
    except ImportError as e:
        print(f"✗ InsightFace import failed: {e}")
        print("  Install with: pip install insightface")
        return False
    
    try:
        import onnxruntime
        print("✓ ONNXRuntime imported successfully")
    except ImportError as e:
        print(f"✗ ONNXRuntime import failed: {e}")
        print("  Install with: pip install onnxruntime")
        return False
    
    print()
    return True


def test_module_import():
    """Test if the embedding generator module can be imported."""
    print("=" * 70)
    print("TEST 2: Checking Embedding Generator Module")
    print("=" * 70)
    
    try:
        from vision.generate_embeddings import (
            EmbeddingGenerator,
            generate_face_embeddings,
            load_known_faces
        )
        print("✓ EmbeddingGenerator class imported successfully")
        print("✓ generate_face_embeddings function imported successfully")
        print("✓ load_known_faces function imported successfully")
    except ImportError as e:
        print(f"✗ Module import failed: {e}")
        return False
    
    print()
    return True


def test_generator_initialization():
    """Test if embedding generator can be initialized."""
    print("=" * 70)
    print("TEST 3: Checking Embedding Generator Initialization")
    print("=" * 70)
    
    try:
        from vision.generate_embeddings import EmbeddingGenerator
        
        print("Initializing EmbeddingGenerator...")
        generator = EmbeddingGenerator(
            model_name='buffalo_l',
            data_dir='dataset',
            output_dir='data'
        )
        print("✓ EmbeddingGenerator initialized successfully")
        print(f"  Model: {generator.model_name}")
        print(f"  Dataset directory: {generator.data_dir.absolute()}")
        print(f"  Output directory: {generator.output_dir.absolute()}")
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False
    
    print()
    return True


def test_directory_structure():
    """Test if directory structure is correct."""
    print("=" * 70)
    print("TEST 4: Checking Directory Structure")
    print("=" * 70)
    
    dataset_dir = Path("dataset")
    if dataset_dir.exists():
        print(f"✓ Dataset directory exists: {dataset_dir.absolute()}")
    else:
        print(f"✗ Dataset directory not found: {dataset_dir.absolute()}")
        return False
    
    data_dir = Path("data")
    if data_dir.exists():
        print(f"✓ Data directory exists: {data_dir.absolute()}")
    else:
        print(f"✗ Data directory not found: {data_dir.absolute()}")
        return False
    
    vision_dir = Path("vision")
    if vision_dir.exists():
        print(f"✓ Vision directory exists: {vision_dir.absolute()}")
    else:
        print(f"✗ Vision directory not found: {vision_dir.absolute()}")
        return False
    
    print()
    return True


def test_student_folders():
    """Check if student folders exist in dataset directory."""
    print("=" * 70)
    print("TEST 5: Checking Student Folders")
    print("=" * 70)
    
    dataset_dir = Path("dataset")
    
    if not dataset_dir.exists():
        print(f"✗ Dataset directory not found")
        return False
    
    student_folders = [d for d in dataset_dir.iterdir() 
                      if d.is_dir() and '_' in d.name]
    
    if not student_folders:
        print("⚠ No student folders found in dataset directory")
        print("  Expected format: dataset/<roll_no>_<name>/")
        print("  Examples: dataset/101_Amit/, dataset/102_Rahul/")
        print("\n  This is not an error if you haven't collected datasets yet.")
        return True
    
    print(f"✓ Found {len(student_folders)} student folders:")
    for folder in sorted(student_folders)[:5]:
        image_count = len([f for f in folder.iterdir() 
                          if f.suffix.lower() in {'.jpg', '.jpeg', '.png'}])
        print(f"  - {folder.name}: {image_count} images")
    
    if len(student_folders) > 5:
        print(f"  ... and {len(student_folders) - 5} more")
    
    print()
    return True


def test_embeddings_file():
    """Check if embeddings file exists."""
    print("=" * 70)
    print("TEST 6: Checking Embeddings File")
    print("=" * 70)
    
    embeddings_file = Path("data/face_embeddings.pkl")
    
    if embeddings_file.exists():
        print(f"✓ Embeddings file exists: {embeddings_file.absolute()}")
        print(f"  File size: {embeddings_file.stat().st_size / 1024:.2f} KB")
        
        # Try to load and verify
        try:
            from vision.generate_embeddings import load_known_faces
            known_faces = load_known_faces()
            
            if known_faces:
                print(f"✓ Successfully loaded {len(known_faces)} student embeddings")
                
                # Show sample
                sample = list(known_faces.items())[0]
                roll_no, data = sample
                print(f"\n  Sample: {data['name']} (Roll No: {roll_no})")
                print(f"    Embedding shape: {data['embedding'].shape}")
                print(f"    Embedding type: {type(data['embedding'])}")
                
                return True
            else:
                print("⚠ Could not load embeddings (corrupted file?)")
                return False
        except Exception as e:
            print(f"✗ Error loading embeddings: {e}")
            return False
    else:
        print(f"⚠ Embeddings file not found: {embeddings_file.absolute()}")
        print("  This is expected if you haven't generated embeddings yet.")
        return True
    
    print()
    return True


def display_usage_examples():
    """Display usage examples."""
    print("=" * 70)
    print("USAGE EXAMPLES")
    print("=" * 70)
    
    print("\n1. GENERATE EMBEDDINGS:")
    print("   $ python vision/generate_embeddings.py")
    print("   or")
    print("   $ python -c \"from vision.generate_embeddings import generate_face_embeddings; generate_face_embeddings()\"")
    
    print("\n2. LOAD EMBEDDINGS IN PYTHON:")
    print("   from vision.generate_embeddings import load_known_faces")
    print("   known_faces = load_known_faces()")
    print("   for roll_no, data in known_faces.items():")
    print("       print(f'{data[\"name\"]} (Roll No: {roll_no})')")
    
    print("\n3. CUSTOM CONFIGURATION:")
    print("   from vision.generate_embeddings import generate_face_embeddings")
    print("   result = generate_face_embeddings(")
    print("       model_name='buffalo_l',")
    print("       data_dir='dataset',")
    print("       output_dir='data'")
    print("   )")
    print("   print(f'Success: {result[\"status\"]}')")
    
    print("\n4. USING THE CLASS:")
    print("   from vision.generate_embeddings import EmbeddingGenerator")
    print("   generator = EmbeddingGenerator()")
    print("   result = generator.generate_face_embeddings()")
    
    print()


def display_next_steps():
    """Display next steps."""
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    
    print("\n1. PHASE 7 — STEP 2: Generate Embeddings")
    print("   $ python vision/generate_embeddings.py")
    print("   or")
    print("   >>> from vision.generate_embeddings import generate_face_embeddings")
    print("   >>> result = generate_face_embeddings()")
    
    print("\n2. PHASE 7 — STEP 3: Build Recognition Engine")
    print("   Create vision/face_recognition.py")
    print("   Use load_known_faces() to load embeddings")
    print("   Implement real-time face matching")
    
    print("\n3. PHASE 7 — STEP 4+: Attendance Integration")
    print("   Integrate with attendance event engine")
    print("   Build Streamlit web UI")
    print("   Deploy to production")
    
    print()


def main():
    """Run all tests."""
    print("\n")
    print("█" * 70)
    print("EMBEDDING GENERATOR - DIAGNOSTIC TEST SUITE")
    print("█" * 70)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Module", test_module_import),
        ("Initialization", test_generator_initialization),
        ("Directories", test_directory_structure),
        ("Student Folders", test_student_folders),
        ("Embeddings File", test_embeddings_file),
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
        print("Your system is ready for embedding generation.")
        display_usage_examples()
        display_next_steps()
        return 0
    else:
        print("⚠ SOME TESTS DID NOT PASS")
        print("Please review the output above and fix any issues.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
