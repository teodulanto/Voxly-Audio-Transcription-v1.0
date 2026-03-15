import sounddevice as sd
import numpy as np
import wave
import os
import tempfile


class AudioRecorder:
    def __init__(self, samplerate=16000):
        self.samplerate = samplerate
        self.recording = False
        self.audio_data = []
        self.temp_file = None
        self.on_volume_callback = None

    def start_recording(self, on_volume=None):
        self.recording = True
        self.audio_data = []
        self.on_volume_callback = on_volume

        def callback(indata, frames, time, status):
            if self.recording:
                self.audio_data.append(indata.copy())
                if self.on_volume_callback:
                    rms = float(np.sqrt(np.mean(indata ** 2)))
                    self.on_volume_callback(rms)

        self.stream = sd.InputStream(
            samplerate=self.samplerate, channels=1, callback=callback
        )
        self.stream.start()

    def stop_recording(self):
        self.recording = False
        if hasattr(self, "stream"):
            self.stream.stop()
            self.stream.close()

        if not self.audio_data:
            return None

        full_audio = np.concatenate(self.audio_data, axis=0)
        fd, self.temp_file = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        with wave.open(self.temp_file, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes((full_audio * 32767).astype(np.int16).tobytes())

        return self.temp_file

    def cleanup(self):
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception:
                pass
            self.temp_file = None
