import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, QStandardPaths, QDateTime, Qt

BOOKMARKS_FILE = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
    "TronBrowser",
    "bookmarks.json"
)

class BookmarkManager(QObject):
    bookmarks_changed = pyqtSignal()
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = BookmarkManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.bookmarks = []
        self.load_bookmarks()

    def load_bookmarks(self):
        try:
            os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
            if os.path.exists(BOOKMARKS_FILE):
                with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
                    self.bookmarks = json.load(f)
        except Exception as e:
            print(f"Error loading bookmarks: {e}")

    def save_bookmarks(self):
        try:
            os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
            with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.bookmarks, f, indent=4)
            self.bookmarks_changed.emit()
        except Exception as e:
            print(f"Error saving bookmarks: {e}")

    def is_bookmarked(self, url):
        if not url:
            return False
        clean = url.strip().lower().rstrip("/")
        for b in self.bookmarks:
            if b.get("url", "").strip().lower().rstrip("/") == clean:
                return True
        return False

    def toggle_bookmark(self, title, url):
        if self.is_bookmarked(url):
            self.remove_bookmark(url)
            return False
        else:
            self.add_bookmark(title, url)
            return True

    def add_bookmark(self, title, url):
        if not url or url.startswith("about:") or url.startswith("tron:"):
            return
        if self.is_bookmarked(url):
            return
            
        item = {
            "title": title or url,
            "url": url,
            "timestamp": QDateTime.currentDateTime().toString(Qt.DateFormat.ISODate)
        }
        self.bookmarks.insert(0, item)
        self.save_bookmarks()

    def remove_bookmark(self, url):
        clean = url.rstrip("/")
        self.bookmarks = [b for b in self.bookmarks if b["url"].rstrip("/") != clean]
        self.save_bookmarks()

    def clear_all(self):
        self.bookmarks = []
        self.save_bookmarks()
