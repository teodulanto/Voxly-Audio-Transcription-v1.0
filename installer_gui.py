"""
VoxlyInstaller.exe — Self-Contained GUI Installer
====================================================
Fully autonomous: detects Python, downloads it if missing (with user consent),
installs all Voxly dependencies, and registers the app in Windows.
No technical knowledge required from the user.
"""
import sys
import os
import subprocess
import threading
import shutil
import winreg
import urllib.request
import zipfile
import tkinter as tk
from tkinter import font as tkfont, messagebox

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME    = "Voxly"
APP_VERSION = "1.0.0"
PUBLISHER   = "Antigravity"

INSTALL_DIR   = os.path.join(os.environ["LOCALAPPDATA"], APP_NAME)
PYTHON_EMBED  = os.path.join(INSTALL_DIR, "python")          # Embedded Python folder
LAUNCHER      = os.path.join(INSTALL_DIR, "Voxly.vbs")
UNINSTALLER   = os.path.join(INSTALL_DIR, "uninstall_voxly.py")
ICON_ICO      = os.path.join(INSTALL_DIR, "app_icon.ico")

# Python Embeddable — 64-bit, Python 3.11 (stable & widely compatible)
PY_EMBED_URL  = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
GET_PIP_URL   = "https://bootstrap.pypa.io/get-pip.py"
PY_EMBED_ZIP  = os.path.join(INSTALL_DIR, "_python_embed.zip")
GET_PIP_PY    = os.path.join(PYTHON_EMBED, "get-pip.py")

PACKAGES = [
    "faster-whisper", "sounddevice", "numpy",
    "keyboard", "pyautogui", "pystray", "Pillow", "pyperclip",
]

# Source dir — PyInstaller _MEIPASS or local folder
if getattr(sys, "frozen", False):
    SRC_DIR = sys._MEIPASS
else:
    SRC_DIR = os.path.dirname(os.path.abspath(__file__))

APP_FILES = [
    "main.py", "hud_window.py", "audio_recorder.py", "transcriber.py",
    "hotkey_manager.py", "input_simulator.py", "settings_manager.py",
    "generate_icon.py", "download_model.py",
    "app_icon.png", "app_icon.ico",
]

# ── Python Detection ──────────────────────────────────────────────────────────
def _find_system_python():
    """Return path to a usable Python 3.9+ exe, or None."""
    candidates = [sys.executable] if not getattr(sys, "frozen", False) else []
    for name in ("python", "python3", "py"):
        try:
            out = subprocess.check_output(
                [name, "--version"], stderr=subprocess.STDOUT, timeout=5
            ).decode().strip()
            if out.startswith("Python 3."):
                ver = tuple(int(x) for x in out.split()[1].split(".")[:2])
                if ver >= (3, 9):
                    return shutil.which(name)
        except Exception:
            pass
    # Check common install locations
    for base in [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python"),
        r"C:\Python311", r"C:\Python310", r"C:\Python39",
    ]:
        for root, dirs, files in os.walk(base or ""):
            for f in files:
                if f.lower() in ("python.exe", "python3.exe"):
                    return os.path.join(root, f)
    return None


