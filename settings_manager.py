import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, QStandardPaths

SETTINGS_FILE = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
    "TronBrowser",
    "settings.json"
)

DEFAULT_SETTINGS = {
    "theme": "light",
    "accent_color": "Tron Blue (Default)",
    "search_engine": "Google",
    "custom_search_url": "https://www.google.com/search?q=",
    "show_bookmark_btn": True,
    "show_home_btn": True,
    "show_history_btn": True,
    "show_download_btn": True,
    "show_star_btn": True,
    "startup_behavior": "home", # 'new_tab', 'blank', 'custom'
    "custom_startup_url": "https://tronexplorer.netlify.app/",
    "autocomplete_enabled": True,
    "adblock_enabled": True,
    "force_https": True,
    "dnt_header": True,
    "hardware_accel": True,
    "download_dir": QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation),
    "ask_download_dir": False,
    "tab_suspension": True,
    "tab_sleep_timeout_minutes": 15,
}

class SettingsManager(QObject):
    settings_changed = pyqtSignal(dict)
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = SettingsManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._data = dict(DEFAULT_SETTINGS)
        self.load_settings()

    def load_settings(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._data.update(saved)
            if self._data.get("custom_startup_url") in ["https://novaaisearch.netlify.app", "https://novaaisearch.netlify.app/"]:
                self._data["custom_startup_url"] = "https://tronexplorer.netlify.app/"
                self.save_settings()
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
            self.settings_changed.emit(self._data)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self._data.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        if self._data.get(key) != value:
            self._data[key] = value
            self.save_settings()

    def update_dict(self, d):
        self._data.update(d)
        self.save_settings()

    def get_search_url(self, query):
        engine = self.get("search_engine", "Google")
        encoded = query.replace(" ", "+")
        if engine == "DuckDuckGo":
            return f"https://duckduckgo.com/?q={encoded}"
        elif engine == "Bing":
            return f"https://www.bing.com/search?q={encoded}"
        elif engine == "Ecosia":
            return f"https://www.ecosia.org/search?q={encoded}"
        elif engine == "Custom":
            custom_url = self.get("custom_search_url", "https://www.google.com/search?q=")
            return f"{custom_url}{encoded}"
        else:
            return f"https://www.google.com/search?q={encoded}"
