"""
Voxly Installer — install_voxly.py
====================================
Run this ONCE.  It will:
  1. Copy Voxly to %LOCALAPPDATA%\Voxly  (permanent install folder)
  2. Create a Python virtual-environment inside that folder
  3. Install all dependencies  
  4. Download the Whisper AI model
  5. Register Voxly in Windows "Apps & Features" (Add/Remove Programs)
  6. Set up Windows auto-startup (Registry)
  7. Create a Desktop shortcut
  8. Drop an uninstaller so the user can remove Voxly cleanly

Usage:  python install_voxly.py
"""
import os
import sys
import subprocess
import shutil
import winreg

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME      = "Voxly"
APP_VERSION   = "1.0.0"
PUBLISHER     = "Antigravity"
# Source folder (where THIS script lives right now)
SRC_DIR       = os.path.dirname(os.path.abspath(__file__))
# Permanent install destination
INSTALL_DIR   = os.path.join(os.environ["LOCALAPPDATA"], APP_NAME)
VENV_DIR      = os.path.join(INSTALL_DIR, "venv")
PYTHON_EXE    = sys.executable
PYTHONW_EXE   = os.path.join(VENV_DIR, "Scripts", "pythonw.exe")
PIP_EXE       = os.path.join(VENV_DIR, "Scripts", "pip.exe")
LAUNCHER_VBS  = os.path.join(INSTALL_DIR, "Voxly.vbs")
UNINSTALLER   = os.path.join(INSTALL_DIR, "uninstall_voxly.py")
ICON_PATH     = os.path.join(INSTALL_DIR, "app_icon.ico")

# Files to copy from the source directory to the install location
APP_FILES = [
    "main.py",
    "hud_window.py",
    "audio_recorder.py",
    "transcriber.py",
    "hotkey_manager.py",
    "input_simulator.py",
    "settings_manager.py",
    "generate_icon.py",
    "download_model.py",
    "app_icon.png",
    "app_icon.ico",
    "Voxly.vbs",
    "start_voxly.bat",
]

PACKAGES = [
    "faster-whisper",
    "sounddevice",
    "numpy",
    "keyboard",
    "pyautogui",
    "pystray",
    "Pillow",
    "pyperclip",
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd):
    print(f"   > {' '.join(cmd)}")
    subprocess.check_call(cmd)


def step(n, msg):
    print(f"\n[{n}] {msg}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print(f"  {APP_NAME} {APP_VERSION}  —  Installation")
    print("=" * 55)

    # 1. Copy app files -----------------------------------------------------------
    step(1, f"Copying Voxly to {INSTALL_DIR} ...")
    os.makedirs(INSTALL_DIR, exist_ok=True)
    missing = []
    for f in APP_FILES:
        src = os.path.join(SRC_DIR, f)
        dst = os.path.join(INSTALL_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            missing.append(f)
    if missing:
        print(f"  Warning: could not find {missing} in source folder.")

    # Write the VBS launcher pointing to INSTALL_DIR
    vbs = (
        'Dim sDir, objShell\r\n'
        f'sDir = "{INSTALL_DIR}"\r\n'
        'Set objShell = CreateObject("WScript.Shell")\r\n'
        'objShell.Run "cmd /c cd /d """ & sDir & """ && start_voxly.bat", 0, False\r\n'
    )
    with open(LAUNCHER_VBS, "w") as fh:
        fh.write(vbs)

    # Write start_voxly.bat that uses the INSTALLED venv
    bat = f'@echo off\r\ncd /d "{INSTALL_DIR}"\r\n.\\venv\\Scripts\\pythonw.exe main.py\r\n'
    with open(os.path.join(INSTALL_DIR, "start_voxly.bat"), "w") as fh:
        fh.write(bat)
    print("  Files copied successfully.")

    # 2. Virtual environment ------------------------------------------------------
    step(2, "Creating Python virtual environment ...")
    if not os.path.isdir(VENV_DIR):
        run([PYTHON_EXE, "-m", "venv", VENV_DIR])
    else:
        print("  Existing venv found, reusing.")

    # 3. Install dependencies -----------------------------------------------------
    step(3, "Installing dependencies (this may take a few minutes) ...")
    venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
    # Use python -m pip to avoid issues with pip.exe on Python 3.13+
    try:
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip", "-q"],
                       check=True)
    except Exception:
        pass  # Non-fatal: continue even if pip self-upgrade fails
    run([venv_python, "-m", "pip", "install"] + PACKAGES + ["-q"])
    print("  All packages installed.")

    # 4. Generate icon ------------------------------------------------------------
    step(4, "Generating app icon ...")
    venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
    gen = os.path.join(INSTALL_DIR, "generate_icon.py")
    if os.path.exists(gen):
        subprocess.run([venv_python, gen], cwd=INSTALL_DIR)

    # 5. Download Whisper model ---------------------------------------------------
    step(5, "Downloading Whisper voice model (~250 MB, one-time only) ...")
    dlm = os.path.join(INSTALL_DIR, "download_model.py")
    if os.path.exists(dlm):
        run([venv_python, dlm])

    # 6. Write uninstaller --------------------------------------------------------
    step(6, "Writing uninstaller ...")
    _write_uninstaller()
    print(f"  Uninstaller saved to: {UNINSTALLER}")

    # 7. Register in Apps & Features ----------------------------------------------
    step(7, 'Registering in Windows "Apps & Features" ...')
    _register_app()
    print('  Voxly now appears in Windows Settings -> Apps & Features.')

    # 8. Auto-startup (Registry) --------------------------------------------------
    step(8, "Configuring Windows auto-startup ...")
    _set_startup()
    print("  Voxly will start automatically with Windows.")

    # 9. Desktop shortcut ---------------------------------------------------------
    step(9, "Creating Desktop shortcut ...")
    _create_shortcut()

    # Done -------------------------------------------------------------------------
    print("\n" + "=" * 55)
    print(f"  {APP_NAME} installed successfully!")
    print(f"  Location: {INSTALL_DIR}")
    print(f'  Launch:   double-click the "{APP_NAME}" shortcut on your Desktop')
    print(f"  Uninstall: Apps & Features → Voxly → Uninstall")
    print("=" * 55)
    input("\nPress Enter to finish ...")


# ── Registry helpers ──────────────────────────────────────────────────────────
def _register_app():
    """Create the Uninstall registry entry so Voxly shows in Apps & Features."""
    key_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, "DisplayName",     0, winreg.REG_SZ,   f"{APP_NAME} — Voice Dictation")
        winreg.SetValueEx(key, "DisplayVersion",  0, winreg.REG_SZ,   APP_VERSION)
        winreg.SetValueEx(key, "Publisher",       0, winreg.REG_SZ,   PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ,   INSTALL_DIR)
        winreg.SetValueEx(key, "DisplayIcon",     0, winreg.REG_SZ,   ICON_PATH)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                          f'python "{UNINSTALLER}"')
        winreg.SetValueEx(key, "NoModify",  0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair",  0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, 350_000)  # ~350 MB in KB
        winreg.CloseKey(key)
    except Exception as e:
        print(f"  Warning: could not write Uninstall key: {e}")


def _set_startup():
    run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'wscript.exe "{LAUNCHER_VBS}"')
        winreg.CloseKey(key)
    except Exception as e:
        print(f"  Warning: could not write startup key: {e}")


