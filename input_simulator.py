import pyperclip
import pyautogui
import time


class InputSimulator:
    def __init__(self):
        pyautogui.FAILSAFE = True

    def simulate_pasting(self, text):
        if not text:
            return
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
