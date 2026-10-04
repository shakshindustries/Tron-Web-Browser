import os
import re
import json
import urllib.request
from urllib.parse import urlparse
from PyQt6.QtCore import Qt, QSize, QUrl, QRectF, QPointF, QThread, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QPainterPath, QColor, QPen, QLinearGradient, QRadialGradient, QFont
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QGridLayout, QScrollArea, QDialog, QFileDialog, QColorDialog,
    QGraphicsDropShadowEffect, QSizePolicy, QCheckBox, QApplication,
    QStyle, QStyleOption
)
from theme_manager import ThemeManager, parse_color, get_tinted_icon, resolve_resource
from settings_manager import SettingsManager

DEFAULT_SHORTCUTS = [
    {"title": "Google", "url": "https://www.google.com", "badge": "G", "color": "#4285f4"},
    {"title": "YouTube", "url": "https://www.youtube.com", "badge": "YT", "color": "#ff0000"},
    {"title": "GitHub", "url": "https://www.github.com", "badge": "GH", "color": "#24292e"},
    {"title": "Reddit", "url": "https://www.reddit.com", "badge": "RD", "color": "#ff4500"},
    {"title": "Wikipedia", "url": "https://www.wikipedia.org", "badge": "W", "color": "#636466"},
    {"title": "Twitter / X", "url": "https://www.x.com", "badge": "X", "color": "#000000"},
    {"title": "ChatGPT", "url": "https://chatgpt.com", "badge": "AI", "color": "#10a37f"},
]

PRESET_WALLPAPERS = {
    "cyberpunk": {
        "name": "Tron Cyber",
        "grad": [("#090d16", 0.0), ("#0f172a", 0.4), ("#0369a1", 0.85), ("#06b6d4", 1.0)],
        "type": "radial"
    },
    "sunset": {
        "name": "Sunset Glow",
        "grad": [("#2e0854", 0.0), ("#701a75", 0.35), ("#be123c", 0.7), ("#f97316", 1.0)],
        "type": "linear"
    },
    "aurora": {
        "name": "Northern Lights",
        "grad": [("#022c22", 0.0), ("#064e3b", 0.35), ("#0f766e", 0.7), ("#06b6d4", 1.0)],
        "type": "linear"
    },
    "deep_space": {
        "name": "Deep Space",
        "grad": [("#030712", 0.0), ("#0c1222", 0.5), ("#1e1b4b", 1.0)],
        "type": "radial"
    },
    "oceanic": {
        "name": "Oceanic Breeze",
        "grad": [("#082f49", 0.0), ("#0369a1", 0.5), ("#38bdf8", 1.0)],
        "type": "linear"
    },
    "obsidian": {
        "name": "Obsidian Slate",
        "grad": [("#0b0f19", 0.0), ("#182234", 0.5), ("#334155", 1.0)],
        "type": "radial"
    },
}

STOCK_WALLPAPERS = [
    {"id": "tron_cyber", "name": "Tron Cyber", "path": "assets/wallpapers/tron_cyber.png", "thumb": "assets/wallpapers/thumbnails/tron_cyber.png"},
    {"id": "neon_cityscape", "name": "Neon City", "path": "assets/wallpapers/neon_cityscape.png", "thumb": "assets/wallpapers/thumbnails/neon_cityscape.png"},
    {"id": "deep_nebula", "name": "Deep Nebula", "path": "assets/wallpapers/deep_nebula.png", "thumb": "assets/wallpapers/thumbnails/deep_nebula.png"},
    {"id": "cosmic_glow", "name": "Cosmic Glow", "path": "assets/wallpapers/cosmic_glow.png", "thumb": "assets/wallpapers/thumbnails/cosmic_glow.png"},
    {"id": "misty_mountains", "name": "Mountains", "path": "assets/wallpapers/misty_mountains.png", "thumb": "assets/wallpapers/thumbnails/misty_mountains.png"},
    {"id": "sunset_horizon", "name": "Sunset Glow", "path": "assets/wallpapers/sunset_horizon.png", "thumb": "assets/wallpapers/thumbnails/sunset_horizon.png"},
    {"id": "oceanic_breeze", "name": "Ocean Breeze", "path": "assets/wallpapers/oceanic_breeze.png", "thumb": "assets/wallpapers/thumbnails/oceanic_breeze.png"},
    {"id": "cyber_forest", "name": "Cyber Forest", "path": "assets/wallpapers/cyber_forest.png", "thumb": "assets/wallpapers/thumbnails/cyber_forest.png"},
    {"id": "aurora_borealis", "name": "Aurora", "path": "assets/wallpapers/aurora_borealis.png", "thumb": "assets/wallpapers/thumbnails/aurora_borealis.png"},
    {"id": "obsidian_geometry", "name": "Obsidian", "path": "assets/wallpapers/obsidian_geometry.png", "thumb": "assets/wallpapers/thumbnails/obsidian_geometry.png"},
    {"id": "minimalist_wave", "name": "Fluid Wave", "path": "assets/wallpapers/minimalist_wave.png", "thumb": "assets/wallpapers/thumbnails/minimalist_wave.png"},
    {"id": "starry_twilight", "name": "Starry Night", "path": "assets/wallpapers/starry_twilight.png", "thumb": "assets/wallpapers/thumbnails/starry_twilight.png"},
]

EXPANDED_ACCENT_COLORS = [
    ("Tron Blue (Default)", "#1a73e8"),
    ("Cyber Blue", "#2563eb"),
    ("Ocean Cyan", "#0284c7"),
    ("Emerald Green", "#059669"),
    ("Mint Lime", "#10b981"),
    ("Sunset Rose", "#e11d48"),
    ("Coral Orange", "#f97316"),
    ("Vibrant Purple", "#7c3aed"),
    ("Amber Gold", "#f59e0b"),
    ("Crimson Red", "#dc2626"),
    ("Obsidian Slate", "#475569"),
]

# Directory to cache fetched website favicons
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".tron_browser", "favicons")
os.makedirs(CACHE_DIR, exist_ok=True)


class SearchHistoryManager:
    @staticmethod
    def get_history():
        return SettingsManager.instance().get("newtab_search_history", [])

    @staticmethod
    def add_query(query):
        query = query.strip()
        if not query:
            return
        h = list(SettingsManager.instance().get("newtab_search_history", []))
        if query in h:
            h.remove(query)
        h.insert(0, query)
        SettingsManager.instance().set("newtab_search_history", h[:30])

    @staticmethod
    def remove_query(query):
        h = list(SettingsManager.instance().get("newtab_search_history", []))
        if query in h:
            h.remove(query)
            SettingsManager.instance().set("newtab_search_history", h)

    @staticmethod
    def clear_all():
        SettingsManager.instance().set("newtab_search_history", [])


