import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, QStandardPaths, QDateTime, Qt

HISTORY_FILE = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
    "TronBrowser",
    "history.json"
)

class HistoryManager(QObject):
    history_changed = pyqtSignal()
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = HistoryManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.history = []
        self.load_history()

    def load_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")

    def save_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history[:500], f, indent=4)
            self.history_changed.emit()
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_history(self, title, url):
        if not url or url.startswith("about:") or url.startswith("tron:"):
            return
            
        now = QDateTime.currentDateTime()
        item = {
            "title": title or url,
            "url": url,
            "timestamp": now.toString(Qt.DateFormat.ISODate),
            "date": now.toString("yyyy-MM-dd"),
            "time": now.toString("hh:mm A")
        }
        
        # Deduplicate recent consecutive entry for same URL
        if self.history and self.history[0]["url"] == url:
            self.history[0] = item
        else:
            self.history.insert(0, item)
            
        self.save_history()

    def remove_item(self, url):
        self.history = [h for h in self.history if h["url"] != url]
        self.save_history()

    def clear_history(self):
        self.history = []
        self.save_history()
