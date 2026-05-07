import sys
import os

# Ensure the vision package can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vision.face_recognition_engine import RealTimeFaceRecognitionEngine

def main():
    print("=" * 60)
    print("STANDALONE TESTING MODULE (LIVE CAMERA)")
    print("=" * 60)
    print("This will open a standalone window to test the recognition engine.")
    print("Make sure you have trained the model using train.py first.")
    print("\nControls:")
    print("  Press 'Q' to quit the camera window.")
    print("  Press 'S' to save a screenshot.")
    print("=" * 60 + "\n")
    
    try:
        # Initialize and start the engine
        engine = RealTimeFaceRecognitionEngine()
        
        # We set frame_resize_scale to a slightly lower value for better testing FPS
        engine.start_recognition(camera_index=0, frame_resize_scale=0.6)
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] Missing File: {e}")
        print("Please run `python train.py` first to generate the necessary embeddings!")
    except Exception as e:
        print(f"\n[ERROR] Testing failed: {e}")
        print("Please ensure your camera is connected and not being used by another application.")

if __name__ == "__main__":
    main()
