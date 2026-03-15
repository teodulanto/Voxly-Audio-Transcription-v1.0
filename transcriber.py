from faster_whisper import WhisperModel
import os


class Transcriber:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path):
        if not audio_path or not os.path.exists(audio_path):
            return ""
        try:
            segments, _ = self.model.transcribe(audio_path, beam_size=5)
            return " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
