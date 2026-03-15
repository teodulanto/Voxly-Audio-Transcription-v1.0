"""
VoxlyInstaller.exe — Installer GUI
Bundled with PyInstaller. Requires Python to be on PATH on the target machine.
"""
import sys
import os
import subprocess
import threading
import shutil
import winreg
import tkinter as tk
from tkinter import font as tkfont

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME    = "Voxly"
APP_VERSION = "1.0.0"
PUBLISHER   = "Antigravity"

# Installation destination
INSTALL_DIR = os.path.join(os.environ["LOCALAPPDATA"], APP_NAME)
VENV_DIR    = os.path.join(INSTALL_DIR, "venv")
LAUNCHER    = os.path.join(INSTALL_DIR, "Voxly.vbs")
UNINSTALLER = os.path.join(INSTALL_DIR, "uninstall_voxly.py")
ICON_ICO    = os.path.join(INSTALL_DIR, "app_icon.ico")

PACKAGES = [
    "faster-whisper", "sounddevice", "numpy",
    "keyboard", "pyautogui", "pystray", "Pillow", "pyperclip",
]

# Source dir = folder next to this exe (or script)
if getattr(sys, "frozen", False):
    SRC_DIR = sys._MEIPASS          # PyInstaller bundle
else:
    SRC_DIR = os.path.dirname(os.path.abspath(__file__))

APP_FILES = [
    "main.py", "hud_window.py", "audio_recorder.py", "transcriber.py",
    "hotkey_manager.py", "input_simulator.py", "settings_manager.py",
    "generate_icon.py", "download_model.py",
    "app_icon.png", "app_icon.ico",
    "start_voxly.bat",
]

