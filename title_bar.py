import sys
import json
import urllib.request
import urllib.parse
from PyQt6.QtCore import Qt, QSize, QRectF, QTimer, QPoint, QThread, pyqtSignal, QStringListModel, QEvent
from PyQt6.QtGui import QIcon, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect, QLineEdit, QSizePolicy, QCompleter, QFrame
)
from theme_manager import ThemeManager, parse_color, get_tinted_icon
from settings_manager import SettingsManager

class SearchSuggestThread(QThread):
    suggestions_ready = pyqtSignal(list)

    def __init__(self, query, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        if not self.query or len(self.query) < 2:
            self.suggestions_ready.emit([])
            return
        try:
            encoded = urllib.parse.quote(self.query)
            url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={encoded}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if isinstance(data, list) and len(data) > 1:
                    suggestions = data[1][:6]
                    self.suggestions_ready.emit(suggestions)
        except Exception:
            self.suggestions_ready.emit([])


class DownloadButton(QPushButton):
    """Modern toolbar action button for file downloads with smooth rotating progress arc and success pulse."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_title_bar = parent
        self.setProperty("navButton", True)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_active = False
        self.angle = 0
        self.progress = 0
        self.completed_pulse = 0.0
        
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.rotate)
        ThemeManager.instance().theme_changed.connect(self.update_icon)
        self.update_icon()

    def update_icon(self):
        c = ThemeManager.instance().colors()
        icon_file = "assets/download_active.svg" if self.is_active else "assets/download.svg"
        self.setIcon(get_tinted_icon(icon_file, c["icon_stroke"], QSize(16, 16)))
        self.setIconSize(QSize(16, 16))

    def rotate(self):
        if self.is_active:
            self.angle = (self.angle + 5) % 360
        if self.completed_pulse > 0:
            self.completed_pulse -= 0.02
            if self.completed_pulse <= 0:
                self.completed_pulse = 0.0
                if not self.is_active:
                    self.timer.stop()
                    if self.parent_title_bar and hasattr(self.parent_title_bar, "update_toolbar_button_visibility"):
                        self.parent_title_bar.update_toolbar_button_visibility()
        self.update()

    def set_progress(self, progress):
        self.progress = progress
        self.update()

    def set_active(self, active):
        was_active = self.is_active
        self.is_active = active
        self.update_icon()
        if active:
            self.timer.start()
            self.completed_pulse = 0.0
        else:
            if was_active:
                self.completed_pulse = 1.0
                self.timer.start()
            else:
                if self.completed_pulse <= 0:
                    self.timer.stop()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = ThemeManager.instance().colors()
        
        if self.completed_pulse > 0:
            green_color = QColor(5, 150, 105, int(self.completed_pulse * 180))
            p.setPen(QPen(green_color, 2.0))
            margin = 2.0
            r = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
            p.drawArc(r, 0, 360 * 16)

        if self.is_active:
            pen = QPen(parse_color(c["accent_blue"]), 2.0)
            p.setPen(pen)
            margin = 2.5
            r = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
            
            if self.progress > 0:
                start_angle = 90 * 16
                span_angle = -int(self.progress * 3.6) * 16
                p.drawArc(r, start_angle, span_angle)
            else:
                p.drawArc(r, -self.angle * 16, 120 * 16)
            
        p.end()


class RoundedAddressBar(QWidget):
    """Address bar container with properly rendered rounded corners and focus glow."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._radius = 16
        self._hovered = False
        self.setMouseTracking(True)
        self.setObjectName("addressBar")
        self.setFixedHeight(34)
        ThemeManager.instance().theme_changed.connect(self.update)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()

        w = self.width()
        h = self.height()
        radius = h / 2.0  # Full rounded stadium / capsule shape matching reference

        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        
        is_focused = hasattr(self, "url_bar") and self.url_bar and self.url_bar.hasFocus()
        if not is_dark:
            if is_focused:
                bg_color = QColor("#ffffff")
                border_color = QColor("#3b82f6")
                pen_width = 1.6
            elif self._hovered:
                bg_color = QColor("#f8fafc")
                border_color = QColor("#94a3b8")
                pen_width = 1.2
            else:
                bg_color = QColor("#f1f5f9")
                border_color = QColor("#dbe3ee")
                pen_width = 1.0
        else:
            bg_str = c["address_bg_hover"] if (self._hovered or is_focused) else c["address_bg"]
            bg_color = parse_color(bg_str)
            border_color = parse_color(c["accent_blue"]) if (is_focused or self._hovered) else parse_color(c["address_border"])
            pen_width = 1.5 if is_focused else 1.0

        p.fillPath(path, bg_color)
        p.setPen(QPen(border_color, pen_width))
        p.drawPath(path)
        p.end()


class SuggestionRowWidget(QFrame):
    """Custom row widget inside URL suggestions dropdown with icon, title, url subtext, fill arrow, and delete button."""
    def __init__(self, item, parent_popup):
        super().__init__(parent_popup)
        self.item = item
        self.parent_popup = parent_popup
        self.setObjectName("suggestionRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_selected = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(16, 16)
        layout.addWidget(self.icon_lbl)
        
        text_container = QVBoxLayout()
        text_container.setSpacing(1)
        
        self.title_lbl = QLabel(item.get("title", ""))
        self.title_lbl.setObjectName("suggestionTitle")
        text_container.addWidget(self.title_lbl)
        
        sub_text = item.get("url", "") or item.get("subtext", "")
        self.sub_lbl = QLabel(sub_text)
        self.sub_lbl.setObjectName("suggestionSubtext")
        if not sub_text or sub_text == item.get("title", ""):
            self.sub_lbl.hide()
        text_container.addWidget(self.sub_lbl)
        
        layout.addLayout(text_container, 1)
        
        self.fill_btn = QPushButton("↖")
        self.fill_btn.setFixedSize(22, 22)
        self.fill_btn.setToolTip("Copy to address bar")
        self.fill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fill_btn.clicked.connect(self.on_fill_clicked)
        layout.addWidget(self.fill_btn)
        
        if item.get("type") == "history":
            self.delete_btn = QPushButton()
            self.delete_btn.setFixedSize(22, 22)
            self.delete_btn.setToolTip("Remove from history")
            self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.delete_btn.clicked.connect(self.on_delete_clicked)
            layout.addWidget(self.delete_btn)
        else:
            self.delete_btn = None
            
        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        
        item_type = self.item.get("type", "search")
        if item_type == "history":
            self.icon_lbl.setPixmap(get_tinted_icon("assets/history.svg", ic, QSize(16, 16)).pixmap(QSize(16, 16)))
        elif item_type == "bookmark":
            self.icon_lbl.setPixmap(get_tinted_icon("assets/bookmark.svg", ic, QSize(16, 16)).pixmap(QSize(16, 16)))
        else:
            self.icon_lbl.setPixmap(get_tinted_icon("assets/search.svg", ic, QSize(16, 16)).pixmap(QSize(16, 16)))
            
        if self.delete_btn:
            self.delete_btn.setIcon(get_tinted_icon("assets/cancel.svg", ic, QSize(10, 10)))
            
        bg = c['menu_hover'] if self.is_selected else "transparent"
        self.setStyleSheet(f"""
            QFrame#suggestionRow {{
                background-color: {bg};
                border-radius: 8px;
            }}
            QLabel#suggestionTitle {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#suggestionSubtext {{
                color: {c['accent_blue'] if item_type != 'search' else c['text_secondary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 11px;
                color: {c['text_secondary']};
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {c['btn_hover']};
            }}
        """)

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_styles()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_popup.select_item(self.item)
        super().mousePressEvent(event)

    def on_fill_clicked(self):
        query = self.item.get("url") or self.item.get("title")
        self.parent_popup.fill_url_bar(query)

    def on_delete_clicked(self):
        url = self.item.get("url")
        if url:
            from history_manager import HistoryManager
            HistoryManager.instance().remove_item(url)
            self.parent_popup.remove_row_item(self.item)


class UrlSuggestionPopup(QWidget):
    """Custom dropdown menu for search & history suggestions with icons, subtext, fill arrows, and delete options."""
    def __init__(self, title_bar):
        super().__init__(title_bar.parent_window)
        self.title_bar = title_bar
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setObjectName("urlSuggestionPopup")
        self.items = []
        self.selected_index = -1
        self.widgets = []

        self.container = QWidget(self)
        self.container.setObjectName("popupContainer")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 6, 12, 16)
        main_layout.addWidget(self.container)

        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(3)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 75))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        self.container.setStyleSheet(f"""
            QWidget#popupContainer {{
                background-color: {c['menu_bg']};
                border: 1px solid {c['title_border']};
                border-radius: 14px;
            }}
        """)

    def show_suggestions(self, items):
        if not items:
            self.hide()
            return

        self.setUpdatesEnabled(False)
        self.items = items
        self.selected_index = -1
        
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.widgets.clear()

        for item in items:
            row = SuggestionRowWidget(item, self)
            self.layout.addWidget(row)
            self.widgets.append(row)

        self.reposition()
        self.setUpdatesEnabled(True)
        if self.isHidden():
            self.show()

    def reposition(self):
        if not self.isVisible() or not self.items:
            return
        addr_bar = self.title_bar.address_bar
        self.setFixedWidth(addr_bar.width() + 24)
        row_height = 42
        total_height = 36 + (len(self.items) * row_height)
        self.setFixedHeight(min(total_height, 380))
        pos = addr_bar.mapToGlobal(QPoint(-12, addr_bar.height() - 2))
        self.move(pos)

    def select_item(self, item):
        target = item.get("url") or item.get("title")
        self.title_bar.url_bar.setText(target)
        self.hide()
        self.title_bar.parent_window.navigate_to_url()

    def fill_url_bar(self, text):
        self.title_bar.url_bar.setText(text)
        self.title_bar.url_bar.setFocus()

    def remove_row_item(self, item):
        if item in self.items:
            idx = self.items.index(item)
            self.items.remove(item)
            if idx < len(self.widgets):
                w = self.widgets.pop(idx)
                w.deleteLater()
            if not self.items:
                self.hide()
            else:
                self.reposition()

    def navigate_selection(self, step):
        if not self.items or not self.isVisible():
            return False
        
        if self.selected_index >= 0 and self.selected_index < len(self.widgets):
            self.widgets[self.selected_index].set_selected(False)

        self.selected_index += step
        if self.selected_index < 0:
            self.selected_index = len(self.items) - 1
        elif self.selected_index >= len(self.items):
            self.selected_index = 0

        self.widgets[self.selected_index].set_selected(True)
        sel_item = self.items[self.selected_index]
        target = sel_item.get("url") or sel_item.get("title")
        self.title_bar.url_bar.setText(target)
        self.title_bar.url_bar.setFocus()
        return True

    def execute_selected(self):
        if self.isVisible() and 0 <= self.selected_index < len(self.items):
            self.select_item(self.items[self.selected_index])
            return True
        return False


