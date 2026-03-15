from faster_whisper import WhisperModel
import sys

def download():
    model_size = "base"
    print(f"Downloading/Verifying Whisper model '{model_size}'...")
    print("This may take a moment depending on your connection (approx 150MB).")
    try:
        # This will download the model to the default cache directory
        WhisperModel(model_size, device="cpu", compute_type="int8")
        print("\nSuccess! Model is ready.")
    except Exception as e:
        print(f"\nError downloading model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download()