# ── GUI ───────────────────────────────────────────────────────────────────────
class InstallerApp:
    BG    = "#0f0f0f"
    CARD  = "#1a1a1a"
    ACCT  = "#3b82f6"
    GREEN = "#22c55e"
    RED   = "#ef4444"
    FG    = "#ffffff"
    GRAY  = "#9ca3af"

    def __init__(self, root):
        self.root = root
        self.root.title(f"Voxly {APP_VERSION} — Setup")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        # Center window
        W, H = 520, 400
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        try:
            ico = os.path.join(SRC_DIR, "app_icon.ico")
            if os.path.exists(ico):
                root.iconbitmap(ico)
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        f_title = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        f_body  = tkfont.Font(family="Segoe UI", size=10)
        f_small = tkfont.Font(family="Segoe UI", size=9)
        f_log   = tkfont.Font(family="Consolas", size=9)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=self.BG, pady=30)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎙  Voxly", font=f_title,
                 fg=self.FG, bg=self.BG).pack()
        tk.Label(hdr, text="AI Voice Dictation for Windows",
                 font=f_body, fg=self.GRAY, bg=self.BG).pack(pady=(4, 0))

        # ── Install Path ─────────────────────────────────────────────────────
        path_frm = tk.Frame(self.root, bg=self.CARD, padx=20, pady=12)
        path_frm.pack(fill="x", padx=24)
        tk.Label(path_frm, text="Install location:", font=f_small,
                 fg=self.GRAY, bg=self.CARD).pack(anchor="w")
        tk.Label(path_frm, text=INSTALL_DIR, font=f_small,
                 fg=self.FG, bg=self.CARD).pack(anchor="w")

        # ── Log box ──────────────────────────────────────────────────────────
        log_frm = tk.Frame(self.root, bg=self.CARD, padx=12, pady=10)
        log_frm.pack(fill="both", expand=True, padx=24, pady=(10, 0))
        self.log_text = tk.Text(log_frm, wrap="word", font=f_log,
                                bg="#0a0a0a", fg=self.GRAY,
                                relief="flat", bd=0, state="disabled",
                                height=8)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("ok",  foreground=self.GREEN)
        self.log_text.tag_config("err", foreground=self.RED)
        self.log_text.tag_config("hd",  foreground=self.ACCT)

        # ── Progress bar (canvas hack) ────────────────────────────────────────
        pb_frm = tk.Frame(self.root, bg=self.BG, pady=10)
        pb_frm.pack(fill="x", padx=24)
        self.pb_track = tk.Canvas(pb_frm, height=6, bg="#2d2d2d",
                                  highlightthickness=0)
        self.pb_track.pack(fill="x")
        self.pb_fill  = None
        self._progress = 0.0

        # ── Bottom buttons ────────────────────────────────────────────────────
        btn_frm = tk.Frame(self.root, bg=self.BG, padx=24, pady=14)
        btn_frm.pack(fill="x")
        self.status_lbl = tk.Label(btn_frm, text="Ready to install",
                                   font=f_small, fg=self.GRAY, bg=self.BG)
        self.status_lbl.pack(side="left")
        self.cancel_btn = tk.Button(btn_frm, text=" Cancel ",
                                    font=f_body, bg="#2d2d2d", fg=self.FG,
                                    relief="flat", padx=10, cursor="hand2",
                                    command=self.root.destroy)
        self.cancel_btn.pack(side="right", padx=(8, 0))
        self.install_btn = tk.Button(btn_frm, text="  Install  ",
                                     font=f_body, bg=self.ACCT, fg=self.FG,
                                     relief="flat", padx=14, cursor="hand2",
                                     command=self._start_install)
        self.install_btn.pack(side="right")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _log(self, msg, tag=""):
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n", tag)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _do)

    def _set_status(self, msg):
        self.root.after(0, lambda: self.status_lbl.config(text=msg))

    def _set_progress(self, pct):
        """pct = 0.0 – 1.0"""
        def _do():
            w = self.pb_track.winfo_width()
            if self.pb_fill:
                self.pb_track.delete(self.pb_fill)
            self.pb_fill = self.pb_track.create_rectangle(
                0, 0, int(w * pct), 6, fill=self.ACCT, outline="")
        self.root.after(0, _do)

    # ── Installation thread ───────────────────────────────────────────────────
    def _start_install(self):
        self.install_btn.config(state="disabled", text="Installing...")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        try:
            self._run_steps()
            self._finish_ok()
        except Exception as e:
            self._log(f"\nERROR: {e}", "err")
            self._set_status("Installation failed.")
            self.root.after(0, lambda: self.install_btn.config(
                state="normal", text="Retry"))

    def _run_steps(self):
        steps = [
            (0.08, "Copying files...",                self._step_copy),
            (0.20, "Creating Python environment...",  self._step_venv),
            (0.45, "Installing AI packages...",       self._step_packages),
            (0.65, "Generating icon...",              self._step_icon),
            (0.80, "Downloading voice model...",      self._step_model),
            (0.88, "Writing uninstaller...",          self._step_uninstaller),
            (0.93, "Registering application...",      self._step_registry),
            (0.97, "Creating shortcuts...",           self._step_shortcuts),
            (1.00, "Done",                            lambda: None),
        ]
        for pct, status, fn in steps:
            self._set_status(status)
            self._log(f"\n>> {status}", "hd")
            fn()
            self._set_progress(pct)

    # ── Steps ─────────────────────────────────────────────────────────────────
    def _step_copy(self):
        os.makedirs(INSTALL_DIR, exist_ok=True)
        for f in APP_FILES:
            src = os.path.join(SRC_DIR, f)
            dst = os.path.join(INSTALL_DIR, f)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                self._log(f"  copied {f}", "ok")
            else:
                self._log(f"  (skipped {f} - not found)")
        # Write custom VBS pointing to INSTALL_DIR
        vbs = (
            'Dim sDir, objShell\r\n'
            f'sDir = "{INSTALL_DIR}"\r\n'
            'Set objShell = CreateObject("WScript.Shell")\r\n'
            'objShell.Run "cmd /c cd /d """ & sDir & """ && start_voxly.bat", 0, False\r\n'
        )
        with open(LAUNCHER, "w") as fh:
            fh.write(vbs)
        bat = f'@echo off\r\ncd /d "{INSTALL_DIR}"\r\n.\\venv\\Scripts\\pythonw.exe main.py\r\n'
        with open(os.path.join(INSTALL_DIR, "start_voxly.bat"), "w") as fh:
            fh.write(bat)
        self._log("  launcher scripts written", "ok")

    def _step_venv(self):
        if os.path.isdir(VENV_DIR):
            self._log("  existing venv reused", "ok")
            return
        python = sys.executable
        result = subprocess.run([python, "-m", "venv", VENV_DIR],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        self._log("  virtual environment created", "ok")

    def _step_packages(self):
        venv_py = os.path.join(VENV_DIR, "Scripts", "python.exe")
        # pip upgrade (non-fatal)
        subprocess.run([venv_py, "-m", "pip", "install", "--upgrade", "pip", "-q"],
                       capture_output=True)
        result = subprocess.run(
            [venv_py, "-m", "pip", "install"] + PACKAGES + ["-q"],
            capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[:500])
        self._log("  all packages installed", "ok")

    def _step_icon(self):
        venv_py = os.path.join(VENV_DIR, "Scripts", "python.exe")
        gen = os.path.join(INSTALL_DIR, "generate_icon.py")
        if os.path.exists(gen):
            subprocess.run([venv_py, gen], cwd=INSTALL_DIR, capture_output=True)
            self._log("  icon generated", "ok")

    def _step_model(self):
        venv_py = os.path.join(VENV_DIR, "Scripts", "python.exe")
        dlm = os.path.join(INSTALL_DIR, "download_model.py")
        if os.path.exists(dlm):
            self._log("  downloading model (this can take 2-5 min)...")
            result = subprocess.run([venv_py, dlm], cwd=INSTALL_DIR,
                                    capture_output=True, text=True)
            if result.returncode == 0:
                self._log("  model ready", "ok")
            else:
                self._log(f"  model download failed: {result.stderr[:200]}", "err")

    def _step_uninstaller(self):
        uninstaller_src = r'''"""Voxly Uninstaller"""
import os, winreg, subprocess

APP_NAME    = "Voxly"
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))

def remove_value(root, path, name):
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
    except Exception: pass

def delete_subkey(root, path):
    try: winreg.DeleteKey(root, path)
    except Exception: pass

def main():
    print("Uninstalling Voxly ...")
    remove_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", APP_NAME)
    delete_subkey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxly")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    lnk = os.path.join(desktop, f"{APP_NAME}.lnk")
    if os.path.exists(lnk): os.remove(lnk)
    bat = os.path.join(os.environ["TEMP"], "voxly_cleanup.bat")
    with open(bat, "w") as f:
        f.write(f"@echo off\ntimeout /t 2 /nobreak > nul\nrd /s /q \"{INSTALL_DIR}\"\ndel \"%~f0\"\n")
    subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000)
    print("Voxly uninstalled.")
    input("Press Enter to close ...")

if __name__ == "__main__":
    main()
'''
        with open(UNINSTALLER, "w") as fh:
            fh.write(uninstaller_src)
        self._log("  uninstaller written", "ok")

    def _step_registry(self):
        # Apps & Features
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxly"
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "DisplayName",     0, winreg.REG_SZ,    "Voxly - Voice Dictation")
            winreg.SetValueEx(key, "DisplayVersion",  0, winreg.REG_SZ,    APP_VERSION)
            winreg.SetValueEx(key, "Publisher",       0, winreg.REG_SZ,    PUBLISHER)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ,    INSTALL_DIR)
            winreg.SetValueEx(key, "DisplayIcon",     0, winreg.REG_SZ,    ICON_ICO)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,    f'python "{UNINSTALLER}"')
            winreg.SetValueEx(key, "NoModify",        0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair",        0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "EstimatedSize",   0, winreg.REG_DWORD, 350_000)
            winreg.CloseKey(key)
            self._log("  Apps & Features entry created", "ok")
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
            self._log("  auto-startup configured", "ok")
        except Exception as e:
            self._log(f"  Startup warning: {e}", "err")

    def _step_shortcuts(self):
        desktop  = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut = os.path.join(desktop, "Voxly.lnk")
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut}"); '
            f'$s.TargetPath = "wscript.exe"; '
            f'$s.Arguments = \'"{LAUNCHER}"\'; '
            f'$s.IconLocation = "{ICON_ICO}"; '
            f'$s.Description = "Voxly Voice Dictation"; '
            f'$s.Save()'
        )
        result = subprocess.run(["powershell", "-Command", ps_cmd],
                                capture_output=True)
        if result.returncode == 0:
            self._log("  desktop shortcut created", "ok")

    # ── Finish ────────────────────────────────────────────────────────────────
    def _finish_ok(self):
        self._log("\n  Voxly installed successfully!", "ok")
        self._set_status("Installation complete!")

        def _show_done():
            self.install_btn.config(
                state="normal", bg="#22c55e",
                text="  Launch Voxly  ",
                command=self._launch)
            self.cancel_btn.config(text=" Close ")
        self.root.after(0, _show_done)

    def _launch(self):
        import subprocess
        subprocess.Popen(["wscript.exe", LAUNCHER])
        self.root.destroy()


# ── Entry ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = InstallerApp(root)
    root.mainloop()
