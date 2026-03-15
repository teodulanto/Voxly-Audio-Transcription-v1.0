import keyboard
import time
import threading


# Minimum seconds between two successful triggers
_DEBOUNCE_SECONDS = 0.5


class HotkeyManager:
    def __init__(self, hotkey="ctrl+alt+v", callback=None):
        self.hotkey = hotkey
        self.callback = callback
        self.is_listening = False
        self._last_trigger = 0.0
        self._lock = threading.Lock()

    def start(self):
        if not self.is_listening:
            # trigger_on_release=True avoids double-fire on key-hold / repeat
            keyboard.add_hotkey(
                self.hotkey,
                self._handle,
                trigger_on_release=False,
                suppress=False,
            )
            self.is_listening = True

    def stop(self):
        if self.is_listening:
            try:
                keyboard.remove_all_hotkeys()
            except Exception:
                pass
            self.is_listening = False

    def _handle(self):
        """Debounced handler — ignores repeat events within the debounce window."""
        now = time.monotonic()
        with self._lock:
            if now - self._last_trigger < _DEBOUNCE_SECONDS:
                return                      # Drop duplicate / phantom trigger
            self._last_trigger = now

        if self.callback:
            # Run in a thread so we don't block the keyboard hook
            threading.Thread(target=self.callback, daemon=True).start()

    def update_hotkey(self, new_hotkey):
        self.stop()
        self.hotkey = new_hotkey
        self.start()
