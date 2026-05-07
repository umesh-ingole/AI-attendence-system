import sys
import os

# Ensure the vision package can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vision.generate_embeddings import generate_face_embeddings

def main():
    print("=" * 60)
    print("STANDALONE TRAINING MODULE")
    print("=" * 60)
    print("Scanning 'dataset/' folder and generating AI embeddings...")
    print("This trains the AI to recognize the newly added students.\n")
    
    # Run the embedding generation which acts as "training" our model
    result = generate_face_embeddings(verbose=True)
    
    if result.get('status') in ['success', 'partial_success']:
        print("\n" + "=" * 60)
        print("TRAINING SUCCESSFUL! 🎉")
        print("The AI model has been updated with the latest faces.")
        print(f"Total students trained: {result.get('successful_students')}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("TRAINING FAILED! ❌")
        print(f"Error: {result.get('error')}")
        print("=" * 60)

if __name__ == "__main__":
    main()
