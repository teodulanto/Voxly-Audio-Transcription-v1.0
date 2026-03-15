import threading
import os
import sys
import time
import ctypes
from PIL import Image, ImageDraw
import pystray
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from input_simulator import InputSimulator
from settings_manager import SettingsManager
from hotkey_manager import HotkeyManager
from hud_window import HudWindow


class VoiceDictationApp:
    def __init__(self):
        # Critical: Tell Windows this is its own app (not python.exe)
        # This makes the taskbar show our custom icon
        try:
            myappid = 'antigravity.voicedictation.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        self.settings = SettingsManager()
        self.recorder = AudioRecorder()
        self.transcriber = None
        self.simulator = InputSimulator()
        self.hotkey_manager = HotkeyManager(
            hotkey=self.settings.get("hotkey"),
            callback=self.toggle_recording
        )

        self.hud = None
        self.tray_icon = None
        self.is_recording = False
        self.is_processing = False
        self.model_loaded = False
        self.should_exit = False

        # Use .ico for best Windows icon rendering
        base = os.path.dirname(os.path.abspath(__file__))
        ico = os.path.join(base, "app_icon.ico")
        png = os.path.join(base, "app_icon.png")
        self.icon_path = ico if os.path.exists(ico) else png

    def toggle_recording(self):
        if self.is_processing or self.should_exit:
            return

        if not self.is_recording:
            if self.hud:
                self.hud.show()
                if not self.model_loaded:
                    self.hud.update_status('loading', 'Loading Model...', 'Using your cached model')
            threading.Thread(target=self.start_recording_flow, daemon=True).start()
        else:
            self.stop_recording()

    def start_recording_flow(self):
        try:
            if self.transcriber is None:
                self.transcriber = Transcriber(
                    model_size=self.settings.get("model_size"),
                    compute_type=self.settings.get("compute_type")
                )
                self.model_loaded = True

            self.is_recording = True
            
            # Callback to update HUD volume
            def on_volume(level):
                if self.hud:
                    self.hud.set_volume_level(level)

            self.recorder.start_recording(on_volume=on_volume)
            if self.hud:
                self.hud.update_status('recording', 'Recording...', 'Press hotkey to stop')
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.is_recording = False

    def stop_recording(self):
        self.is_recording = False
        self.is_processing = True

        if self.hud:
            self.hud.update_status('processing', 'Processing...', 'Transcribing...')

        threading.Thread(target=self.process_audio, daemon=True).start()

    def process_audio(self):
        try:
            audio_path = self.recorder.stop_recording()
            if audio_path and self.transcriber:
                text = self.transcriber.transcribe(audio_path)
                if text:
                    if self.hud:
                        self.hud.hide()
                    time.sleep(0.1) # Small buffer for OS focus
                    self.simulator.simulate_pasting(text)
                else:
                    if self.hud:
                        self.hud.update_status('standby', 'No voice detected', 'Try again')
                        time.sleep(1.5)
                        self.hud.hide()
                self.recorder.cleanup()
        except Exception as e:
            print(f"Error in process_audio: {e}")
            if self.hud:
                self.hud.hide()
        finally:
            self.is_processing = False
            if self.hud:
                self.hud.set_preview('')

    def create_tray_icon(self):
        if os.path.exists(self.icon_path):
            image = Image.open(self.icon_path).convert("RGBA")
            # Ensure it's square for tray
            if image.size[0] != image.size[1]:
                size = min(image.size)
                image = image.resize((64, 64), Image.LANCZOS)
        else:
            image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
            dc = ImageDraw.Draw(image)
            dc.ellipse([5, 5, 59, 59], fill=(239, 68, 68, 255))

        menu = pystray.Menu(
            pystray.MenuItem("Exit", self.quit_app)
        )
        self.tray_icon = pystray.Icon(
            "VoiceDictation", image, "Voice Dictation - Running", menu
        )
        self.tray_icon.run()

    def quit_app(self, *args):
        self.should_exit = True
        self.hotkey_manager.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        if self.hud:
            self.hud.destroy()
        sys.exit(0)

    def run(self):
        # Build the HUD (tkinter runs in its own daemon thread)
        self.hud = HudWindow(icon_path=self.icon_path)
        self.hud.start()

        # Start the system tray in another thread
        threading.Thread(target=self.create_tray_icon, daemon=True).start()

        # Start hotkey listener
        self.hotkey_manager.start()

        # Block the main thread so the process stays alive
        try:
            while not self.should_exit:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.quit_app()


if __name__ == "__main__":
    app = VoiceDictationApp()
    app.run()
