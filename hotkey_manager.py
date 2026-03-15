import keyboard


class HotkeyManager:
    def __init__(self, hotkey="ctrl+alt+v", callback=None):
        self.hotkey = hotkey
        self.callback = callback
        self.is_listening = False

    def start(self):
        if not self.is_listening:
            keyboard.add_hotkey(self.hotkey, self._handle)
            self.is_listening = True

    def stop(self):
        if self.is_listening:
            try:
                keyboard.remove_hotkey(self._handle)
            except Exception:
                pass
            self.is_listening = False

    def _handle(self):
        if self.callback:
            self.callback()

    def update_hotkey(self, new_hotkey):
        self.stop()
        self.hotkey = new_hotkey
        self.start()
