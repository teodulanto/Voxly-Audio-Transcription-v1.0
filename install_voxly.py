"""
Voxly Installer
---------------
Run this once to set up Voxly on a new machine.
It will:
  1. Create a Python virtual environment
  2. Install all dependencies
  3. Download the Whisper model
  4. Set up Windows auto-startup via Registry
  5. Create a desktop shortcut
"""
import os
import sys
import subprocess
import winreg
import shutil

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
VENV_DIR   = os.path.join(BASE_DIR, "venv")
PYTHON_EXE = sys.executable
APP_NAME   = "Voxly"
LAUNCHER   = os.path.join(BASE_DIR, "Voxly.vbs")


def run(cmd, **kw):
    print(f"  > {' '.join(cmd)}")
    subprocess.check_call(cmd, **kw)


def step(n, msg):
    print(f"\n[{n}] {msg}")


def main():
    print("=" * 50)
    print(f"  {APP_NAME} - Voice Dictation Installer")
    print("=" * 50)

    # 1. Create venv if not present
    step(1, "Setting up Python environment...")
    if not os.path.isdir(VENV_DIR):
        run([PYTHON_EXE, "-m", "venv", VENV_DIR])
        print("  Virtual environment created.")
    else:
        print("  Virtual environment already exists, skipping.")

    pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")

    # 2. Install dependencies
    step(2, "Installing dependencies (this may take a few minutes)...")
    packages = [
        "faster-whisper",
        "sounddevice",
        "numpy",
        "keyboard",
        "pyautogui",
        "pystray",
        "Pillow",
    ]
    run([pip, "install", "--upgrade", "pip", "-q"])
    run([pip, "install"] + packages + ["-q"])
    print("  All packages installed.")

    # 3. Generate app icon
    step(3, "Generating app icon...")
    python_w = os.path.join(VENV_DIR, "Scripts", "python.exe")
    gen_icon = os.path.join(BASE_DIR, "generate_icon.py")
    if os.path.exists(gen_icon):
        run([python_w, gen_icon])
    else:
        print("  generate_icon.py not found, skipping.")

    # 4. Download Whisper model
    step(4, "Downloading Whisper voice model (~250MB, one-time setup)...")
    dl_model = os.path.join(BASE_DIR, "download_model.py")
    if os.path.exists(dl_model):
        run([python_w, dl_model])
    else:
        print("  download_model.py not found, skipping.")

    # 5. Write Voxly.vbs launcher
    step(5, "Creating Voxly launcher...")
    vbs_content = (
        f'Set objShell = CreateObject("WScript.Shell")\r\n'
        f'objShell.Run "{os.path.join(BASE_DIR, "start_voxly.bat")}", 0, False\r\n'
    )
    with open(LAUNCHER, "w") as f:
        f.write(vbs_content)

    bat_path = os.path.join(BASE_DIR, "start_voxly.bat")
    bat_content = f'@echo off\r\ncd /d "{BASE_DIR}"\r\n.\\venv\\Scripts\\pythonw.exe main.py\r\n'
    with open(bat_path, "w") as f:
        f.write(bat_content)
    print("  Voxly.vbs and start_voxly.bat created.")

    # 6. Windows Registry auto-startup
    step(6, "Configuring auto-startup with Windows...")
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{LAUNCHER}"')
        winreg.CloseKey(key)
        print("  Auto-startup configured in Windows Registry.")
    except Exception as e:
        print(f"  Warning: Could not set Registry key: {e}")

    # 7. Desktop shortcut
    step(7, "Creating desktop shortcut...")
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut = os.path.join(desktop, f"{APP_NAME}.lnk")
        ps_script = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut}"); '
            f'$s.TargetPath = "{LAUNCHER}"; '
            f'$s.Description = "Voxly Voice Dictation"; '
            f'$s.Save()'
        )
        subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, check=True
        )
        print(f"  Desktop shortcut created: {shortcut}")
    except Exception as e:
        print(f"  Warning: Could not create shortcut: {e}")

    print("\n" + "=" * 50)
    print(f"  {APP_NAME} installed successfully!")
    print(f"  Launch it now by double-clicking 'Voxly.vbs'")
    print(f"  or the Desktop shortcut.")
    print(f"  Voxly will auto-start on every Windows boot.")
    print("=" * 50)
    input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
