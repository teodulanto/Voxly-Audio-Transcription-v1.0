# 🎙️ Voxly — Voice Dictation for Windows

Voxly is a **free, offline, premium** voice dictation tool for Windows. Press a hotkey, speak, and your words are instantly typed anywhere — emails, documents, chat, forms.

Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI Whisper AI, runs fully locally).

---

## ✨ Features

- 🎯 **Universal** — works in any app (Word, Chrome, Excel, etc.)
- 🔒 **100% Offline** — your voice never leaves your machine
- ⚡ **Fast** — near real-time transcription
- 🎨 **Minimal HUD** — sleek floating pill with voice-reactive visualizer
- 🤫 **Silent** — lives in the system tray, launches on boot
- 🌍 **Multi-language** — auto-detects your language

---

## 🚀 Installation

> **Requires Python 3.9+**

1. Clone this repo:
   ```bash
   git clone https://github.com/teodulanto/Rec_Au_v01.git
   cd Rec_Au_v01
   ```

2. Run the one-step installer:
   ```bash
   python install_voxly.py
   ```
   This will: set up a virtual environment, install all dependencies, download the AI model, create a Desktop shortcut, and configure Windows auto-startup.

---

## 🎮 How to Use

| Action | Gesture |
|--------|---------|
| Start recording | `Ctrl + Alt + V` |
| Stop & paste text | `Ctrl + Alt + V` |
| Exit app completely | Right-click tray icon → **Exit** |

---

## ⚙️ Configuration

Edit `settings.json` (created on first run) to customize:

```json
{
    "hotkey": "ctrl+alt+v",
    "model_size": "base",
    "language": null,
    "compute_type": "int8"
}
```

- `model_size`: `"tiny"` (fastest) · `"base"` (default) · `"small"` / `"medium"` (more accurate)
- `language`: `null` for auto-detect, or `"es"`, `"en"`, `"fr"`, etc.

---

## 📁 Project Structure

```
Rec_Au_v01/
├── main.py              # App entry point
├── hud_window.py        # Floating HUD (tkinter)
├── audio_recorder.py    # Microphone capture with volume feedback
├── transcriber.py       # Whisper AI transcription
├── hotkey_manager.py    # Global hotkey listener
├── input_simulator.py   # Auto-paste via clipboard
├── settings_manager.py  # Persistent configuration
├── generate_icon.py     # Generates the red-dot .ico / .png icon
├── download_model.py    # Pre-downloads the Whisper model
├── install_voxly.py     # One-step setup installer
├── Voxly.vbs            # Silent Windows launcher (no console window)
└── start_voxly.bat      # Bat file called by the VBS launcher
```

---

## 📄 License

MIT — free to use, modify, and share.