# ── GUI ───────────────────────────────────────────────────────────────────────
class InstallerApp:
    BG    = "#0f0f0f"
    CARD  = "#1a1a1a"
    ACCT  = "#3b82f6"
    GREEN = "#22c55e"
    RED   = "#ef4444"
    FG    = "#ffffff"
    GRAY  = "#9ca3af"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.python_exe = None     # resolved after detection
        self.root.title(f"Voxly {APP_VERSION} Setup")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        W, H = 540, 440
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        try:
            ico = os.path.join(SRC_DIR, "app_icon.ico")
            if os.path.exists(ico):
                root.iconbitmap(ico)
        except Exception:
            pass

        self._build_ui()
        # Run Python detection in background so UI shows immediately
        threading.Thread(target=self._detect_python, daemon=True).start()

    # ── UI Builder ────────────────────────────────────────────────────────────
    def _build_ui(self):
        f_big   = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        f_body  = tkfont.Font(family="Segoe UI", size=10)
        f_small = tkfont.Font(family="Segoe UI", size=9)
        self._f_log = tkfont.Font(family="Consolas", size=9)

        # Header
        hdr = tk.Frame(self.root, bg=self.BG, pady=22)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎙  Voxly", font=f_big,
                 fg=self.FG, bg=self.BG).pack()
        tk.Label(hdr, text="AI Voice Dictation  •  Free & Offline",
                 font=f_small, fg=self.GRAY, bg=self.BG).pack(pady=(3, 0))

        # Install path card
        p = tk.Frame(self.root, bg=self.CARD, padx=20, pady=10)
        p.pack(fill="x", padx=24)
        tk.Label(p, text="Install location:", font=f_small,
                 fg=self.GRAY, bg=self.CARD).pack(anchor="w")
        tk.Label(p, text=INSTALL_DIR, font=f_small,
                 fg=self.FG, bg=self.CARD).pack(anchor="w")

        # Log box
        lf = tk.Frame(self.root, bg=self.CARD, padx=10, pady=8)
        lf.pack(fill="both", expand=True, padx=24, pady=(10, 0))
        self.log = tk.Text(lf, wrap="word", font=self._f_log,
                           bg="#0a0a0a", fg=self.GRAY,
                           relief="flat", bd=0, state="disabled", height=10)
        self.log.pack(fill="both", expand=True)
        self.log.tag_config("ok",  foreground=self.GREEN)
        self.log.tag_config("err", foreground=self.RED)
        self.log.tag_config("hd",  foreground=self.ACCT)
        self.log.tag_config("dim", foreground="#555555")

        # Progress bar
        pb_f = tk.Frame(self.root, bg=self.BG, pady=8)
        pb_f.pack(fill="x", padx=24)
        self.pb_cv = tk.Canvas(pb_f, height=5, bg="#2d2d2d",
                               highlightthickness=0)
        self.pb_cv.pack(fill="x")
        self._pb_bar = None

        # Buttons
        bf = tk.Frame(self.root, bg=self.BG, padx=24, pady=12)
        bf.pack(fill="x")
        self.status_lbl = tk.Label(bf, text="Checking system...",
                                   font=f_small, fg=self.GRAY, bg=self.BG)
        self.status_lbl.pack(side="left")
        self.close_btn = tk.Button(bf, text=" Cancel ", font=f_body,
                                   bg="#2d2d2d", fg=self.FG, relief="flat",
                                   padx=10, cursor="hand2",
                                   command=self.root.destroy)
        self.close_btn.pack(side="right", padx=(6, 0))
        self.install_btn = tk.Button(bf, text="  Install  ", font=f_body,
                                     bg="#2d2d2d", fg="#555555",
                                     relief="flat", padx=14, state="disabled",
                                     cursor="hand2",
                                     command=self._on_install_click)
        self.install_btn.pack(side="right")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _log(self, msg, tag=""):
        def _do():
            self.log.config(state="normal")
            self.log.insert("end", msg + "\n", tag)
            self.log.see("end")
            self.log.config(state="disabled")
        self.root.after(0, _do)

    def _status(self, msg):
        self.root.after(0, lambda: self.status_lbl.config(text=msg))

    def _progress(self, pct):
        def _do():
            w = self.pb_cv.winfo_width()
            if self._pb_bar:
                self.pb_cv.delete(self._pb_bar)
            self._pb_bar = self.pb_cv.create_rectangle(
                0, 0, int(w * pct), 5,
                fill=self.ACCT, outline="")
        self.root.after(0, _do)

    def _enable_install(self):
        self.root.after(0, lambda: self.install_btn.config(
            state="normal", bg=self.ACCT, fg=self.FG))

    # ── Python Detection ──────────────────────────────────────────────────────
    def _detect_python(self):
        self._log("Scanning for Python installation...", "hd")
        found = _find_system_python()
        if found:
            self.python_exe = found
            self._log(f"  Found: {found}", "ok")
            self._status("Python found. Ready to install.")
        else:
            self._log("  Python not found on this PC.", "dim")
            self._log("  Voxly will download a lightweight Python (~12 MB).", "dim")
            self._status("Python not found — will download automatically.")
        self._enable_install()
        self._progress(0.03)

    # ── Install trigger ───────────────────────────────────────────────────────
    def _on_install_click(self):
        self.install_btn.config(state="disabled",
                                text=" Installing... ", bg="#2d2d2d", fg="#555555")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        try:
            self._run_all_steps()
            self._finish_success()
        except Exception as exc:
            self._log(f"\nInstallation failed: {exc}", "err")
            self._status("Installation failed.")
            self.root.after(0, lambda: self.install_btn.config(
                state="normal", bg=self.RED, fg=self.FG, text=" Retry "))

    # ── Step runner ───────────────────────────────────────────────────────────
    def _run_all_steps(self):
        steps = [
            (0.08, "Copying files...",               self._step_copy),
            (0.20, "Setting up Python...",           self._step_python),
            (0.45, "Installing AI packages...",      self._step_packages),
            (0.62, "Generating icon...",             self._step_icon),
            (0.80, "Downloading voice model...",     self._step_model),
            (0.88, "Writing uninstaller...",         self._step_uninstaller),
            (0.93, "Registering application...",     self._step_registry),
            (0.98, "Creating shortcuts...",          self._step_shortcuts),
            (1.00, "Done",                           lambda: None),
        ]
        for pct, msg, fn in steps:
            self._status(msg)
            self._log(f"\n>> {msg}", "hd")
            fn()
            self._progress(pct)

    # ── Steps ─────────────────────────────────────────────────────────────────
    def _step_copy(self):
        os.makedirs(INSTALL_DIR, exist_ok=True)
        for f in APP_FILES:
            src = os.path.join(SRC_DIR, f)
            dst = os.path.join(INSTALL_DIR, f)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                self._log(f"  copied {f}", "ok")
        # Write launcher VBS
        vbs = (
            'Dim sDir, objShell\r\n'
            f'sDir = "{INSTALL_DIR}"\r\n'
            'Set objShell = CreateObject("WScript.Shell")\r\n'
            'objShell.Run "cmd /c cd /d """ & sDir & """ && start_voxly.bat", 0, False\r\n'
        )
        with open(LAUNCHER, "w") as f:
            f.write(vbs)

    def _step_python(self):
        if self.python_exe:
            self._log(f"  Using system Python: {self.python_exe}", "ok")
            # Create venv from system python
            venv_dir = os.path.join(INSTALL_DIR, "venv")
            if not os.path.isdir(venv_dir):
                result = subprocess.run(
                    [self.python_exe, "-m", "venv", venv_dir],
                    capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"venv failed: {result.stderr}")
            self.py = os.path.join(venv_dir, "Scripts", "python.exe")
            self.pythonw = os.path.join(venv_dir, "Scripts", "pythonw.exe")
            self._log("  Virtual environment ready", "ok")
        else:
            self._bootstrap_embedded_python()

    def _bootstrap_embedded_python(self):
        """Download and configure Python Embeddable if no system Python."""
        os.makedirs(PYTHON_EMBED, exist_ok=True)
        py_exe = os.path.join(PYTHON_EMBED, "python.exe")

        if not os.path.exists(py_exe):
            self._log("  Downloading Python 3.11 Embeddable (~12 MB)...", "dim")
            self._download_with_progress(PY_EMBED_URL, PY_EMBED_ZIP, label="  Python")
            self._log("  Extracting Python...", "dim")
            with zipfile.ZipFile(PY_EMBED_ZIP, "r") as z:
                z.extractall(PYTHON_EMBED)
            os.remove(PY_EMBED_ZIP)
            self._log("  Python extracted.", "ok")

            # Enable site-packages in the embeddable distribution
            pth_files = [f for f in os.listdir(PYTHON_EMBED) if f.endswith("._pth")]
            for pf in pth_files:
                path = os.path.join(PYTHON_EMBED, pf)
                with open(path) as fh:
                    content = fh.read()
                # Uncomment `import site`
                content = content.replace("#import site", "import site")
                with open(path, "w") as fh:
                    fh.write(content)

            # Download and install pip
            self._log("  Installing pip...", "dim")
            urllib.request.urlretrieve(GET_PIP_URL, GET_PIP_PY)
            subprocess.run([py_exe, GET_PIP_PY, "-q"],
                           capture_output=True, cwd=PYTHON_EMBED)
            os.remove(GET_PIP_PY)
            self._log("  pip installed.", "ok")

        self.py      = py_exe
        self.pythonw = py_exe   # no pythonw in embeddable, use python.exe
        # Update start_voxly.bat to use embedded python silently via wscript wrapper
        _bat = (
            f'@echo off\r\n'
            f'cd /d "{INSTALL_DIR}"\r\n'
            f'start "" /B "{self.py}" main.py\r\n'
        )
        with open(os.path.join(INSTALL_DIR, "start_voxly.bat"), "w") as fh:
            fh.write(_bat)
        self._log("  Embedded Python ready", "ok")

    def _download_with_progress(self, url, dest, label=""):
        downloaded = [0]
        total      = [1]

        def reporthook(block, bsize, tsize):
            if tsize > 0:
                total[0] = tsize
            downloaded[0] += bsize
            pct = min(1.0, downloaded[0] / total[0])
            mb  = downloaded[0] / 1_048_576
            self._log(f"  {label}  {mb:.1f} MB", "dim")

        urllib.request.urlretrieve(url, dest)

    def _step_packages(self):
        result = subprocess.run(
            [self.py, "-m", "pip", "install"] + PACKAGES + ["-q"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr[:500])
        self._log("  All packages installed.", "ok")

    def _step_icon(self):
        gen = os.path.join(INSTALL_DIR, "generate_icon.py")
        if os.path.exists(gen):
            subprocess.run([self.py, gen], cwd=INSTALL_DIR, capture_output=True)
            self._log("  Icon generated.", "ok")

    def _step_model(self):
        dlm = os.path.join(INSTALL_DIR, "download_model.py")
        if os.path.exists(dlm):
            self._log("  Downloading voice model (~150 MB, one-time only)...")
            r = subprocess.run([self.py, dlm], cwd=INSTALL_DIR,
                               capture_output=True, text=True)
            if r.returncode == 0:
                self._log("  Voice model ready.", "ok")
            else:
                self._log(f"  Model warning: {r.stderr[:100]}", "err")

    def _step_uninstaller(self):
        src = (
            'import os, winreg, subprocess\n'
            'APP_NAME    = "Voxly"\n'
            'INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))\n\n'
            'def _del_val(root, path, name):\n'
            '    try:\n'
            '        k = winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE)\n'
            '        winreg.DeleteValue(k, name); winreg.CloseKey(k)\n'
            '    except Exception: pass\n\n'
            'def _del_key(root, path):\n'
            '    try: winreg.DeleteKey(root, path)\n'
            '    except Exception: pass\n\n'
            'def main():\n'
            '    print("Uninstalling Voxly...")\n'
            '    _del_val(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", APP_NAME)\n'
            '    _del_key(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Voxly")\n'
            '    desktop = os.path.join(os.path.expanduser("~"), "Desktop")\n'
            '    lnk = os.path.join(desktop, f"{APP_NAME}.lnk")\n'
            '    if os.path.exists(lnk): os.remove(lnk)\n'
            '    bat = os.path.join(os.environ["TEMP"], "voxly_rm.bat")\n'
            '    with open(bat, "w") as f:\n'
            '        f.write(f"@echo off\\ntimeout /t 2 /nobreak > nul\\nrd /s /q \\"{INSTALL_DIR}\\"\\ndel \\"%~f0\\"\\n")\n'
            '    subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000)\n'
            '    print("Done. Voxly removed.")\n'
            '    input("Press Enter to close...")\n\n'
            'if __name__ == "__main__":\n'
            '    main()\n'
        )
        with open(UNINSTALLER, "w") as fh:
            fh.write(src)
        self._log("  Uninstaller written.", "ok")

    def _step_registry(self):
        # Apps & Features
        try:
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxly")
            winreg.SetValueEx(k, "DisplayName",     0, winreg.REG_SZ,    "Voxly - Voice Dictation")
            winreg.SetValueEx(k, "DisplayVersion",  0, winreg.REG_SZ,    APP_VERSION)
            winreg.SetValueEx(k, "Publisher",       0, winreg.REG_SZ,    PUBLISHER)
            winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ,    INSTALL_DIR)
            winreg.SetValueEx(k, "DisplayIcon",     0, winreg.REG_SZ,    ICON_ICO)
            winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ,    f'python "{UNINSTALLER}"')
            winreg.SetValueEx(k, "NoModify",        0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "NoRepair",        0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "EstimatedSize",   0, winreg.REG_DWORD, 400_000)
            winreg.CloseKey(k)
            self._log("  Apps & Features entry created.", "ok")
        except Exception as e:
            self._log(f"  Registry warning: {e}", "err")
        # Auto-startup
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Run",
                               0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ,
                              f'wscript.exe "{LAUNCHER}"')
            winreg.CloseKey(k)
            self._log("  Auto-startup configured.", "ok")
        except Exception as e:
            self._log(f"  Startup warning: {e}", "err")

    def _step_shortcuts(self):
        desktop  = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut = os.path.join(desktop, "Voxly.lnk")
        ps = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut}"); '
            f'$s.TargetPath = "wscript.exe"; '
            f'$s.Arguments = \'"{LAUNCHER}"\'; '
            f'$s.IconLocation = "{ICON_ICO}"; '
            f'$s.Description = "Voxly Voice Dictation"; '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-Command", ps], capture_output=True)
        self._log("  Desktop shortcut created.", "ok")

    # ── Done ──────────────────────────────────────────────────────────────────
    def _finish_success(self):
        self._log("\n  Voxly is ready! Enjoy.", "ok")
        self._status("Installation complete!")

        def _done_ui():
            self.install_btn.config(
                state="normal", bg=self.GREEN, fg=self.FG,
                text="  Launch Voxly  ",
                command=self._launch)
            self.close_btn.config(text=" Close ")
        self.root.after(0, _done_ui)

    def _launch(self):
        subprocess.Popen(["wscript.exe", LAUNCHER])
        self.root.destroy()


# ── Entry ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()
