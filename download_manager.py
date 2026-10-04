import os
import json
import time
import shutil
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QUrl, QFileInfo, QDateTime, QStandardPaths, QSize, QPoint, QPropertyAnimation, QEasingCurve, QMimeData
from PyQt6.QtGui import QIcon, QColor, QDesktopServices, QPainter, QPen, QDrag
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QScrollArea, QLineEdit, QFileDialog, QFrame, QFileIconProvider, QSizePolicy,
    QGraphicsDropShadowEffect, QApplication
)
from theme_manager import ThemeManager, parse_color, get_tinted_icon

# File to persist download history
HISTORY_FILE = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
    "TronBrowser",
    "downloads_history.json"
)

CATEGORIES = {
    "All": [],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".rtf", ".pdf"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".wmv", ".3gp"],
    "Images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
    "Other": []
}

class DownloadTracker(QObject):
    download_started = pyqtSignal(str)
    download_completed = pyqtSignal(str)
    download_failed = pyqtSignal(str)
    downloads_updated = pyqtSignal()
    
    _instance = None
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = DownloadTracker()
        return cls._instance

    def __init__(self):
        if DownloadTracker._instance is not None:
            raise Exception("This class is a singleton!")
        super().__init__()
        self.downloads = []
        self.load_history()
        
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start()

    def load_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    for item in history:
                        item['request'] = None
                        item['speed'] = 0
                        item['eta'] = 0
                        self.downloads.append(item)
        except Exception as e:
            print(f"Error loading download history: {e}")

    def save_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            serializable = []
            for item in self.downloads:
                serializable.append({
                    "id": item["id"],
                    "filename": item["filename"],
                    "directory": item["directory"],
                    "full_path": item["full_path"],
                    "url": item["url"],
                    "total_bytes": item["total_bytes"],
                    "received_bytes": item["received_bytes"],
                    "state": item["state"],
                    "timestamp": item["timestamp"]
                })
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(serializable[:100], f, indent=4)
        except Exception as e:
            print(f"Error saving download history: {e}")

    def add_download(self, request):
        item_id = int(time.time() * 1000)
        full_path = os.path.join(request.downloadDirectory(), request.downloadFileName())
        
        item = {
            "id": item_id,
            "filename": request.downloadFileName(),
            "directory": request.downloadDirectory(),
            "full_path": full_path,
            "url": request.url().toString(),
            "total_bytes": request.totalBytes(),
            "received_bytes": request.receivedBytes(),
            "state": int(request.state().value),
            "timestamp": QDateTime.currentDateTime().toString(Qt.DateFormat.ISODate),
            "request": request,
            "speed": 0,
            "eta": 0,
            "last_bytes": 0,
            "last_time": time.time()
        }
        
        self.downloads.insert(0, item)
        
        request.receivedBytesChanged.connect(lambda: self.on_bytes_changed(item_id))
        request.stateChanged.connect(lambda state: self.on_state_changed(item_id, state))
        request.isPausedChanged.connect(self.downloads_updated.emit)
        
        self.download_started.emit(item["filename"])
        self.downloads_updated.emit()
        self.save_history()

    def on_bytes_changed(self, item_id):
        try:
            item = self.find_item(item_id)
            if item and item.get("request"):
                req = item["request"]
                item["received_bytes"] = req.receivedBytes()
                item["total_bytes"] = req.totalBytes()
                self.downloads_updated.emit()
        except (RuntimeError, KeyError, AttributeError):
            pass

    def on_state_changed(self, item_id, state):
        try:
            item = self.find_item(item_id)
            if item:
                item["state"] = int(state.value)
                from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
                
                if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                    self.download_completed.emit(item["filename"])
                    item["request"] = None
                    self.save_history()
                elif state in [QWebEngineDownloadRequest.DownloadState.DownloadCancelled, QWebEngineDownloadRequest.DownloadState.DownloadInterrupted]:
                    self.download_failed.emit(item["filename"])
                    item["request"] = None
                    self.save_history()
                    
                self.downloads_updated.emit()
        except (RuntimeError, KeyError, AttributeError):
            pass

    def find_item(self, item_id):
        for item in self.downloads:
            if item["id"] == item_id:
                return item
        return None

    def update_progress(self):
        try:
            active_any = False
            current_time = time.time()
            
            for item in self.downloads:
                if item.get("request"):
                    active_any = True
                    req = item["request"]
                    
                    elapsed = current_time - item["last_time"]
                    if elapsed >= 0.8:
                        received = req.receivedBytes()
                        diff = received - item["last_bytes"]
                        item["speed"] = max(0, int(diff / elapsed))
                        item["last_bytes"] = received
                        item["last_time"] = current_time
                        
                        total = req.totalBytes()
                        if total > 0 and item["speed"] > 0:
                            item["eta"] = int((total - received) / item["speed"])
                        else:
                            item["eta"] = 0
                            
            if active_any:
                self.downloads_updated.emit()
        except (RuntimeError, KeyError, AttributeError):
            pass

    def clear_all(self):
        self.downloads = [item for item in self.downloads if item["request"] is not None]
        self.save_history()
        self.downloads_updated.emit()

    def remove_download(self, item_id):
        item = self.find_item(item_id)
        if item:
            if item["request"]:
                item["request"].cancel()
            self.downloads.remove(item)
            self.save_history()
            self.downloads_updated.emit()

    def is_any_downloading(self):
        for item in self.downloads:
            if item["request"] is not None:
                return True
        return False

    def get_overall_progress(self):
        active = [item for item in self.downloads if item["request"] is not None]
        if not active:
            return 0
        total = sum(item["total_bytes"] for item in active if item["total_bytes"] > 0)
        received = sum(item["received_bytes"] for item in active)
        if total > 0:
            return int((received / total) * 100)
        return 0