class NewTabSuggestThread(QThread):
    suggestions_ready = pyqtSignal(list)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            if not self.query:
                self.suggestions_ready.emit([])
                return
            import urllib.parse
            encoded = urllib.parse.quote(self.query)
            url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={encoded}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                suggestions = data[1][:6]
                self.suggestions_ready.emit(suggestions)
        except Exception:
            self.suggestions_ready.emit([])


class NewTabSearchInput(QLineEdit):
    down_pressed = pyqtSignal()
    up_pressed = pyqtSignal()
    escape_pressed = pyqtSignal()
    focused_in = pyqtSignal()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focused_in.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Down:
            self.down_pressed.emit()
            return
        elif event.key() == Qt.Key.Key_Up:
            self.up_pressed.emit()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            return
        super().keyPressEvent(event)


class NewTabSearchRow(QFrame):
    def __init__(self, item, index, dropdown, parent=None):
        super().__init__(parent)
        self.item = item
        self.index = index
        self.dropdown = dropdown
        self.setObjectName("newTabSearchRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self._hovered = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Icon
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(16, 16)
        layout.addWidget(self.icon_lbl)

        # Query Text
        self.text_lbl = QLabel(item["query"])
        self.text_lbl.setStyleSheet("font-size: 13.5px; font-weight: 500; font-family: 'Segoe UI', system-ui, sans-serif;")
        layout.addWidget(self.text_lbl, 1)

        # Delete Button for history
        if item["type"] == "history":
            self.del_btn = QPushButton()
            self.del_btn.setFixedSize(24, 24)
            self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.del_btn.setToolTip("Delete from history")
            self.del_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background: rgba(225, 29, 72, 0.15);
                }
            """)
            self.del_btn.clicked.connect(self._on_delete_clicked)
            layout.addWidget(self.del_btn)
        else:
            self.del_btn = None

        self.update_style(False)

    def _on_delete_clicked(self):
        SearchHistoryManager.remove_query(self.item["query"])
        self.dropdown.on_row_deleted(self.item["query"])

    def enterEvent(self, e):
        self._hovered = True
        self.update_style(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update_style(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.del_btn and self.del_btn.underMouse():
                return
            self.dropdown.select_item(self.item["query"])
        super().mousePressEvent(e)

    def update_style(self, selected=False):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        ic = c["icon_stroke"]

        if self.item["type"] == "history":
            self.icon_lbl.setPixmap(get_tinted_icon("assets/history.svg", c["accent_blue"], QSize(16, 16)).pixmap(QSize(16, 16)))
        else:
            self.icon_lbl.setPixmap(get_tinted_icon("assets/search.svg", ic, QSize(16, 16)).pixmap(QSize(16, 16)))

        if self.del_btn:
            self.del_btn.setIcon(get_tinted_icon("assets/close.svg", c["text_secondary"], QSize(10, 10)))

        text_col = "#f8fafc" if is_dark else "#0f172a"
        hover_bg = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.05)"
        active_bg = hover_bg if (selected or self._hovered) else "transparent"

        self.setStyleSheet(f"""
            QFrame#newTabSearchRow {{
                background-color: {active_bg};
                border-radius: 0px;
                border: none;
            }}
            QLabel {{
                color: {text_col};
                background: transparent;
                border: none;
            }}
        """)


class NewTabSearchDropdown(QFrame):
    def __init__(self, newtab_page, parent=None):
        super().__init__(parent)
        self.newtab_page = newtab_page
        self.setObjectName("newTabSearchDropdown")
        self.items = []
        self.selected_index = -1
        self.row_widgets = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 6)
        self.main_layout.setSpacing(0)

        # Rows Box
        self.rows_box = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_box)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.main_layout.addWidget(self.rows_box)

        # Footer Box
        self.footer_box = QWidget()
        f_layout = QHBoxLayout(self.footer_box)
        f_layout.setContentsMargins(14, 4, 14, 2)
        f_layout.setSpacing(6)

        self.clear_all_btn = QPushButton("Clear all searches")
        self.clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_all_btn.setIcon(get_tinted_icon("assets/trash.svg", "#94a3b8", QSize(13, 13)))
        self.clear_all_btn.clicked.connect(self._on_clear_all_clicked)
        f_layout.addStretch()
        f_layout.addWidget(self.clear_all_btn)
        self.main_layout.addWidget(self.footer_box)

        self.update_styles()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        bg_mode = SettingsManager.instance().get("newtab_bg_mode", "default")
        has_wallpaper = (bg_mode != "default")

        if is_dark:
            card_bg = "rgba(24, 24, 37, 0.95)" if has_wallpaper else "rgba(26, 27, 38, 0.98)"
            btn_col = "#94a3b8"
        else:
            card_bg = "rgba(255, 255, 255, 0.96)" if has_wallpaper else "#ffffff"
            btn_col = c["text_secondary"]

        active_border = c["accent_blue"]

        self.setStyleSheet(f"""
            QFrame#newTabSearchDropdown {{
                background-color: {card_bg};
                border-left: 1.5px solid {active_border};
                border-right: 1.5px solid {active_border};
                border-bottom: 1.5px solid {active_border};
                border-top: none;
                border-bottom-left-radius: 24px;
                border-bottom-right-radius: 24px;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {btn_col};
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(225, 29, 72, 0.15);
                color: #e11d48;
            }}
        """)
        for row in self.row_widgets:
            row.update_style(False)

    def show_items(self, history_items, suggestion_items):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.row_widgets.clear()
        self.items = []
        self.selected_index = -1

        for q in history_items:
            self.items.append({"type": "history", "query": q})
        for q in suggestion_items:
            if q not in history_items:
                self.items.append({"type": "suggest", "query": q})

        if not self.items:
            self.hide()
            self.newtab_page.on_dropdown_visibility_changed(False)
            return

        for idx, item in enumerate(self.items):
            row = NewTabSearchRow(item, idx, self)
            self.rows_layout.addWidget(row)
            self.row_widgets.append(row)

        has_history = any(it["type"] == "history" for it in self.items)
        self.footer_box.setVisible(has_history)

        self.update_styles()
        self.show()
        self.newtab_page.on_dropdown_visibility_changed(True)

    def on_row_deleted(self, query):
        current_text = self.newtab_page.search_input.text().strip()
        self.newtab_page.refresh_suggestions(current_text)

    def _on_clear_all_clicked(self):
        SearchHistoryManager.clear_all()
        current_text = self.newtab_page.search_input.text().strip()
        self.newtab_page.refresh_suggestions(current_text)

    def select_item(self, query):
        self.newtab_page.search_input.setText(query)
        self.hide()
        self.newtab_page.on_dropdown_visibility_changed(False)
        self.newtab_page._on_search_submitted()

    def navigate_selection(self, step):
        if not self.items:
            return
        self.selected_index += step
        if self.selected_index < 0:
            self.selected_index = len(self.items) - 1
        elif self.selected_index >= len(self.items):
            self.selected_index = 0

        for i, row in enumerate(self.row_widgets):
            row.update_style(i == self.selected_index)

        selected_query = self.items[self.selected_index]["query"]
        self.newtab_page.search_input.setText(selected_query)

    def execute_selected(self):
        if 0 <= self.selected_index < len(self.items):
            self.select_item(self.items[self.selected_index]["query"])
            return True
        return False


class AsyncFaviconFetcher(QThread):
    """Background worker to download real favicons for any website without blocking UI."""
    icon_ready = pyqtSignal(str, str) # url, cached_path

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            domain = urlparse(self.url).netloc
            if not domain:
                return
            
            clean_name = re.sub(r'[^a-zA-Z0-9_\.]', '_', domain) + ".png"
            cached_path = os.path.join(CACHE_DIR, clean_name)
            
            if os.path.exists(cached_path) and os.path.getsize(cached_path) > 0:
                self.icon_ready.emit(self.url, cached_path)
                return

            api_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = response.read()
                if len(data) > 0:
                    with open(cached_path, "wb") as f:
                        f.write(data)
                    self.icon_ready.emit(self.url, cached_path)
                    return
        except Exception:
            pass

        # Fallback to DuckDuckGo favicon service
        try:
            domain = urlparse(self.url).netloc
            clean_name = re.sub(r'[^a-zA-Z0-9_\.]', '_', domain) + ".png"
            cached_path = os.path.join(CACHE_DIR, clean_name)
            ddg_url = f"https://icons.duckduckgo.com/ip3/{domain}.ico"
            req = urllib.request.Request(ddg_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                if len(data) > 0:
                    with open(cached_path, "wb") as f:
                        f.write(data)
                    self.icon_ready.emit(self.url, cached_path)
        except Exception:
            pass


class ShortcutCard(QFrame):
    """Modern speed-dial card displaying authentic site favicon with hover effects."""
    def __init__(self, title, url, badge=None, color=None, on_click=None, on_delete=None, parent=None):
        super().__init__(parent)
        self.url = url
        self.badge = badge or title[:2].upper()
        self.color = color or "#1a73e8"
        self.on_click = on_click
        self.on_delete = on_delete
        
        self.setFixedSize(92, 92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("shortcutCard")
        self._hovered = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon backdrop container
        self.icon_badge = QLabel()
        self.icon_badge.setFixedSize(46, 46)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_badge, 0, Qt.AlignmentFlag.AlignCenter)

        # Title Label
        display_title = title if len(title) <= 11 else title[:9] + "..."
        self.title_lbl = QLabel(display_title)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        # Delete button with clean SVG icon (no emojis!)
        self.del_btn = QPushButton(self)
        self.del_btn.setFixedSize(18, 18)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setIcon(get_tinted_icon("assets/close.svg", "#ffffff", QSize(9, 9)))
        self.del_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.55);
                border-radius: 9px;
                border: none;
            }
            QPushButton:hover {
                background: #e11d48;
            }
        """)
        self.del_btn.move(self.width() - 22, 4)
        if self.on_delete:
            self.del_btn.clicked.connect(lambda: self.on_delete(self.url))
        self.del_btn.hide()

        self._setup_icon()
        self.update_style()
        ThemeManager.instance().theme_changed.connect(self.update_style)

    def _setup_icon(self):
        domain = urlparse(self.url).netloc
        if domain:
            clean_name = re.sub(r'[^a-zA-Z0-9_\.]', '_', domain) + ".png"
            cached = os.path.join(CACHE_DIR, clean_name)
            if os.path.exists(cached) and os.path.getsize(cached) > 0:
                pix = QPixmap(cached).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.icon_badge.setPixmap(pix)
                self.icon_badge.setStyleSheet("""
                    QLabel {
                        background-color: rgba(255, 255, 255, 0.95);
                        border-radius: 23px;
                        border: 1px solid rgba(0, 0, 0, 0.08);
                    }
                """)
                return

        # Fallback to monogram and fetch authentic site favicon asynchronously
        self.icon_badge.setText(self.badge)
        self.icon_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {self.color};
                color: #ffffff;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 16px;
                font-weight: 700;
                border-radius: 23px;
            }}
        """)
        self._fetcher = AsyncFaviconFetcher(self.url)
        self._fetcher.icon_ready.connect(self._on_favicon_fetched)
        self._fetcher.start()

    def _on_favicon_fetched(self, url, path):
        if url == self.url and os.path.exists(path):
            pix = QPixmap(path).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_badge.setText("")
            self.icon_badge.setPixmap(pix)
            self.icon_badge.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.95);
                    border-radius: 23px;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                }
            """)

    def enterEvent(self, e):
        self._hovered = True
        self.del_btn.show()
        self.update_style()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.del_btn.hide()
        self.update_style()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and not self.del_btn.underMouse():
            if self.on_click:
                self.on_click(self.url)
        super().mousePressEvent(e)

    def update_style(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        bg_mode = SettingsManager.instance().get("newtab_bg_mode", "default")
        has_wallpaper = (bg_mode != "default")

        if has_wallpaper:
            card_bg = "rgba(15, 23, 42, 0.72)" if self._hovered else "rgba(15, 23, 42, 0.52)"
            border = c["accent_blue"] if self._hovered else "rgba(255, 255, 255, 0.16)"
            text_color = "#ffffff"
        else:
            card_bg = "rgba(255, 255, 255, 0.95)" if self._hovered else ("rgba(255, 255, 255, 0.08)" if is_dark else "rgba(255, 255, 255, 0.65)")
            border = c["accent_blue"] if self._hovered else ("rgba(255, 255, 255, 0.14)" if is_dark else "rgba(0, 80, 180, 0.12)")
            text_color = c["text_primary"]

        self.setStyleSheet(f"""
            QFrame#shortcutCard {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 16px;
            }}
        """)
        self.title_lbl.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }}
        """)


class AddShortcutCard(QFrame):
    """Button to add a custom shortcut."""
    def __init__(self, on_add, parent=None):
        super().__init__(parent)
        self.on_add = on_add
        self.setFixedSize(92, 92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("addShortcutCard")
        self._hovered = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_lbl = QLabel("+")
        self.icon_lbl.setFixedSize(46, 46)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        self.title_lbl = QLabel("Add shortcut")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_lbl, 0, Qt.AlignmentFlag.AlignCenter)

        self.update_style()
        ThemeManager.instance().theme_changed.connect(self.update_style)

    def enterEvent(self, e):
        self._hovered = True
        self.update_style()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update_style()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.on_add()
        super().mousePressEvent(e)

    def update_style(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        bg_mode = SettingsManager.instance().get("newtab_bg_mode", "default")
        has_wallpaper = (bg_mode != "default")

        if has_wallpaper:
            card_bg = "rgba(15, 23, 42, 0.72)" if self._hovered else "rgba(15, 23, 42, 0.45)"
            border = c["accent_blue"] if self._hovered else "rgba(255, 255, 255, 0.16)"
            text_color = "#e2e8f0"
        else:
            card_bg = "rgba(255, 255, 255, 0.20)" if self._hovered else ("rgba(255, 255, 255, 0.06)" if is_dark else "rgba(255, 255, 255, 0.55)")
            border = c["accent_blue"] if self._hovered else ("rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 80, 180, 0.10)")
            text_color = c["text_secondary"]

        self.setStyleSheet(f"""
            QFrame#addShortcutCard {{
                background-color: {card_bg};
                border: 1px dashed {border};
                border-radius: 16px;
            }}
        """)
        self.icon_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {'rgba(255, 255, 255, 0.12)' if (is_dark or has_wallpaper) else 'rgba(0, 80, 180, 0.08)'};
                color: {c['accent_blue'] if self._hovered else (text_color)};
                font-size: 24px;
                font-weight: 300;
                border-radius: 23px;
            }}
        """)
        self.title_lbl.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 11px;
                font-weight: 500;
                background: transparent;
            }}
        """)


class AddShortcutDialog(QDialog):
    """Clean modal dialog to add custom shortcut."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Shortcut")
        self.setFixedSize(360, 200)
        c = ThemeManager.instance().colors()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['menu_bg']};
                color: {c['text_primary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            QLineEdit {{
                background-color: {c['address_bg']};
                border: 1px solid {c['address_border']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {c['address_text']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {c['accent_blue']};
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name (e.g. YouTube)")
        layout.addWidget(self.name_input)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("URL (e.g. https://www.youtube.com)")
        layout.addWidget(self.url_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"background: {c['btn_bg']}; color: {c['text_primary']}; border: none;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Done")
        save_btn.setStyleSheet(f"background: {c['accent_blue']}; color: #ffffff; border: none;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)


class StockWallpaperCard(QFrame):
    """Visual thumbnail card for curated stock wallpapers in the customization panel."""
    clicked = pyqtSignal(str)

    def __init__(self, wp_info, is_selected=False, parent=None):
        super().__init__(parent)
        self.wp_info = wp_info
        self._selected = is_selected
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("stockWpCard")
        self.setFixedSize(142, 96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.img_lbl = QLabel(self)
        self.img_lbl.setFixedSize(130, 64)
        self.img_lbl.setScaledContents(True)
        self.img_lbl.setStyleSheet("border-radius: 6px; background: #0f172a;")

        thumb_path = wp_info.get("thumb", "")
        if os.path.exists(thumb_path):
            self.img_lbl.setPixmap(QPixmap(thumb_path))

        layout.addWidget(self.img_lbl)

        self.name_lbl = QLabel(wp_info["name"], self)
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_lbl)
        ThemeManager.instance().theme_changed.connect(self.update_style)
        self.update_style()

    def set_selected(self, selected):
        self._selected = selected
        self.update_style()

    def enterEvent(self, e):
        self._hovered = True
        self.update_style()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update_style()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.wp_info["path"])
        super().mousePressEvent(e)

    def update_style(self):
        c = ThemeManager.instance().colors()
        is_light = not ThemeManager.instance().is_dark()
        accent = c['accent_blue']

        if self._selected:
            img_border = f"2.5px solid {accent}"
            name_color = accent
            name_weight = "700"
        elif self._hovered:
            img_border = f"2px solid {accent}"
            name_color = c['text_primary']
            name_weight = "600"
        else:
            img_border = f"1px solid {c['card_border']}"
            name_color = c['text_secondary']
            name_weight = "500"

        self.setStyleSheet("""
            QFrame#stockWpCard {
                background: transparent;
                border: none;
            }
        """)
        self.img_lbl.setStyleSheet(f"""
            QLabel {{
                border-radius: 8px;
                border: {img_border};
                background: #0f172a;
            }}
        """)
        self.name_lbl.setStyleSheet(f"""
            QLabel {{
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 11px;
                font-weight: {name_weight};
                color: {name_color};
                background: transparent;
                border: none;
            }}
        """)


class CustomizeSidebar(QWidget):
    """Chrome-style slide-out side panel on the right edge of the New Tab page."""
    close_requested = pyqtSignal()

    def __init__(self, newtab_page, parent=None):
        super().__init__(parent)
        self.newtab_page = newtab_page
        self.setFixedWidth(350)
        self.setObjectName("customizeSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self._init_ui()
        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Header with Title and Close button
        self.header = QFrame()
        self.header.setFixedHeight(54)
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(18, 0, 14, 0)

        self.title = QLabel("Customize Tron")
        self.title.setStyleSheet("font-size: 16px; font-weight: 700;")
        h_layout.addWidget(self.title)
        h_layout.addStretch()

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close_requested.emit)
        h_layout.addWidget(self.close_btn)
        main_layout.addWidget(self.header)

        # Divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setFixedHeight(1)
        main_layout.addWidget(self.divider)

        # 2. Scrollable Settings Body
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")

        self.body = QWidget()
        b_layout = QVBoxLayout(self.body)
        b_layout.setContentsMargins(18, 16, 18, 24)
        b_layout.setSpacing(20)

        # --- SECTION: APPEARANCE & WALLPAPERS ---
        self.sec1_title = QLabel("Background Wallpaper")
        b_layout.addWidget(self.sec1_title)

        self.upload_btn = QPushButton("  Upload from device")
        self.upload_btn.setFixedHeight(40)
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.clicked.connect(self._on_upload_clicked)
        b_layout.addWidget(self.upload_btn)

        self.reset_btn = QPushButton("  Classic Default")
        self.reset_btn.setFixedHeight(36)
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._on_reset_bg_clicked)
        b_layout.addWidget(self.reset_btn)

        # Stock Wallpapers (12)
        self.preset_lbl = QLabel("Stock Wallpapers (12)")
        b_layout.addWidget(self.preset_lbl)

        self.wallpaper_cards = []
        wp_grid = QGridLayout()
        wp_grid.setSpacing(10)
        current_stock = SettingsManager.instance().get("newtab_stock_bg", "")
        current_mode = SettingsManager.instance().get("newtab_bg_mode", "default")

        for idx, wp in enumerate(STOCK_WALLPAPERS):
            is_sel = (current_mode == "stock_image" and current_stock == wp["path"])
            card = StockWallpaperCard(wp, is_selected=is_sel, parent=self.body)
            card.clicked.connect(self._on_stock_wallpaper_clicked)
            self.wallpaper_cards.append(card)
            wp_grid.addWidget(card, idx // 2, idx % 2)

        b_layout.addLayout(wp_grid)

        # --- SECTION: TRON ACCENT COLOR ---
        b_layout.addSpacing(6)
        self.sec2_title = QLabel("Tron Accent Color")
        b_layout.addWidget(self.sec2_title)

        color_grid = QGridLayout()
        color_grid.setSpacing(10)
        c_row, c_col = 0, 0
        for name, col_hex in EXPANDED_ACCENT_COLORS:
            dot = QPushButton()
            dot.setFixedSize(36, 36)
            dot.setCursor(Qt.CursorShape.PointingHandCursor)
            dot.setToolTip(name)
            dot.setStyleSheet(f"""
                QPushButton {{
                    background-color: {col_hex};
                    border-radius: 18px;
                    border: 2px solid #ffffff;
                }}
                QPushButton:hover {{
                    border: 3px solid #2563eb;
                }}
            """)
            dot.clicked.connect(lambda checked=False, n=name: self._on_accent_selected(n))
            color_grid.addWidget(dot, c_row, c_col)
            c_col += 1
            if c_col > 4:
                c_col = 0
                c_row += 1

        # Custom Color Swatch
        self.custom_dot = QPushButton()
        self.custom_dot.setFixedSize(36, 36)
        self.custom_dot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.custom_dot.setToolTip("Custom Color Palette")
        self.custom_dot.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff007f, stop:0.5 #7928ca, stop:1 #0070f3);
                border-radius: 18px;
                border: 2px solid #ffffff;
            }
        """)
        self.custom_dot.clicked.connect(self._on_custom_color_clicked)
        color_grid.addWidget(self.custom_dot, c_row, c_col)
        b_layout.addLayout(color_grid)

        # --- SECTION: THEME MODE ---
        b_layout.addSpacing(6)
        self.sec3_title = QLabel("Color Theme")
        b_layout.addWidget(self.sec3_title)

        theme_layout = QHBoxLayout()
        self.light_btn = QPushButton("  Light")
        self.light_btn.setFixedHeight(34)
        self.light_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.light_btn.clicked.connect(lambda: ThemeManager.instance().set_theme("light"))
        theme_layout.addWidget(self.light_btn)

        self.dark_btn = QPushButton("  Dark")
        self.dark_btn.setFixedHeight(34)
        self.dark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dark_btn.clicked.connect(lambda: ThemeManager.instance().set_theme("dark"))
        theme_layout.addWidget(self.dark_btn)
        b_layout.addLayout(theme_layout)

        # --- SECTION: SHORTCUTS TOGGLE ---
        b_layout.addSpacing(6)
        self.show_shortcuts_cb = QCheckBox("Show shortcuts on New Tab")
        self.show_shortcuts_cb.setChecked(SettingsManager.instance().get("newtab_show_shortcuts", True))
        self.show_shortcuts_cb.toggled.connect(self._on_shortcuts_toggled)
        b_layout.addWidget(self.show_shortcuts_cb)

        b_layout.addStretch()
        self.scroll.setWidget(self.body)
        main_layout.addWidget(self.scroll)

        self.update_styles()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        is_light = not is_dark
        accent = c['accent_blue']
        sidebar_bg = c['card_bg']
        header_bg = c['menu_bg'] if is_dark else '#f8fafc'
        border_col = c['card_border']
        text_primary = c['text_primary']
        text_secondary = c['text_secondary']

        self.setStyleSheet(f"""
            QWidget#customizeSidebar {{
                background-color: {sidebar_bg};
                border-left: 1px solid {border_col};
            }}
        """)
        self.header.setStyleSheet(f"""
            QFrame {{
                background-color: {header_bg};
                border-bottom: 1px solid {border_col};
            }}
        """)
        self.title.setStyleSheet(f"""
            QLabel {{
                color: {text_primary};
                font-size: 15px;
                font-weight: 700;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
        """)
        self.close_btn.setIcon(get_tinted_icon("assets/close.svg", text_secondary, QSize(12, 12)))
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                background: {'rgba(0,0,0,0.08)' if is_light else 'rgba(255,255,255,0.12)'};
            }}
        """)
        self.divider.setStyleSheet(f"background: {border_col}; border: none;")
        self.scroll.setStyleSheet(f"""QScrollArea {{ background: transparent; border: none; }}
            {ThemeManager.instance().scrollbar_style()}""")
        self.body.setStyleSheet("background: transparent;")

        # Section labels: clean modern typography
        sec_style = f"""
            QLabel {{
                color: {c['text_primary']};
                font-size: 13px;
                font-weight: 700;
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: transparent;
                border: none;
                padding: 4px 0px 2px 0px;
            }}
        """
        self.sec1_title.setStyleSheet(sec_style)
        if hasattr(self, 'sec2_title'):
            self.sec2_title.setStyleSheet(sec_style)
        if hasattr(self, 'sec3_title'):
            self.sec3_title.setStyleSheet(sec_style)
        self.preset_lbl.setStyleSheet(f"""
            QLabel {{
                color: {text_secondary};
                font-size: 12px;
                font-weight: 600;
                padding: 2px 0px;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
        """)

        # Upload button — accent primary CTA
        self.upload_btn.setIcon(get_tinted_icon("assets/folder.svg", "#ffffff", QSize(16, 16)))
        self.upload_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                border: none;
                border-radius: 10px;
                color: #ffffff;
                font-weight: 600;
                font-size: 13px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                text-align: left;
                padding-left: 14px;
            }}
            QPushButton:hover {{
                background-color: {accent}cc;
            }}
            QPushButton:pressed {{
                background-color: {accent}99;
            }}
        """)

        # Reset button — outlined secondary
        self.reset_btn.setIcon(get_tinted_icon("assets/reset.svg", accent, QSize(14, 14)))
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1.5px solid {border_col};
                border-radius: 10px;
                color: {text_primary};
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI', system-ui, sans-serif;
                text-align: left;
                padding-left: 14px;
            }}
            QPushButton:hover {{
                border-color: {accent};
                background-color: {'rgba(26,115,232,0.05)' if is_light else 'rgba(255,255,255,0.06)'};
            }}
        """)

        # Light/Dark mode toggle — active one highlighted
        active_btn = f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
        """
        inactive_btn = f"""
            QPushButton {{
                background-color: {'#f1f5f9' if is_light else 'rgba(255,255,255,0.08)'};
                color: {text_secondary};
                border: 1px solid {border_col};
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            QPushButton:hover {{
                border-color: {accent};
                color: {text_primary};
            }}
        """
        cur_light = not is_dark
        self.light_btn.setIcon(get_tinted_icon("assets/sun.svg", "#ffffff" if cur_light else text_secondary, QSize(15, 15)))
        self.dark_btn.setIcon(get_tinted_icon("assets/moon.svg", text_secondary if cur_light else "#ffffff", QSize(15, 15)))
        self.light_btn.setStyleSheet(active_btn if cur_light else inactive_btn)
        self.dark_btn.setStyleSheet(active_btn if not cur_light else inactive_btn)

        # Custom color dot icon
        self.custom_dot.setIcon(get_tinted_icon("assets/palette.svg", "#ffffff", QSize(18, 18)))

        # Shortcuts checkbox
        self.show_shortcuts_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {text_primary};
                font-size: 13px;
                font-weight: 500;
                font-family: 'Segoe UI', system-ui, sans-serif;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 2px solid {border_col};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border-color: {accent};
            }}
        """)

    def _on_upload_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Wallpaper",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if file_path:
            SettingsManager.instance().set("newtab_bg_mode", "custom_image")
            SettingsManager.instance().set("newtab_custom_bg", file_path)
            self.newtab_page.load_background()
            self.newtab_page.update()
            self.newtab_page.update_styles()
            for c in getattr(self, "wallpaper_cards", []):
                c.set_selected(False)

    def _on_reset_bg_clicked(self):
        SettingsManager.instance().set("newtab_bg_mode", "default")
        SettingsManager.instance().set("newtab_custom_bg", "")
        SettingsManager.instance().set("newtab_stock_bg", "")
        self.newtab_page.load_background()
        self.newtab_page.update()
        self.newtab_page.update_styles()
        for c in getattr(self, "wallpaper_cards", []):
            c.set_selected(False)

    def _on_stock_wallpaper_clicked(self, wp_path):
        SettingsManager.instance().set("newtab_bg_mode", "stock_image")
        SettingsManager.instance().set("newtab_stock_bg", wp_path)
        self.newtab_page.load_background()
        self.newtab_page.update()
        self.newtab_page.update_styles()
        for c in getattr(self, "wallpaper_cards", []):
            c.set_selected(c.wp_info.get("path") == wp_path)

    def _on_accent_selected(self, name):
        ThemeManager.instance().set_accent_color(name)
        self.newtab_page.update()
        self.newtab_page.update_styles()

    def _on_custom_color_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            ThemeManager.instance().set_accent_color(color.name())
            self.newtab_page.update()
            self.newtab_page.update_styles()

    def _on_shortcuts_toggled(self, checked):
        SettingsManager.instance().set("newtab_show_shortcuts", checked)
        self.newtab_page.toggle_shortcuts(checked)


class NewTabPage(QWidget):
    """Modern Chrome-style New Tab / Start Page with Right Sidebar Customization, authentic favicons, and adaptive contrast."""
    def __init__(self, browser_window, parent=None):
        super().__init__(parent)
        self.browser_window = browser_window
        self.setObjectName("newTabPage")
        self._bg_pixmap = None
        self.shortcuts = []

        self.load_background()
        self.load_shortcuts()

        # Main Horizontal Layout: Left is Main Start Page Content, Right is Chrome Sidebar
        self.root_layout = QHBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # ----------------------------------------------------
        # 1. Left Content Area (Responsive Centered Hero & Grid)
        # ----------------------------------------------------
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(content_widget)
        c_layout.setContentsMargins(40, 50, 40, 40)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        c_layout.setSpacing(28)

        # Branding Hero
        self.logo_lbl = QLabel()
        self.logo_lbl.setPixmap(QIcon(resolve_resource("assets/app_icon.png")).pixmap(QSize(76, 76)))
        self.logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(self.logo_lbl)

        self.title_lbl = QLabel("Tron")
        self.title_lbl.setObjectName("newTabBrandTitle")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(self.title_lbl)

        # Search Omnibar Hero Card & Suggestion Dropdown in unified Container
        self.search_container = QWidget()
        self.search_container.setObjectName("newTabSearchContainer")
        self.search_container.setFixedWidth(640)
        sc_layout = QVBoxLayout(self.search_container)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(0)

        # Drop shadow on search container
        self.search_shadow = QGraphicsDropShadowEffect(self.search_container)
        self.search_shadow.setBlurRadius(24)
        self.search_shadow.setYOffset(4)
        self.search_shadow.setColor(QColor(0, 0, 0, 45))
        self.search_container.setGraphicsEffect(self.search_shadow)

        self.search_card = QFrame()
        self.search_card.setObjectName("newTabSearchCard")
        self.search_card.setFixedHeight(50)

        s_layout = QHBoxLayout(self.search_card)
        s_layout.setContentsMargins(18, 0, 16, 0)
        s_layout.setSpacing(10)

        self.search_icon = QLabel()
        self.search_icon.setPixmap(get_tinted_icon("assets/search.svg", "#64748b", QSize(18, 18)).pixmap(QSize(18, 18)))
        s_layout.addWidget(self.search_icon)

        self.search_input = NewTabSearchInput()
        self.search_input.setObjectName("newTabSearchInput")
        self.search_input.setPlaceholderText("Search Google or type a URL")
        self.search_input.returnPressed.connect(self._on_search_submitted)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.focused_in.connect(self._on_search_focused)
        self.search_input.down_pressed.connect(lambda: self.search_dropdown.navigate_selection(1))
        self.search_input.up_pressed.connect(lambda: self.search_dropdown.navigate_selection(-1))
        self.search_input.escape_pressed.connect(self._hide_search_dropdown)
        s_layout.addWidget(self.search_input, 1)

        voice_btn = QPushButton()
        voice_btn.setFixedSize(28, 28)
        voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        voice_btn.setToolTip("Search")
        voice_btn.setIcon(get_tinted_icon("assets/search.svg", "#64748b", QSize(16, 16)))
        voice_btn.setStyleSheet("background: transparent; border: none;")
        voice_btn.clicked.connect(self._on_search_submitted)
        s_layout.addWidget(voice_btn)

        sc_layout.addWidget(self.search_card)

        # Google Search Suggestion & History Dropdown
        self.search_dropdown = NewTabSearchDropdown(self)
        self.search_dropdown.hide()
        sc_layout.addWidget(self.search_dropdown)

        c_layout.addWidget(self.search_container, 0, Qt.AlignmentFlag.AlignCenter)

        # Shortcuts Grid
        self.grid_container = QWidget()
        self.grid_container.setFixedWidth(560)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 16, 0, 0)
        self.grid_layout.setSpacing(14)
        c_layout.addWidget(self.grid_container, 0, Qt.AlignmentFlag.AlignCenter)

        show_sc = SettingsManager.instance().get("newtab_show_shortcuts", True)
        self.grid_container.setVisible(show_sc)
        self._populate_shortcuts()

        c_layout.addStretch()
        self.content_scroll.setWidget(content_widget)
        self.root_layout.addWidget(self.content_scroll, 1)

        # ----------------------------------------------------
        # 2. Right Sidebar: Chrome Customization Side Panel
        # ----------------------------------------------------
        self.sidebar = CustomizeSidebar(self, self)
        self.sidebar.close_requested.connect(self.toggle_sidebar)
        self.sidebar.hide() # Hidden by default, toggled via Customize Tron button
        self.root_layout.addWidget(self.sidebar)

        # ----------------------------------------------------
        # 3. Floating "Customize Tron" Button in Bottom Right
        # ----------------------------------------------------
        self.custom_btn = QPushButton("  Customize Tron", self)
        self.custom_btn.setObjectName("customizeBtn")
        self.custom_btn.setFixedHeight(36)
        self.custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.custom_btn.clicked.connect(self.toggle_sidebar)

        btn_shadow = QGraphicsDropShadowEffect(self.custom_btn)
        btn_shadow.setBlurRadius(16)
        btn_shadow.setYOffset(3)
        btn_shadow.setColor(QColor(0, 0, 0, 50))
        self.custom_btn.setGraphicsEffect(btn_shadow)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

        # Scroll Zoom Support for New Tab Page
        self._zoom_factor = 1.0
        self.content_scroll.viewport().installEventFilter(self)
        self.content_scroll.installEventFilter(self)
        content_widget.installEventFilter(self)
        self.search_container.installEventFilter(self)
        self.search_card.installEventFilter(self)
        self.search_input.installEventFilter(self)
        self.grid_container.installEventFilter(self)

    def _on_search_focused(self):
        text = self.search_input.text().strip()
        self.refresh_suggestions(text)

    def _on_search_text_changed(self, text):
        self.refresh_suggestions(text.strip())

    def _hide_search_dropdown(self):
        self.search_dropdown.hide()
        self.on_dropdown_visibility_changed(False)

    def refresh_suggestions(self, query):
        all_hist = SearchHistoryManager.get_history()
        if not query:
            matching_hist = all_hist[:6]
        else:
            matching_hist = [h for h in all_hist if query.lower() in h.lower()][:4]

        if hasattr(self, "_suggest_thread") and self._suggest_thread and self._suggest_thread.isRunning():
            self._suggest_thread.terminate()

        if query:
            self._suggest_thread = NewTabSuggestThread(query)
            self._suggest_thread.suggestions_ready.connect(
                lambda suggestions: self.search_dropdown.show_items(matching_hist, suggestions)
            )
            self._suggest_thread.start()
        else:
            self.search_dropdown.show_items(matching_hist, [])

    def on_dropdown_visibility_changed(self, visible):
        self.update_search_card_style(has_dropdown=visible)

    def mousePressEvent(self, e):
        if hasattr(self, "search_dropdown") and self.search_dropdown.isVisible():
            click_pos = self.content_scroll.widget().mapFrom(self, e.pos())
            if not self.search_container.geometry().contains(click_pos):
                self._hide_search_dropdown()
        super().mousePressEvent(e)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                current_zoom = getattr(self, "_zoom_factor", 1.0)
                if delta > 0:
                    new_zoom = min(current_zoom + 0.1, 2.5)
                else:
                    new_zoom = max(current_zoom - 0.1, 0.4)
                new_zoom = round(new_zoom, 2)
                if abs(new_zoom - current_zoom) > 0.01:
                    self.set_zoom_factor(new_zoom)
                    if hasattr(self.browser_window, "show_zoom_toast"):
                        self.browser_window.show_zoom_toast(new_zoom)
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            current_zoom = getattr(self, "_zoom_factor", 1.0)
            if delta > 0:
                new_zoom = min(current_zoom + 0.1, 2.5)
            else:
                new_zoom = max(current_zoom - 0.1, 0.4)
            new_zoom = round(new_zoom, 2)
            if abs(new_zoom - current_zoom) > 0.01:
                self.set_zoom_factor(new_zoom)
                if hasattr(self.browser_window, "show_zoom_toast"):
                    self.browser_window.show_zoom_toast(new_zoom)
            event.accept()
            return
        super().wheelEvent(event)

    def zoomFactor(self):
        return getattr(self, "_zoom_factor", 1.0)

    def setZoomFactor(self, factor):
        self.set_zoom_factor(factor)

    def set_zoom_factor(self, factor):
        self._zoom_factor = max(0.4, min(factor, 2.5))
        # Scale search container width (base 640)
        base_w = 640
        sc_w = max(340, min(int(base_w * self._zoom_factor), 1100))
        self.search_container.setFixedWidth(sc_w)

        # Scale shortcuts container width (base 560)
        grid_w = max(300, min(int(560 * self._zoom_factor), 1000))
        self.grid_container.setFixedWidth(grid_w)

        # Scale Title font size (base 38)
        title_font_size = max(18, min(int(38 * self._zoom_factor), 72))
        c = ThemeManager.instance().colors()
        bg_mode = SettingsManager.instance().get("newtab_bg_mode", "default")
        has_wallpaper = (bg_mode != "default")
        title_color = "#ffffff" if has_wallpaper else c["text_primary"]
        self.title_lbl.setStyleSheet(f"""
            color: {title_color};
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: {title_font_size}px;
            font-weight: 800;
            letter-spacing: -0.5px;
        """)

        # Scale Logo size (base 76)
        logo_sz = max(36, min(int(76 * self._zoom_factor), 130))
        self.logo_lbl.setPixmap(QIcon(resolve_resource("assets/app_icon.png")).pixmap(QSize(logo_sz, logo_sz)))
        self.update()

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
            self.custom_btn.show()
        else:
            self.sidebar.show()
            self.custom_btn.hide()

    def toggle_shortcuts(self, visible):
        self.grid_container.setVisible(visible)

    def load_background(self):
        sm = SettingsManager.instance()
        mode = sm.get("newtab_bg_mode", "default")
        custom_path = sm.get("newtab_custom_bg", "")
        stock_path = sm.get("newtab_stock_bg", "")

        if mode == "stock_image" and stock_path and os.path.exists(stock_path):
            self._bg_pixmap = QPixmap(stock_path)
        elif mode == "custom_image" and custom_path and os.path.exists(custom_path):
            self._bg_pixmap = QPixmap(custom_path)
        else:
            self._bg_pixmap = None

    def load_shortcuts(self):
        sm = SettingsManager.instance()
        saved = sm.get("newtab_shortcuts", None)
        if saved is not None:
            self.shortcuts = saved
        else:
            self.shortcuts = list(DEFAULT_SHORTCUTS)

    def save_shortcuts(self):
        SettingsManager.instance().set("newtab_shortcuts", self.shortcuts)

    def _populate_shortcuts(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 5
        for i, s in enumerate(self.shortcuts):
            row = i // cols
            col = i % cols
            card = ShortcutCard(
                s["title"],
                s["url"],
                badge=s.get("badge", s["title"][:2].upper()),
                color=s.get("color", "#2563eb"),
                on_click=self._on_shortcut_clicked,
                on_delete=self._on_shortcut_deleted,
                parent=self.grid_container
            )
            self.grid_layout.addWidget(card, row, col)

        total = len(self.shortcuts)
        add_card = AddShortcutCard(on_add=self._on_add_shortcut_clicked, parent=self.grid_container)
        self.grid_layout.addWidget(add_card, total // cols, total % cols)

    def _on_shortcut_clicked(self, url):
        if hasattr(self.browser_window, "navigate_from_newtab"):
            self.browser_window.navigate_from_newtab(self, url)
        else:
            self.browser_window.add_new_tab(url)

    def _on_shortcut_deleted(self, url):
        self.shortcuts = [s for s in self.shortcuts if s["url"] != url]
        self.save_shortcuts()
        self._populate_shortcuts()

    def _on_add_shortcut_clicked(self):
        dlg = AddShortcutDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.name_input.text().strip()
            url = dlg.url_input.text().strip()
            if name and url:
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                self.shortcuts.append({
                    "title": name,
                    "url": url,
                    "badge": name[:2].upper(),
                    "color": "#1a73e8"
                })
                self.save_shortcuts()
                self._populate_shortcuts()

    def _on_search_submitted(self):
        text = self.search_input.text().strip()
        if not text:
            return

        SearchHistoryManager.add_query(text)
        self._hide_search_dropdown()

        if text.startswith("http://") or text.startswith("https://") or ('.' in text and ' ' not in text):
            target_url = text if text.startswith("http") else "https://" + text
        else:
            target_url = SettingsManager.instance().get_search_url(text)

        if hasattr(self.browser_window, "navigate_from_newtab"):
            self.browser_window.navigate_from_newtab(self, target_url)
        else:
            self.browser_window.add_new_tab(target_url)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.custom_btn.adjustSize()
        w = self.custom_btn.width() + 24
        h = self.custom_btn.height()
        self.custom_btn.setGeometry(self.width() - w - 24, self.height() - h - 20, w, h)

    def update_search_card_style(self, has_dropdown=False):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        bg_mode = SettingsManager.instance().get("newtab_bg_mode", "default")
        has_wallpaper = (bg_mode != "default")

        if is_dark:
            card_bg = "rgba(24, 24, 37, 0.95)" if has_wallpaper else "rgba(26, 27, 38, 0.98)"
            card_border = "rgba(255, 255, 255, 0.18)" if has_wallpaper else "rgba(255, 255, 255, 0.15)"
            input_color = "#f8fafc"
            placeholder_color = "#94a3b8"
        else:
            card_bg = "rgba(255, 255, 255, 0.96)" if has_wallpaper else "#ffffff"
            card_border = "rgba(0, 0, 0, 0.14)" if has_wallpaper else "rgba(0, 80, 180, 0.16)"
            input_color = "#0f172a"
            placeholder_color = "#64748b"

        if has_dropdown:
            card_radius = "border-top-left-radius: 24px; border-top-right-radius: 24px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;"
            border_bottom = "border-bottom: none;"
            active_border = c["accent_blue"]
        else:
            card_radius = "border-radius: 24px;"
            border_bottom = ""
            active_border = card_border

        self.search_card.setStyleSheet(f"""
            QFrame#newTabSearchCard {{
                background-color: {card_bg};
                border-left: 1.5px solid {active_border};
                border-right: 1.5px solid {active_border};
                border-top: 1.5px solid {active_border};
                border-bottom: 1.5px solid {active_border};
                {border_bottom}
                {card_radius}
            }}
            QFrame#newTabSearchCard:hover {{
                border-color: {c['accent_blue']};
            }}
            QLineEdit#newTabSearchInput {{
                background: transparent;
                border: none;
                color: {input_color};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 15px;
            }}
            QLineEdit#newTabSearchInput::placeholder {{
                color: {placeholder_color};
            }}
        """)

    def update_styles(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        bg_mode = SettingsManager.instance().get("newtab_bg_mode", "default")
        has_wallpaper = (bg_mode != "default")

        if hasattr(self, "search_icon"):
            self.search_icon.setPixmap(get_tinted_icon("assets/search.svg", c["accent_blue"], QSize(18, 18)).pixmap(QSize(18, 18)))

        if has_wallpaper:
            card_border = "rgba(255, 255, 255, 0.20)"
            title_color = "#ffffff"
            btn_bg = "rgba(15, 23, 42, 0.85)"
            btn_color = "#ffffff"
        else:
            card_border = "rgba(0, 80, 180, 0.16)" if not is_dark else "rgba(255, 255, 255, 0.15)"
            title_color = c["text_primary"]
            btn_bg = "rgba(255, 255, 255, 0.90)" if not is_dark else "rgba(30, 30, 46, 0.85)"
            btn_color = c["text_primary"]

        self.content_scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {ThemeManager.instance().scrollbar_style()}")

        has_dropdown = hasattr(self, "search_dropdown") and self.search_dropdown.isVisible()
        self.update_search_card_style(has_dropdown=has_dropdown)
        if hasattr(self, "search_dropdown"):
            self.search_dropdown.update_styles()

        self.custom_btn.setIcon(get_tinted_icon("assets/edit.svg", btn_color, QSize(15, 15)))
        self.custom_btn.setStyleSheet(f"""
            QPushButton#customizeBtn {{
                background-color: {btn_bg};
                color: {btn_color};
                border: 1px solid {card_border};
                border-radius: 18px;
                padding: 6px 16px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#customizeBtn:hover {{
                border: 1px solid {c['accent_blue']};
            }}
        """)
        self.title_lbl.setStyleSheet(f"""
            color: {title_color};
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 38px;
            font-weight: 800;
            letter-spacing: -0.5px;
        """)
        self.sidebar.update_styles()
        self.update()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        w = float(self.width())
        h = float(self.height())

        sm = SettingsManager.instance()
        mode = sm.get("newtab_bg_mode", "default")
        preset_key = sm.get("newtab_preset_bg", "cyberpunk")

        # 1. Custom or Stock Image Background
        if mode in ("custom_image", "stock_image") and self._bg_pixmap and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)

            # High-end readability ambient overlay
            ambient_grad = QLinearGradient(0.0, 0.0, 0.0, h)
            ambient_grad.setColorAt(0.0, QColor(0, 0, 0, 110))
            ambient_grad.setColorAt(0.5, QColor(0, 0, 0, 70))
            ambient_grad.setColorAt(1.0, QColor(0, 0, 0, 140))
            p.fillRect(self.rect(), ambient_grad)

        # 2. Preset Gradient Background
        elif mode == "preset" and preset_key in PRESET_WALLPAPERS:
            pinfo = PRESET_WALLPAPERS[preset_key]
            if pinfo["type"] == "radial":
                grad = QRadialGradient(w * 0.45, h * 0.35, max(w, h) * 0.75)
                for hex_col, pos in pinfo["grad"]:
                    grad.setColorAt(pos, QColor(hex_col))
                p.fillRect(self.rect(), grad)
            else:
                grad = QLinearGradient(0.0, 0.0, w, h)
                for hex_col, pos in pinfo["grad"]:
                    grad.setColorAt(pos, QColor(hex_col))
                p.fillRect(self.rect(), grad)

            # Soft ambient contrast overlay
            overlay = QColor(0, 0, 0, 50)
            p.fillRect(self.rect(), overlay)

        # 3. Clean Default Theme Background
        else:
            base_bg = parse_color(c["page_bg"])
            p.fillRect(self.rect(), base_bg)
            # Subtle radial light glow in upper-center
            grad = QRadialGradient(w / 2.0, h * 0.35, w * 0.5)
            glow_col = QColor(26, 115, 232, 22) if not is_dark else QColor(138, 180, 248, 15)
            grad.setColorAt(0.0, glow_col)
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), grad)

        p.end()