class HoverIconButton(QPushButton):
    """Clean Chrome-style navigation toolbar button with smooth hover background."""
    def __init__(self, icon_path, is_win_control=False, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.is_win_control = is_win_control
        self.setProperty("navButton", True)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        ThemeManager.instance().theme_changed.connect(self.update_icon_style)
        self.update_icon_style()

    def update_icon_style(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        if self.icon_path:
            self.setIcon(get_tinted_icon(self.icon_path, ic, QSize(16, 16)))
        self.setIconSize(QSize(16, 16))


class SlimProgressBar(QWidget):
    """Slim accent line tracking web page loading progress."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(2)
        self._progress = 0
        self.hide()
        ThemeManager.instance().theme_changed.connect(self.update)

    def set_progress(self, val):
        self._progress = max(0, min(100, val))
        if 0 < self._progress < 100:
            self.show()
        else:
            self.hide()
        self.update()

    def paintEvent(self, event):
        if self._progress <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = ThemeManager.instance().colors()
        accent = parse_color(c["accent_blue"])
        w = int(self.width() * (self._progress / 100.0))
        p.fillRect(0, 0, w, self.height(), accent)
        p.end()


class TitleBar(QWidget):
    """Modern Navigation Toolbar containing Navigation Controls, Omnibox, and Tools."""
    def __init__(self, container, parent_window):
        super().__init__(container)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.parent_window = parent_window
        self.setObjectName("unifiedTitleBar")
        self.setFixedHeight(44)
        self.setMouseTracking(True)
        self.drag_pos = None

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 4, 10, 4)
        main_layout.setSpacing(8)

        # ----------------------------------------------------
        # 1. Left Section: Navigation Controls
        # ----------------------------------------------------
        self.back_btn = self._make_icon_button("assets/back.svg")
        self.back_btn.setObjectName("navPillBtn")
        self.back_btn.setToolTip("Back (Alt+Left)")
        self.fwd_btn = self._make_icon_button("assets/forward.svg")
        self.fwd_btn.setObjectName("navPillBtn")
        self.fwd_btn.setToolTip("Forward (Alt+Right)")
        self.reload_btn = self._make_icon_button("assets/reload.svg")
        self.reload_btn.setObjectName("navPillBtn")
        self.reload_btn.setToolTip("Reload page (Ctrl+R)")
        self.home_btn = self._make_icon_button("assets/home.svg")
        self.home_btn.setObjectName("navPillBtn")
        self.home_btn.setToolTip("Open homepage")

        main_layout.addWidget(self.back_btn)
        main_layout.addWidget(self.fwd_btn)
        main_layout.addWidget(self.reload_btn)
        main_layout.addWidget(self.home_btn)

        # ----------------------------------------------------
        # 2. Center Section: Omnibar (Search & Address)
        # ----------------------------------------------------
        self.address_bar = RoundedAddressBar(self)
        address_layout = QHBoxLayout(self.address_bar)
        address_layout.setContentsMargins(12, 0, 8, 0)
        address_layout.setSpacing(6)
        
        self.search_icon = QLabel()
        self.search_icon.setFixedSize(16, 16)
        self.search_icon.setToolTip("Search or type URL")
        
        self.lock_icon = QLabel()
        self.lock_icon.setFixedSize(16, 16)
        self.lock_icon.setToolTip("Connection is secure (HTTPS)")
        self.lock_icon.hide()

        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("urlInput")
        self.url_bar.setPlaceholderText("Search Google or type a URL")
        self.url_bar.returnPressed.connect(self._on_url_submitted)
        self.url_bar.setClearButtonEnabled(True)
        self.url_bar.textEdited.connect(self._on_text_edited)
        self.url_bar.installEventFilter(self)
        self.address_bar.url_bar = self.url_bar

        self.suggest_thread = None
        self.suggestion_popup = UrlSuggestionPopup(self)

        self.reader_btn = self._make_icon_button("assets/reader.svg")
        self.reader_btn.setFixedSize(26, 26)
        self.reader_btn.setToolTip("Toggle Reader Mode (Ctrl+Alt+R)")
        if hasattr(self.parent_window, "toggle_reader_mode"):
            self.reader_btn.clicked.connect(self.parent_window.toggle_reader_mode)

        self.star_btn = self._make_icon_button("assets/star.svg")
        self.star_btn.setFixedSize(26, 26)
        self.star_btn.setToolTip("Bookmark current page (Ctrl+D)")
        self.star_btn.clicked.connect(self.parent_window.toggle_bookmark_current_page)
        
        self.pwa_btn = QPushButton()
        self.pwa_btn.setFixedSize(26, 26)
        self.pwa_btn.setToolTip("Install this page as an app")
        self.pwa_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pwa_btn.clicked.connect(self.parent_window.trigger_pwa_install)
        self.pwa_btn.hide()
        
        self.title_label = QLabel()
        self.title_label.hide()
        
        self.reader_btn.hide()
        self.star_btn.hide()
        
        address_layout.addWidget(self.lock_icon)
        address_layout.addWidget(self.search_icon)
        address_layout.addWidget(self.url_bar, 1)
        address_layout.addWidget(self.reader_btn)
        address_layout.addWidget(self.star_btn)
        address_layout.addWidget(self.pwa_btn)
        
        main_layout.addWidget(self.address_bar, 1)

        # ----------------------------------------------------
        # 3. Right Section: Toolbar Tools (Star, Download, Extensions, Menu)
        # ----------------------------------------------------
        self.star_toolbar_btn = self._make_icon_button("assets/star.svg")
        self.star_toolbar_btn.setObjectName("navActionBtn")
        self.star_toolbar_btn.setToolTip("Bookmark current page (Ctrl+D)")
        self.star_toolbar_btn.clicked.connect(self.parent_window.toggle_bookmark_current_page)

        self.download_btn = DownloadButton(self)
        self.download_btn.setObjectName("navActionBtn")
        self.download_btn.setToolTip("Downloads (Ctrl+J)")

        self.bookmark_btn = self._make_icon_button("assets/bookmark.svg")
        self.bookmark_btn.setObjectName("navActionBtn")
        self.bookmark_btn.setToolTip("Open Bookmarks (Ctrl+B)")
        self.bookmark_btn.clicked.connect(self.parent_window.open_bookmarks_page)
        self.bookmark_btn.hide() # Collapsed into clean modern right toolbar

        self.menu_btn = self._make_icon_button("assets/menu.svg")
        self.menu_btn.setObjectName("navActionBtn")
        self.menu_btn.setToolTip("Menu & Settings")

        main_layout.addWidget(self.star_toolbar_btn)
        main_layout.addWidget(self.download_btn)
        main_layout.addWidget(self.menu_btn)
        
        self.browser_menu = None
        self._menu_was_visible = False
        self.menu_btn.pressed.connect(self._on_menu_btn_pressed)
        self.menu_btn.clicked.connect(self._on_menu_btn_clicked)

        # 4. Slim Page Load Progress Bar
        self.load_progress_bar = SlimProgressBar(self)

        # Compatibility handles
        self.app_icon_label = QLabel()
        self.app_icon_label.hide()
        self.incognito_badge = QLabel()
        self.incognito_badge.hide()

        ThemeManager.instance().theme_changed.connect(self.update_theme_styles)
        SettingsManager.instance().settings_changed.connect(self.update_toolbar_button_visibility)
        
        self.update_theme_styles()
        self.update_toolbar_button_visibility()

    @property
    def min_btn(self):
        return getattr(self.parent_window.tab_container, "min_btn", None)

    @property
    def max_btn(self):
        return getattr(self.parent_window.tab_container, "max_btn", None)

    @property
    def close_btn(self):
        return getattr(self.parent_window.tab_container, "close_btn", None)

    @property
    def win_controls(self):
        return getattr(self.parent_window.tab_container, "win_controls", None)

    def set_load_progress(self, val):
        if hasattr(self, "load_progress_bar"):
            self.load_progress_bar.set_progress(val)

    def set_reload_state(self, is_loading):
        icon_file = "assets/stop.svg" if is_loading else "assets/reload.svg"
        self.reload_btn.setProperty("icon_path", icon_file)
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        self.reload_btn.setIcon(get_tinted_icon(icon_file, ic, QSize(16, 16)))

    def update_toolbar_button_visibility(self):
        sm = SettingsManager.instance()
        self.bookmark_btn.setVisible(False)
        self.home_btn.setVisible(sm.get("show_home_btn", True))
        self.star_btn.hide()
        if hasattr(self, "star_toolbar_btn"):
            self.star_toolbar_btn.setVisible(sm.get("show_star_btn", True))

        always_show = sm.get("show_download_btn", True)
        if always_show:
            self.download_btn.show()
        else:
            from download_manager import DownloadTracker
            is_downloading = DownloadTracker.instance().is_any_downloading()
            is_pulsing = hasattr(self.download_btn, "completed_pulse") and self.download_btn.completed_pulse > 0
            if is_downloading or is_pulsing:
                self.download_btn.show()
            else:
                self.download_btn.hide()

    def update_theme_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]

        self.back_btn.setIcon(get_tinted_icon("assets/back.svg", ic, QSize(16, 16)))
        self.fwd_btn.setIcon(get_tinted_icon("assets/forward.svg", ic, QSize(16, 16)))
        reload_icon_file = self.reload_btn.property("icon_path") or "assets/reload.svg"
        self.reload_btn.setIcon(get_tinted_icon(reload_icon_file, ic, QSize(16, 16)))
        self.home_btn.setIcon(get_tinted_icon("assets/home.svg", ic, QSize(16, 16)))
        self.bookmark_btn.setIcon(get_tinted_icon("assets/bookmark.svg", ic, QSize(16, 16)))
        self.reader_btn.setIcon(get_tinted_icon("assets/reader.svg", ic, QSize(16, 16)))
        self.menu_btn.setIcon(get_tinted_icon("assets/menu.svg", ic, QSize(16, 16)))
        
        self.search_icon.setPixmap(get_tinted_icon("assets/search.svg", c["address_placeholder"], QSize(16, 16)).pixmap(QSize(16, 16)))
        self.lock_icon.setPixmap(get_tinted_icon("assets/lock.svg", c["accent_blue"], QSize(16, 16)).pixmap(QSize(16, 16)))
        is_dark = ThemeManager.instance().is_dark()
        is_star_active = getattr(self, "_is_star_active", False)
        star_color = "#f59e0b" if is_star_active else ic
        self.star_btn.setIcon(get_tinted_icon("assets/star.svg", star_color, QSize(16, 16)))
        if hasattr(self, "star_toolbar_btn"):
            self.star_toolbar_btn.setIcon(get_tinted_icon("assets/star.svg", star_color, QSize(16, 16)))

        if is_dark:
            nav_pill_qss = """
                QPushButton#navPillBtn, QPushButton#navActionBtn {
                    background: transparent;
                    border: none;
                    border-radius: 16px;
                    padding: 0px;
                }
                QPushButton#navPillBtn:hover, QPushButton#navActionBtn:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    border: none;
                }
                QPushButton#navPillBtn:pressed, QPushButton#navActionBtn:pressed {
                    background-color: rgba(255, 255, 255, 0.20);
                    border: none;
                }
                QPushButton#navPillBtn:disabled, QPushButton#navActionBtn:disabled {
                    background: transparent;
                    border: none;
                    opacity: 0.35;
                }
            """
        else:
            nav_pill_qss = """
                QPushButton#navPillBtn, QPushButton#navActionBtn {
                    background: transparent;
                    border: none;
                    border-radius: 16px;
                    padding: 0px;
                }
                QPushButton#navPillBtn:hover, QPushButton#navActionBtn:hover {
                    background-color: rgba(0, 0, 0, 0.08);
                    border: none;
                }
                QPushButton#navPillBtn:pressed, QPushButton#navActionBtn:pressed {
                    background-color: rgba(0, 0, 0, 0.14);
                    border: none;
                }
                QPushButton#navPillBtn:disabled, QPushButton#navActionBtn:disabled {
                    background: transparent;
                    border: none;
                    opacity: 0.35;
                }
            """

        self.setStyleSheet(f"""
            #unifiedTitleBar {{
                background: {c.get('nav_container_bg', c['window_bg'])};
                border-bottom: 1px solid {c['title_border']};
            }}
            
            #urlInput {{
                background: transparent;
                border: none;
                color: {c['address_text']};
                font-family: "Segoe UI", "Roboto", sans-serif;
                font-size: 13px;
                padding: 2px 2px;
                selection-background-color: {c['accent_blue']};
            }}
            #urlInput::placeholder {{
                color: {c['address_placeholder']};
            }}
            
            {nav_pill_qss}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "load_progress_bar"):
            self.load_progress_bar.setGeometry(0, self.height() - 2, self.width(), 2)
        if hasattr(self, "suggestion_popup"):
            self.suggestion_popup.reposition()

    def eventFilter(self, watched, event):
        if watched == self.url_bar:
            if event.type() == QEvent.Type.FocusIn:
                self.address_bar.update()
                QTimer.singleShot(0, self.url_bar.selectAll)
            elif event.type() == QEvent.Type.MouseButtonPress:
                if not self.url_bar.hasFocus():
                    self.address_bar.update()
                    QTimer.singleShot(0, self.url_bar.selectAll)
            elif event.type() == QEvent.Type.FocusOut:
                self.address_bar.update()
                QTimer.singleShot(150, self._check_focus_out)
            elif hasattr(self, "suggestion_popup") and self.suggestion_popup.isVisible() and event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Down:
                    self.suggestion_popup.navigate_selection(1)
                    return True
                elif event.key() == Qt.Key.Key_Up:
                    self.suggestion_popup.navigate_selection(-1)
                    return True
                elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    if self.suggestion_popup.execute_selected():
                        return True
                    else:
                        self.suggestion_popup.hide()
                elif event.key() == Qt.Key.Key_Escape:
                    self.suggestion_popup.hide()
                    return True
        return super().eventFilter(watched, event)

    def _on_url_submitted(self):
        if hasattr(self, "suggestion_popup") and self.suggestion_popup:
            self.suggestion_popup.hide()
        self.parent_window.navigate_to_url()

    def set_bookmark_star_active(self, active):
        self._is_star_active = active
        c = ThemeManager.instance().colors()
        if active:
            self.star_btn.setIcon(get_tinted_icon("assets/star.svg", "#f59e0b", QSize(16, 16)))
            self.star_btn.setToolTip("Bookmarked! Click to remove bookmark")
        else:
            ic = c["icon_stroke"]
            self.star_btn.setIcon(get_tinted_icon("assets/star.svg", ic, QSize(16, 16)))
            self.star_btn.setToolTip("Bookmark current page")

    def _check_focus_out(self):
        if hasattr(self, "suggestion_popup") and self.suggestion_popup.isVisible():
            focused = QApplication.focusWidget()
            if focused != self.url_bar and not (focused and self.suggestion_popup.isAncestorOf(focused)):
                self.suggestion_popup.hide()

    def _on_text_edited(self, text):
        text_str = text.strip()
        if not text_str or text_str.startswith("tron:"):
            if hasattr(self, "suggestion_popup"):
                self.suggestion_popup.hide()
            return
            
        items = []
        
        # 1. Matching History Entries
        try:
            from history_manager import HistoryManager
            hist = HistoryManager.instance().history
            for h in hist:
                title = h.get("title", "")
                url = h.get("url", "")
                if text_str.lower() in title.lower() or text_str.lower() in url.lower():
                    items.append({
                        "type": "history",
                        "title": title or url,
                        "url": url
                    })
                    if len(items) >= 3:
                        break
        except Exception:
            pass

        # 2. Matching Bookmark Entries
        try:
            from bookmarks_manager import BookmarksManager
            bms = BookmarksManager.instance().bookmarks
            for b in bms:
                title = b.get("title", "")
                url = b.get("url", "")
                if text_str.lower() in title.lower() or text_str.lower() in url.lower():
                    if not any(item["url"] == url for item in items):
                        items.append({
                            "type": "bookmark",
                            "title": title or url,
                            "url": url
                        })
                        if len(items) >= 5:
                            break
        except Exception:
            pass

        # 3. Direct Google Search Option
        items.append({
            "type": "search",
            "title": text_str,
            "url": "Search Google"
        })

        if not hasattr(self, "suggestion_popup"):
            self.suggestion_popup = UrlSuggestionPopup(self)
            
        self.suggestion_popup.show_suggestions(items)

        if SettingsManager.instance().get("autocomplete_enabled", True):
            if self.suggest_thread and self.suggest_thread.isRunning():
                self.suggest_thread.terminate()
            self.suggest_thread = SearchSuggestThread(text_str, self)
            self.suggest_thread.suggestions_ready.connect(self._on_suggestions_ready)
            self.suggest_thread.start()

    def _on_suggestions_ready(self, suggestions):
        if not hasattr(self, "suggestion_popup") or not self.suggestion_popup.isVisible():
            return
            
        existing_titles = {item.get("title", "").lower() for item in self.suggestion_popup.items}
        new_items = list(self.suggestion_popup.items)
        
        for s in suggestions[:4]:
            if s.lower() not in existing_titles:
                new_items.append({
                    "type": "search",
                    "title": s,
                    "url": "Search Google"
                })
                
        self.suggestion_popup.show_suggestions(new_items[:7])

    def _make_icon_button(self, icon_path, is_win_control=False):
        btn = HoverIconButton(icon_path, is_win_control=is_win_control)
        return btn

    def update_max_icon(self, is_maximized):
        if hasattr(self.parent_window, "tab_container") and hasattr(self.parent_window.tab_container, "update_max_icon"):
            self.parent_window.tab_container.update_max_icon(is_maximized)

    def _on_menu_btn_pressed(self):
        if self.browser_menu and self.browser_menu.isVisible():
            self._menu_was_visible = True
        else:
            self._menu_was_visible = False

    def _on_menu_btn_clicked(self):
        if self._menu_was_visible:
            self._menu_was_visible = False
            return
        self.show_browser_menu()

    def show_browser_menu(self):
        if not self.browser_menu:
            from browser_menu import BrowserMenu
            self.browser_menu = BrowserMenu(self.parent_window, self.menu_btn)

        self.browser_menu.show_menu()