class SparklineWidget(QWidget):
    """Draws a smooth graph of active download speeds."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.setFixedHeight(20)
        self.setFixedWidth(70)

    def set_history(self, history):
        self.history = history
        self.update()

    def paintEvent(self, event):
        if not self.history or len(self.history) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = ThemeManager.instance().colors()
        
        p.setPen(QPen(parse_color(c["accent_blue"]), 1.5))
        
        max_val = max(self.history) if max(self.history) > 0 else 1
        w = self.width()
        h = self.height()
        points = []
        dx = w / (len(self.history) - 1)
        for i, val in enumerate(self.history):
            x = i * dx
            y = h - (val / max_val) * (h - 4) - 2
            points.append(QPoint(int(x), int(y)))
            
        for i in range(len(points) - 1):
            p.drawLine(points[i], points[i+1])
        p.end()


class DownloadItemWidget(QFrame):
    def __init__(self, item, query="", parent=None):
        super().__init__(parent)
        self.item = item
        self.query = query
        self.setObjectName("downloadCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.speed_history = [0] * 10
        self.drag_start_position = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # 1. System File Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(36, 36)
        provider = QFileIconProvider()
        info = QFileInfo(item["full_path"])
        icon = provider.icon(info)
        if icon.isNull():
            icon = provider.icon(QFileIconProvider.IconType.File)
        self.icon_label.setPixmap(icon.pixmap(QSize(32, 32)))
        layout.addWidget(self.icon_label)

        # 2. Progress & Info Section
        self.info_layout = QVBoxLayout()
        self.info_layout.setSpacing(4)
        
        filename = item["filename"]
        if query:
            import re
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            filename = pattern.sub(lambda m: f"<span style='background-color: #ffeb3b; color: #202124;'>{m.group(0)}</span>", filename)
            
        self.name_lbl = QLabel()
        self.name_lbl.setText(filename)
        self.name_lbl.setObjectName("filenameLabel")
        self.info_layout.addWidget(self.name_lbl)
        
        display_url = item["url"]
        if len(display_url) > 100:
            display_url = display_url[:97] + "..."
        self.url_lbl = QLabel(display_url)
        self.url_lbl.setObjectName("urlLabel")
        self.url_lbl.setWordWrap(True)
        self.info_layout.addWidget(self.url_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.info_layout.addWidget(self.progress_bar)

        self.info_row = QHBoxLayout()
        self.info_row.setSpacing(8)
        
        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("infoLabel")
        self.info_row.addWidget(self.status_lbl)
        
        self.sparkline = SparklineWidget()
        self.sparkline.setVisible(False)
        self.info_row.addWidget(self.sparkline)
        self.info_row.addStretch(1)
        
        self.info_layout.addLayout(self.info_row)
        layout.addLayout(self.info_layout, 1)

        # 3. Action Buttons Section
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(8)
        
        self.action_btn = QPushButton()
        self.action_btn.setFixedSize(28, 28)
        self.action_btn.setToolTip("Open File")
        self.action_btn.clicked.connect(self.open_file)
        
        self.folder_btn = QPushButton()
        self.folder_btn.setFixedSize(28, 28)
        self.folder_btn.setToolTip("Show in Folder")
        self.folder_btn.clicked.connect(self.show_in_folder)

        self.retry_btn = QPushButton()
        self.retry_btn.setFixedSize(28, 28)
        self.retry_btn.setToolTip("Retry Download")
        self.retry_btn.clicked.connect(self.retry_download)

        self.pause_btn = QPushButton()
        self.pause_btn.setFixedSize(28, 28)
        self.pause_btn.setToolTip("Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        
        self.cancel_btn = QPushButton()
        self.cancel_btn.setFixedSize(28, 28)
        self.cancel_btn.setToolTip("Cancel Download")
        self.cancel_btn.clicked.connect(self.cancel_download)
        
        self.delete_btn = QPushButton()
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setToolTip("Remove from history")
        self.delete_btn.clicked.connect(self.delete_item)
        
        self.btn_layout.addWidget(self.action_btn)
        self.btn_layout.addWidget(self.folder_btn)
        self.btn_layout.addWidget(self.retry_btn)
        self.btn_layout.addWidget(self.pause_btn)
        self.btn_layout.addWidget(self.cancel_btn)
        self.btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(self.btn_layout)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()
        self.update_ui()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        
        self.action_btn.setIcon(get_tinted_icon("assets/open.svg", ic, QSize(14, 14)))
        self.folder_btn.setIcon(get_tinted_icon("assets/folder.svg", ic, QSize(14, 14)))
        self.retry_btn.setIcon(get_tinted_icon("assets/reload.svg", ic, QSize(14, 14)))
        self.pause_btn.setIcon(get_tinted_icon("assets/pause.svg", ic, QSize(14, 14)))
        self.cancel_btn.setIcon(get_tinted_icon("assets/cancel.svg", ic, QSize(14, 14)))
        self.delete_btn.setIcon(get_tinted_icon("assets/remove.svg", ic, QSize(14, 14)))

        self.setStyleSheet(f"""
            #downloadCard {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
                padding: 12px;
            }}
            #downloadCard:hover {{
                border: 1px solid {c['accent_blue']};
            }}
            QLabel {{
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                background: transparent;
                border: none;
            }}
            QLabel#filenameLabel {{
                color: {c['text_primary']};
                font-size: 14px;
                font-weight: 600;
            }}
            QLabel#urlLabel {{
                color: {c['text_secondary']};
                font-size: 11px;
            }}
            QLabel#infoLabel {{
                color: {c['text_secondary']};
                font-size: 11px;
            }}
            QPushButton {{
                background-color: {c['btn_bg']};
                border: none;
                border-radius: 14px;
                padding: 6px;
            }}
            QPushButton:hover {{
                background-color: {c['btn_hover']};
            }}
            QProgressBar {{
                border: none;
                background-color: {c['btn_bg']};
                height: 3px;
                text-align: center;
                border-radius: 1.5px;
            }}
            QProgressBar::chunk {{
                background-color: {c['accent_blue']};
                border-radius: 1.5px;
            }}
        """)

    def mouseDoubleClickEvent(self, event):
        if self.item["state"] == 2:
            self.open_file()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.item["state"] == 2:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not self.drag_start_position:
            return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        filepath = self.item["full_path"]
        if not os.path.exists(filepath):
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(filepath)])
        drag.setMimeData(mime_data)
        
        provider = QFileIconProvider()
        info = QFileInfo(filepath)
        icon = provider.icon(info)
        drag.setPixmap(icon.pixmap(QSize(32, 32)))
        
        drag.exec(Qt.DropAction.CopyAction)

    def toggle_pause(self):
        if self.item and self.item["request"]:
            req = self.item["request"]
            if req.isPaused():
                req.resume()
            else:
                req.pause()
            self.update_ui()

    def update_ui(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        latest = DownloadTracker.instance().find_item(self.item["id"])
        if latest:
            self.item = latest
        state = self.item["state"]
        
        if state == 1:
            self.progress_bar.setVisible(True)
            self.sparkline.setVisible(True)
            total = self.item["total_bytes"]
            received = self.item["received_bytes"]
            
            self.speed_history.append(self.item["speed"])
            self.speed_history = self.speed_history[-15:]
            self.sparkline.set_history(self.speed_history)
            
            percent = int((received / total) * 100) if total > 0 else 0
            is_paused = self.item["request"] and self.item["request"].isPaused()
            if is_paused:
                self.pause_btn.setIcon(get_tinted_icon("assets/play.svg", ic, QSize(14, 14)))
                self.pause_btn.setToolTip("Resume")
                size_str = self.format_size(received)
                total_str = self.format_size(total) if total > 0 else "unknown"
                self.status_lbl.setText(f"{percent}% — Paused — {size_str} of {total_str}")
                self.progress_bar.setMaximum(100)
                self.progress_bar.setValue(percent)
                self.sparkline.setVisible(False)
            else:
                self.pause_btn.setIcon(get_tinted_icon("assets/pause.svg", ic, QSize(14, 14)))
                self.pause_btn.setToolTip("Pause")
                if total > 0:
                    self.progress_bar.setMaximum(100)
                    self.progress_bar.setValue(percent)
                    
                    size_str = self.format_size(received) + " / " + self.format_size(total)
                    speed_str = self.format_size(self.item["speed"]) + "/s"
                    eta_str = self.format_eta(self.item["eta"])
                    self.status_lbl.setText(f"{percent}% — {size_str} — {speed_str} — {eta_str} remaining")
                else:
                    self.progress_bar.setMaximum(0)
                    self.status_lbl.setText(f"{self.format_size(received)} downloaded — calculating speed...")
                
            self.action_btn.setVisible(False)
            self.folder_btn.setVisible(False)
            self.retry_btn.setVisible(False)
            self.pause_btn.setVisible(True)
            self.cancel_btn.setVisible(True)
            self.delete_btn.setVisible(False)
            
        elif state == 2:
            self.progress_bar.setVisible(False)
            self.sparkline.setVisible(False)
            size_str = self.format_size(self.item["total_bytes"])
            self.status_lbl.setText(f"Completed ({size_str}) — {self.item['timestamp']}")
            
            self.action_btn.setVisible(True)
            self.folder_btn.setVisible(True)
            self.retry_btn.setVisible(True)
            self.pause_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.delete_btn.setVisible(True)
            
        elif state == 3:
            self.progress_bar.setVisible(False)
            self.sparkline.setVisible(False)
            self.status_lbl.setText(f"Cancelled — {self.item['timestamp']}")
            
            self.action_btn.setVisible(False)
            self.folder_btn.setVisible(False)
            self.retry_btn.setVisible(True)
            self.pause_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.delete_btn.setVisible(True)
            
        elif state == 4:
            self.progress_bar.setVisible(False)
            self.sparkline.setVisible(False)
            self.status_lbl.setText(f"Failed / Interrupted — {self.item['timestamp']}")
            
            self.action_btn.setVisible(False)
            self.folder_btn.setVisible(False)
            self.retry_btn.setVisible(True)
            self.pause_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.delete_btn.setVisible(True)

    def retry_download(self):
        url = self.item.get("url") or self.item.get("download_url")
        if url and not url.startswith("tron:"):
            from PyQt6.QtWidgets import QApplication
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, "navigate_to_url"):
                    widget.navigate_to_url(url)
                    break

    def format_size(self, size):
        if size < 1024: return f"{size} B"
        elif size < 1024 * 1024: return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024: return f"{size / (1024 * 1024):.1f} MB"
        else: return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def format_eta(self, seconds):
        if seconds <= 0: return "unknown"
        elif seconds < 60: return f"{seconds}s"
        else: return f"{seconds // 60}m {seconds % 60}s"

    def open_file(self):
        path = self.item["full_path"]
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.status_lbl.setText("Error: File does not exist anymore.")

    def show_in_folder(self):
        path = self.item["full_path"]
        if os.path.exists(path):
            folder = os.path.dirname(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            self.status_lbl.setText("Error: Directory does not exist.")

    def cancel_download(self):
        DownloadTracker.instance().remove_download(self.item["id"])

    def delete_item(self):
        DownloadTracker.instance().remove_download(self.item["id"])


class DownloadsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("downloadsPage")
        self.current_category = "All"
        self.card_widgets = {}

        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 24, 12, 24)
        sidebar_layout.setSpacing(4)
        
        self.category_icons = {
            "All": "assets/cat_all.svg",
            "Documents": "assets/cat_docs.svg",
            "Videos": "assets/cat_videos.svg",
            "Images": "assets/cat_images.svg",
            "Archives": "assets/cat_archives.svg",
            "Other": "assets/cat_other.svg"
        }
        
        self.sidebar_btns = {}
        for category in CATEGORIES.keys():
            btn = QPushButton(category)
            btn.setProperty("active", category == "All")
            btn.setProperty("categoryName", category)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setObjectName(f"sideBtn_{category}")
            btn.setProperty("class", "sidebarBtn")
            btn.clicked.connect(self.on_category_clicked)
            sidebar_layout.addWidget(btn)
            self.sidebar_btns[category] = btn
            
        sidebar_layout.addStretch(1)
        main_h_layout.addWidget(self.sidebar)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        self.title_lbl = QLabel("Downloads")
        self.title_lbl.setObjectName("pageTitle")
        
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("searchBar")
        self.search_bar.setPlaceholderText("Search downloads...")
        self.search_bar.textChanged.connect(self.load_downloads)
        self.search_bar.setFixedWidth(240)
        self.search_bar.setFixedHeight(32)
        
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setObjectName("clearBtn")
        self.clear_btn.clicked.connect(self.clear_history)
        
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch(1)
        header_layout.addWidget(self.search_bar)
        header_layout.addWidget(self.clear_btn)
        content_layout.addLayout(header_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.scroll_content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setContentsMargins(0, 0, 16, 0)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch(1)
        
        self.scroll.setWidget(self.scroll_content)
        content_layout.addWidget(self.scroll, 1)

        self.empty_state_frame = QFrame()
        self.empty_state_frame.setObjectName("emptyState")
        empty_layout = QVBoxLayout(self.empty_state_frame)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(12)
        
        self.empty_icon = QLabel()
        self.empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_icon)
        
        empty_txt = QLabel("No downloads found")
        empty_txt.setObjectName("emptyText")
        empty_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_txt)
        
        content_layout.addWidget(self.empty_state_frame, 1)
        self.empty_state_frame.hide()

        main_h_layout.addWidget(self.content_widget, 1)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

        DownloadTracker.instance().downloads_updated.connect(self.load_downloads)
        self.load_downloads()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]

        for cat, btn in self.sidebar_btns.items():
            icon_path = self.category_icons.get(cat, "assets/cat_other.svg")
            btn.setIcon(get_tinted_icon(icon_path, ic, QSize(16, 16)))
            btn.setIconSize(QSize(16, 16))

        self.empty_icon.setPixmap(get_tinted_icon("assets/download.svg", c["text_secondary"], QSize(48, 48)).pixmap(QSize(48, 48)))

        self.setStyleSheet(f"""
            #downloadsPage {{
                background-color: {c['page_bg']};
            }}
            QLabel#pageTitle {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                font-size: 20px;
                font-weight: 600;
            }}
            QLineEdit#searchBar {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 16px;
                padding: 4px 14px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {c['text_primary']};
            }}
            QLineEdit#searchBar:focus {{
                border: 1px solid {c['accent_blue']};
            }}
            QPushButton#clearBtn {{
                background-color: {c['btn_bg']};
                color: {c['text_primary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 500;
                border-radius: 6px;
                padding: 6px 14px;
                border: none;
            }}
            QPushButton#clearBtn:hover {{
                background-color: {c['btn_hover']};
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['card_border']};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['accent_blue']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QFrame#sidebar {{
                background-color: {c['card_bg']};
                border-right: 1px solid {c['card_border']};
            }}
            QPushButton.sidebarBtn {{
                text-align: left;
                padding: 10px 16px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {c['text_secondary']};
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton.sidebarBtn:hover {{
                background-color: {c['btn_bg']};
                color: {c['text_primary']};
            }}
            QPushButton.sidebarBtn[active="true"] {{
                background-color: {c['btn_bg']};
                color: {c['accent_blue']};
                font-weight: 600;
            }}
            #emptyState {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
                padding: 40px;
            }}
            #emptyText {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: 500;
            }}
        """)

    def on_category_clicked(self):
        sender = self.sender()
        category = sender.property("categoryName")
        self.current_category = category
        
        for name, btn in self.sidebar_btns.items():
            btn.setProperty("active", name == category)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        self.load_downloads()

    def load_downloads(self):
        filter_text = self.search_bar.text().strip().lower()
        downloads = sorted(DownloadTracker.instance().downloads, key=lambda x: (x.get("state") == 1, x.get("id", 0)), reverse=True)
        current_ids = set()

        matched_count = 0
        for item in downloads:
            item_id = item["id"]
            if filter_text and filter_text not in item["filename"].lower():
                continue
                
            ext = os.path.splitext(item["filename"])[1].lower()
            if self.current_category != "All":
                if self.current_category == "Other":
                    classified = (ext in CATEGORIES["Documents"] or ext in CATEGORIES["Videos"] or 
                                  ext in CATEGORIES["Images"] or ext in CATEGORIES["Archives"])
                    if classified:
                        continue
                else:
                    if ext not in CATEGORIES[self.current_category]:
                        continue
            
            matched_count += 1
            current_ids.add(item_id)

            if item_id in self.card_widgets:
                card = self.card_widgets[item_id]
                card.update_ui()
            else:
                card = DownloadItemWidget(item, query=filter_text)
                self.card_widgets[item_id] = card
                
            self.list_layout.removeWidget(card)
            self.list_layout.insertWidget(matched_count - 1, card)

        to_remove = [k for k in self.card_widgets.keys() if k not in current_ids]
        for k in to_remove:
            card = self.card_widgets.pop(k)
            self.list_layout.removeWidget(card)
            card.deleteLater()

        if matched_count == 0:
            self.scroll.hide()
            self.empty_state_frame.show()
        else:
            self.scroll.show()
            self.empty_state_frame.hide()

    def clear_history(self):
        DownloadTracker.instance().clear_all()


class DownloadBubbleRow(QFrame):
    """Represent a single row inside the toolbar dropdown history list."""
    def __init__(self, item, parent_bubble):
        super().__init__(parent_bubble)
        self.item = item
        self.parent_bubble = parent_bubble
        self.setObjectName("bubbleRowCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(16, 16)
        row1.addWidget(self.icon_lbl)
        
        self.name_lbl = QLabel()
        self.name_lbl.setObjectName("rowTitle")
        row1.addWidget(self.name_lbl, 1)
        
        self.pause_btn = QPushButton()
        self.pause_btn.setFixedSize(22, 22)
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.clicked.connect(self.toggle_pause)
        
        self.cancel_btn = QPushButton()
        self.cancel_btn.setFixedSize(22, 22)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_download)
        
        self.folder_btn = QPushButton()
        self.folder_btn.setFixedSize(22, 22)
        self.folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_btn.clicked.connect(self.show_in_folder)
        
        row1.addWidget(self.pause_btn)
        row1.addWidget(self.cancel_btn)
        row1.addWidget(self.folder_btn)
        layout.addLayout(row1)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.info_lbl = QLabel()
        self.info_lbl.setObjectName("rowInfo")
        layout.addWidget(self.info_lbl)
        
        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()
        self.update_row()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]

        self.pause_btn.setIcon(get_tinted_icon("assets/pause.svg", ic, QSize(12, 12)))
        self.cancel_btn.setIcon(get_tinted_icon("assets/cancel.svg", ic, QSize(12, 12)))
        self.folder_btn.setIcon(get_tinted_icon("assets/folder.svg", ic, QSize(12, 12)))

        self.setStyleSheet(f"""
            QFrame#bubbleRowCard {{
                background-color: {c['menu_hover']};
                border: 1px solid {c['card_border']};
                border-radius: 8px;
            }}
            QLabel#rowTitle {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#rowInfo {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 500;
            }}
            QProgressBar {{
                border: none;
                background-color: {c['btn_bg']};
                height: 5px;
                border-radius: 2.5px;
            }}
            QProgressBar::chunk {{
                background-color: {c['accent_blue']};
                border-radius: 2.5px;
            }}
            QPushButton {{
                background-color: {c['btn_bg']};
                border: none;
                border-radius: 11px;
            }}
            QPushButton:hover {{
                background-color: {c['btn_hover']};
            }}
        """)

    def update_row(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        latest = DownloadTracker.instance().find_item(self.item["id"])
        if latest:
            self.item = latest
        
        metrics = self.name_lbl.fontMetrics()
        filename = self.item.get("filename", "Download")
        elided = metrics.elidedText(filename, Qt.TextElideMode.ElideRight, 200)
        self.name_lbl.setText(elided)
        
        provider = QFileIconProvider()
        full_path = self.item.get("full_path", "")
        if full_path:
            info = QFileInfo(full_path)
            icon = provider.icon(info)
        else:
            icon = QIcon()
        if icon.isNull():
            icon = provider.icon(QFileIconProvider.IconType.File)
        self.icon_lbl.setPixmap(icon.pixmap(QSize(16, 16)))
        
        state = self.item.get("state", 2)
        if state == 1:
            self.progress_bar.setVisible(True)
            self.pause_btn.setVisible(True)
            self.cancel_btn.setVisible(True)
            self.folder_btn.setVisible(False)
            
            total = self.item.get("total_bytes", 0)
            received = self.item.get("received_bytes", 0)
            
            if self.item.get("request") and self.item["request"].isPaused():
                self.pause_btn.setIcon(get_tinted_icon("assets/play.svg", ic, QSize(12, 12)))
                self.info_lbl.setText("Paused")
                self.progress_bar.setMaximum(100)
                if total > 0:
                    self.progress_bar.setValue(int((received / total) * 100))
                else:
                    self.progress_bar.setValue(0)
            else:
                self.pause_btn.setIcon(get_tinted_icon("assets/pause.svg", ic, QSize(12, 12)))
                if total > 0:
                    self.progress_bar.setMaximum(100)
                    self.progress_bar.setValue(int((received / total) * 100))
                    speed_str = self.format_size(self.item.get("speed", 0)) + "/s"
                    self.info_lbl.setText(f"{speed_str}  •  {self.format_eta(self.item.get('eta', 0))} remaining")
                else:
                    self.progress_bar.setMaximum(0)
                    self.info_lbl.setText(f"{self.format_size(received)} downloaded")
        elif state == 2:
            self.progress_bar.setVisible(False)
            self.pause_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.folder_btn.setVisible(True)
            self.info_lbl.setText("✓ Completed")
        else:
            self.progress_bar.setVisible(False)
            self.pause_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.folder_btn.setVisible(False)
            self.info_lbl.setText("✕ Cancelled/Failed")

    def toggle_pause(self):
        if self.item and self.item.get("request"):
            req = self.item["request"]
            if req.isPaused():
                req.resume()
            else:
                req.pause()
            self.update_row()
            self.parent_bubble.update_bubble(force=True)

    def cancel_download(self):
        if self.item:
            DownloadTracker.instance().remove_download(self.item["id"])
            self.parent_bubble.update_bubble(force=True)

    def show_in_folder(self):
        if self.item:
            path = self.item.get("full_path", "")
            if path and os.path.exists(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
            elif path and os.path.exists(os.path.dirname(path)):
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
            self.parent_bubble.hide()

    def format_size(self, size):
        if size < 1024: return f"{size} B"
        elif size < 1024*1024: return f"{size/1024:.1f} KB"
        else: return f"{size/(1024*1024):.1f} MB"

    def format_eta(self, seconds):
        if seconds <= 0: return "calculating..."
        elif seconds < 60: return f"{seconds}s"
        else: return f"{seconds//60}m {seconds%60}s"


class DownloadBubblePopup(QWidget):
    """Dropdown list from the toolbar that displays recent downloads."""
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setObjectName("downloadBubble")
        self.setFixedWidth(350)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        
        self.header_lbl = QLabel("Recent Downloads")
        self.header_lbl.setObjectName("popupHeaderTitle")
        header.addWidget(self.header_lbl)
        header.addStretch(1)
        
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        self.rows_container = QWidget()
        self.rows_container.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(8)
        layout.addWidget(self.rows_container)

        self.show_all_btn = QPushButton("Show all downloads in Tron")
        self.show_all_btn.setObjectName("showAllBtn")
        self.show_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_all_btn.clicked.connect(self.show_all_downloads)
        layout.addWidget(self.show_all_btn)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        self.hide()
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide)

        DownloadTracker.instance().downloads_updated.connect(lambda: self.update_bubble())

    def enterEvent(self, event):
        if hasattr(self, "auto_hide_timer"):
            self.auto_hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if hasattr(self, "auto_hide_timer") and self.isVisible():
            self.auto_hide_timer.start(3000)
        super().leaveEvent(event)

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        self.close_btn.setIcon(get_tinted_icon("assets/cancel.svg", ic, QSize(12, 12)))
        self.setStyleSheet(f"""
            #downloadBubble {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
            }}
            QLabel#popupHeaderTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 700;
                color: {c['text_primary']};
                background: transparent;
            }}
            QPushButton#showAllBtn {{
                background-color: {c['accent_blue']};
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }}
            QPushButton#showAllBtn:hover {{
                background-color: {c['btn_hover']};
            }}
        """)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {c['btn_hover']};
            }}
        """)

    def show_for_item(self, item):
        btn = self.parent_window.title_bar.download_btn
        btn.show()
        btn_pos = btn.mapTo(self.parent_window, QPoint(0, 0))
        
        target_x = btn_pos.x() + btn.width() - self.width()
        min_x = 10
        max_x = max(10, self.parent_window.width() - self.width() - 10)
        x = max(min_x, min(target_x, max_x))

        start_y = btn_pos.y() + btn.height() - 10
        end_y = btn_pos.y() + btn.height() + 6
        
        self.move(x, start_y)
        self.show()
        self.update_bubble(force=True)
        self.raise_()
        
        self.anim.stop()
        self.anim.setStartValue(QPoint(x, start_y))
        self.anim.setEndValue(QPoint(x, end_y))
        self.anim.start()

        if hasattr(self, "auto_hide_timer"):
            self.auto_hide_timer.stop()
            self.auto_hide_timer.start(5000)

    def update_bubble(self, force=False):
        if self.isHidden() and not force:
            return
            
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        all_downloads = sorted(DownloadTracker.instance().downloads, key=lambda x: (x.get("state") == 1, x.get("id", 0)), reverse=True)
        downloads = all_downloads[:4]
        
        header_footer_height = 95

        if not downloads:
            empty_lbl = QLabel("No recent downloads")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c = ThemeManager.instance().colors()
            empty_lbl.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px; padding: 24px 0; background: transparent;")
            self.rows_layout.addWidget(empty_lbl)
            self.setFixedHeight(header_footer_height + 56)
        else:
            item_height = 68
            computed_height = header_footer_height + (len(downloads) * item_height)
            self.setFixedHeight(computed_height)
            for d in downloads:
                row = DownloadBubbleRow(d, self)
                self.rows_layout.addWidget(row)

    def toggle_bubble(self):
        if self.isVisible():
            self.hide()
            return
        self.show()
        self.update_bubble(force=True)
        btn = self.parent_window.title_bar.download_btn
        btn_pos = btn.mapTo(self.parent_window, QPoint(0, 0))
        target_x = btn_pos.x() + btn.width() - self.width()
        min_x = 10
        max_x = max(10, self.parent_window.width() - self.width() - 10)
        x = max(min_x, min(target_x, max_x))
        y = btn_pos.y() + btn.height() + 6
        self.move(x, y)
        self.raise_()

    def show_all_downloads(self):
        self.parent_window.open_downloads_page()
        self.hide()
