import json
import os


class SettingsManager:
    def __init__(self, settings_file="settings.json"):
        self.settings_file = settings_file
        self.default_settings = {
            "hotkey": "ctrl+alt+v",
            "model_size": "base",
            "language": None,      # None = auto-detect
            "compute_type": "int8",
        }
        self.settings = self._load()

    def _load(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    return {**self.default_settings, **json.load(f)}
            except Exception:
                pass
        return self.default_settings.copy()

    def save(self, new_settings):
        self.settings.update(new_settings)
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key):
        return self.settings.get(key, self.default_settings.get(key))