def _create_shortcut():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut = os.path.join(desktop, f"{APP_NAME}.lnk")
    ps = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{shortcut}"); '
        f'$s.TargetPath = "wscript.exe"; '
        f'$s.Arguments = \'"{LAUNCHER_VBS}"\'; '
        f'$s.IconLocation = "{ICON_PATH}"; '
        f'$s.Description = "Voxly Voice Dictation"; '
        f'$s.Save()'
    )
    try:
        subprocess.run(["powershell", "-Command", ps], capture_output=True, check=True)
        print(f"  Desktop shortcut created.")
    except Exception as e:
        print(f"  Warning: could not create shortcut: {e}")


# ── Uninstaller source (written into the install folder) ─────────────────────
def _write_uninstaller():
    src = r'''"""
Voxly Uninstaller — uninstall_voxly.py
Run: python uninstall_voxly.py  (or use Apps & Features)
"""
import os, sys, shutil, winreg, subprocess, time

APP_NAME    = "Voxly"
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))

def remove_value(root, path, name):
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
    except Exception:
        pass

def delete_subkey(root, path):
    try:
        winreg.DeleteKey(root, path)
    except Exception:
        pass

def main():
    print("Uninstalling Voxly ...")

    remove_value(winreg.HKEY_CURRENT_USER,
                 r"Software\Microsoft\Windows\CurrentVersion\Run", APP_NAME)
    print("  Startup entry removed.")

    delete_subkey(winreg.HKEY_CURRENT_USER,
                  r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxly")
    print("  Apps & Features entry removed.")

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    lnk = os.path.join(desktop, f"{APP_NAME}.lnk")
    if os.path.exists(lnk):
        os.remove(lnk)
        print("  Desktop shortcut removed.")

    print(f"  Scheduling removal of: {INSTALL_DIR}")
    bat = os.path.join(os.environ["TEMP"], "voxly_cleanup.bat")
    with open(bat, "w") as f:
        f.write(f"@echo off\ntimeout /t 2 /nobreak > nul\nrd /s /q \"{INSTALL_DIR}\"\ndel \"%~f0\"\n")
    subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000)

    print("\nVoxly has been uninstalled. Goodbye!")
    input("Press Enter to close ...")

if __name__ == "__main__":
    main()
'''
    with open(UNINSTALLER, "w") as fh:
        fh.write(src)


if __name__ == "__main__":
    main()
