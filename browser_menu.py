import sys
from PyQt6.QtCore import Qt, QPoint, QSize, QRectF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QWidget, QApplication
)
from theme_manager import ThemeManager, parse_color, get_tinted_icon

class ZoomControlWidget(QWidget):
    """Modern Zoom Bar with larger buttons, custom slider, live badge, and 100% Reset button."""
    def __init__(self, parent_menu):
        super().__init__(parent_menu)
        self.parent_menu = parent_menu
        self.setObjectName("zoomControlRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self.zoom_lbl = QLabel("Zoom")
        self.zoom_lbl.setObjectName("zoomTitle")
        layout.addWidget(self.zoom_lbl)

        self.minus_btn = QPushButton()
        self.minus_btn.setFixedSize(28, 28)
        self.minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minus_btn.setToolTip("Zoom Out (-10%)")
        self.minus_btn.clicked.connect(self.zoom_out)
        layout.addWidget(self.minus_btn)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(25)
        self.slider.setMaximum(300)
        self.slider.setValue(100)
        self.slider.setFixedHeight(22)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.valueChanged.connect(self.on_slider_change)
        layout.addWidget(self.slider, 1)

        self.plus_btn = QPushButton()
        self.plus_btn.setFixedSize(28, 28)
        self.plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plus_btn.setToolTip("Zoom In (+10%)")
        self.plus_btn.clicked.connect(self.zoom_in)
        layout.addWidget(self.plus_btn)

        self.val_badge = QLabel("100%")
        self.val_badge.setObjectName("zoomBadge")
        self.val_badge.setFixedWidth(44)
        self.val_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.val_badge)

        self.reset_btn = QPushButton()
        self.reset_btn.setFixedSize(28, 28)
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setToolTip("Reset to 100%")
        self.reset_btn.clicked.connect(self.zoom_reset)
        layout.addWidget(self.reset_btn)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]

        self.minus_btn.setIcon(get_tinted_icon("assets/minus.svg", ic, QSize(14, 14)))
        self.plus_btn.setIcon(get_tinted_icon("assets/plus.svg", ic, QSize(14, 14)))
        self.reset_btn.setIcon(get_tinted_icon("assets/reset.svg", ic, QSize(14, 14)))

        self.setStyleSheet(f"""
            #zoomControlRow {{
                background-color: {c['btn_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
            }}
            QLabel#zoomTitle {{
                font-family: 'Segoe UI', Roboto, sans-serif;
                font-size: 13px;
                color: {c['text_secondary']};
                font-weight: 600;
            }}
            QLabel#zoomBadge {{
                font-family: 'Segoe UI', Roboto, sans-serif;
                font-size: 12px;
                font-weight: 700;
                color: {c['text_primary']};
                background: {c['pill_bg']};
                border-radius: 6px;
                padding: 3px 6px;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {c['btn_hover']};
            }}
            QSlider::groove:horizontal {{
                height: 5px;
                background: {c['card_border']};
                border-radius: 2.5px;
            }}
            QSlider::sub-page:horizontal {{
                background: {c['accent_blue']};
                border-radius: 2.5px;
            }}
            QSlider::handle:horizontal {{
                background: {c['accent_blue']};
                width: 14px;
                height: 14px;
                margin-top: -4.5px;
                margin-bottom: -4.5px;
                border-radius: 7px;
            }}
        """)

    def update_from_browser(self):
        try:
            active = self.parent_menu.parent_window.browser_stack.currentWidget()
            if hasattr(active, "zoomFactor"):
                zoom = active.zoomFactor()
                percent = int(round(zoom * 100))
                self.val_badge.setText(f"{percent}%")
                self.slider.blockSignals(True)
                self.slider.setValue(percent)
                self.slider.blockSignals(False)
        except Exception:
            pass

    def on_slider_change(self, value):
        active = self.parent_menu.parent_window.browser_stack.currentWidget()
        if hasattr(active, "setZoomFactor"):
            active.setZoomFactor(value / 100.0)
            self.val_badge.setText(f"{value}%")
            if hasattr(self.parent_menu.parent_window, "show_zoom_overlay"):
                self.parent_menu.parent_window.show_zoom_overlay(value / 100.0)

    def zoom_out(self):
        val = max(25, self.slider.value() - 10)
        self.slider.setValue(val)

    def zoom_in(self):
        val = min(300, self.slider.value() + 10)
        self.slider.setValue(val)

    def zoom_reset(self):
        self.slider.setValue(100)


class BrowserMenu(QFrame):
    def __init__(self, parent_window, trigger_button):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.trigger_button = trigger_button
        
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("browserDropdownMenu")
        self.setFixedWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 14) # Extra bottom margin to ensure full 16px corner visibility
        layout.setSpacing(3)
        
        # --- Section 1: Primary Actions ---
        self.new_tab_btn = self._add_menu_item(
            icon_path="assets/tab_new.svg",
            name="New Tab",
            shortcut="Ctrl+T",
            callback=self._trigger_new_tab,
            action_type="primary"
        )
        self.new_win_btn = self._add_menu_item(
            icon_path="assets/window_new.svg",
            name="New Window",
            shortcut="Ctrl+N",
            callback=self._trigger_new_window,
            action_type="primary"
        )
        self.incognito_btn = self._add_menu_item(
            icon_path="assets/incognito.svg",
            name="New Incognito Window",
            shortcut="Ctrl+Shift+N",
            callback=self._trigger_incognito_window,
            action_type="primary"
        )

        layout.addWidget(self._make_divider())

        # --- Section 2: Navigation & Internal Pages ---
        self.star_tab_btn = self._add_menu_item(
            icon_path="assets/star.svg",
            name="Bookmark this Tab",
            shortcut="Ctrl+D",
            callback=self._trigger_bookmark_tab,
            action_type="nav"
        )
        self.bookmarks_btn = self._add_menu_item(
            icon_path="assets/bookmark.svg",
            name="Bookmarks Manager",
            shortcut="Ctrl+Shift+O",
            callback=self._trigger_bookmarks,
            action_type="nav"
        )
        self.history_btn = self._add_menu_item(
            icon_path="assets/history.svg",
            name="Browsing History",
            shortcut="Ctrl+H",
            callback=self._trigger_history,
            action_type="nav"
        )
        self.downloads_btn = self._add_menu_item(
            icon_path="assets/download.svg",
            name="Downloads",
            shortcut="Ctrl+J",
            callback=self._trigger_downloads,
            action_type="nav"
        )
        
        layout.addWidget(self._make_divider())
        
        # --- Section 3: Page Utilities ---
        self.print_btn = self._add_menu_item(
            icon_path="assets/print.svg",
            name="Print Page",
            shortcut="Ctrl+P",
            callback=self._trigger_print,
            action_type="utility"
        )
        self.find_btn = self._add_menu_item(
            icon_path="assets/find.svg",
            name="Find in Page",
            shortcut="Ctrl+F",
            callback=self._trigger_find,
            action_type="utility"
        )
        self.screenshot_btn = self._add_menu_item(
            icon_path="assets/camera.svg",
            name="Take Web Screenshot",
            shortcut="Ctrl+Shift+S",
            callback=self._trigger_screenshot,
            action_type="utility"
        )
        self.reader_btn = self._add_menu_item(
            icon_path="assets/reader.svg",
            name="Distraction-Free Reader",
            shortcut="Ctrl+Alt+R",
            callback=self._trigger_reader_mode,
            action_type="utility"
        )

        layout.addWidget(self._make_divider())

        # --- Section 4: Zoom Bar ---
        self.zoom_widget = ZoomControlWidget(self)
        layout.addWidget(self.zoom_widget)

        layout.addWidget(self._make_divider())

        # --- Section 5: Preferences & System ---
        self.theme_btn = self._add_menu_item(
            icon_path="assets/moon.svg" if not ThemeManager.instance().is_dark() else "assets/sun.svg",
            name="Dark Mode" if not ThemeManager.instance().is_dark() else "Light Mode",
            shortcut="Ctrl+Shift+L",
            callback=self._trigger_theme_toggle,
            action_type="utility"
        )
        self.settings_btn = self._add_menu_item(
            icon_path="assets/settings.svg",
            name="Settings",
            shortcut="Ctrl+,",
            callback=self._trigger_settings,
            action_type="nav"
        )
        self.about_btn = self._add_menu_item(
            icon_path="assets/info.svg",
            name="About Tron Browser",
            shortcut="",
            callback=self._trigger_about,
            action_type="nav"
        )

        layout.addWidget(self._make_divider())

        # --- Section 6: Exit Action ---
        self.exit_btn = self._add_menu_item(
            icon_path="assets/close.svg",
            name="Exit Browser",
            shortcut="Alt+F4",
            callback=self._trigger_exit,
            action_type="danger"
        )
        
        ThemeManager.instance().theme_changed.connect(self.update_theme_styles)
        self.update_theme_styles()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = ThemeManager.instance().colors()

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 16.0, 16.0)

        p.fillPath(path, parse_color(c["menu_bg"]))
        p.setPen(QPen(parse_color(c["menu_border"]), 1.2))
        p.drawPath(path)
        p.end()

    def update_theme_styles(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        ic = c["icon_stroke"]
        
        hover_styles = {
            "primary": {
                "light_hover": "rgba(37, 99, 235, 0.1)",
                "dark_hover": "rgba(137, 180, 250, 0.18)",
                "light_text": "#1d4ed8",
                "dark_text": "#89b4fa",
            },
            "nav": {
                "light_hover": "rgba(124, 58, 237, 0.08)",
                "dark_hover": "rgba(196, 167, 231, 0.16)",
                "light_text": "#6d28d9",
                "dark_text": "#c4a7e7",
            },
            "utility": {
                "light_hover": "rgba(15, 23, 42, 0.06)",
                "dark_hover": "rgba(255, 255, 255, 0.1)",
                "light_text": c["menu_text"],
                "dark_text": c["menu_text"],
            },
            "danger": {
                "light_hover": "rgba(239, 68, 68, 0.12)",
                "dark_hover": "rgba(243, 139, 168, 0.2)",
                "light_text": "#dc2626",
                "dark_text": "#f38ba8",
            }
        }

        menu_items = [
            (self.new_tab_btn, "assets/tab_new.svg", "primary"),
            (self.new_win_btn, "assets/window_new.svg", "primary"),
            (self.incognito_btn, "assets/incognito.svg", "primary"),
            (self.star_tab_btn, "assets/star.svg", "nav"),
            (self.bookmarks_btn, "assets/bookmark.svg", "nav"),
            (self.history_btn, "assets/history.svg", "nav"),
            (self.downloads_btn, "assets/download.svg", "nav"),
            (self.print_btn, "assets/print.svg", "utility"),
            (self.find_btn, "assets/find.svg", "utility"),
            (self.screenshot_btn, "assets/camera.svg", "utility"),
            (self.reader_btn, "assets/reader.svg", "utility"),
            (self.theme_btn, "assets/moon.svg" if not is_dark else "assets/sun.svg", "utility"),
            (self.settings_btn, "assets/settings.svg", "nav"),
            (self.about_btn, "assets/info.svg", "nav"),
            (self.exit_btn, "assets/close.svg", "danger"),
        ]

        for btn, icon_path, atype in menu_items:
            h_info = hover_styles.get(atype, hover_styles["utility"])
            hover_bg = h_info["dark_hover"] if is_dark else h_info["light_hover"]
            active_text = h_info["dark_text"] if is_dark else h_info["light_text"]
            icon_color = "#f38ba8" if atype == "danger" and is_dark else ("#dc2626" if atype == "danger" else ic)

            btn_layout = btn.layout()
            if btn_layout and btn_layout.count() >= 2:
                icon_lbl = btn_layout.itemAt(0).widget()
                text_lbl = btn_layout.itemAt(1).widget()
                if isinstance(icon_lbl, QLabel):
                    icon_lbl.setPixmap(get_tinted_icon(icon_path, icon_color, QSize(20, 20)).pixmap(QSize(20, 20)))
                if isinstance(text_lbl, QLabel):
                    if btn == self.theme_btn:
                        text_lbl.setText("Dark Mode" if not is_dark else "Light Mode")
                    text_lbl.setStyleSheet(f"font-family: 'Segoe UI', Roboto, sans-serif; font-size: 14px; font-weight: 500; color: {c['menu_text']};")

                if btn_layout.count() >= 3:
                    kbd_lbl = btn_layout.itemAt(2).widget()
                    if isinstance(kbd_lbl, QLabel):
                        kbd_lbl.setStyleSheet(f"""
                            font-family: 'Segoe UI', Roboto, sans-serif;
                            font-size: 11px;
                            font-weight: 600;
                            color: {c['text_secondary']};
                            background: {c['btn_bg']};
                            border: 1px solid {c['card_border']};
                            border-radius: 5px;
                            padding: 3px 7px;
                        """)
                    
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 12px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {hover_bg};
                }}
                QPushButton:hover QLabel {{
                    color: {active_text};
                }}
                QPushButton:pressed {{
                    background: {c['btn_bg']};
                }}
            """)

    def show_menu(self):
        self.adjustSize()
        gp = self.trigger_button.mapToGlobal(QPoint(0, 0))
        x = gp.x() + self.trigger_button.width() - self.width()
        y = gp.y() + self.trigger_button.height() + 4

        screen_geo = QApplication.primaryScreen().availableGeometry()
        if y + self.height() > screen_geo.bottom():
            y = screen_geo.bottom() - self.height() - 6

        self.move(x, y)
        
        # Dynamic Bookmark status update
        current_browser = self.parent_window.browser_stack.currentWidget()
        is_bm = False
        if hasattr(current_browser, "url"):
            url = current_browser.url().toString()
            from bookmarks_manager import BookmarkManager
            is_bm = BookmarkManager.instance().is_bookmarked(url)

        btn_layout = self.star_tab_btn.layout()
        if btn_layout and btn_layout.count() >= 2:
            icon_lbl = btn_layout.itemAt(0).widget()
            text_lbl = btn_layout.itemAt(1).widget()
            c = ThemeManager.instance().colors()
            ic = c["icon_stroke"]
            if is_bm:
                if isinstance(text_lbl, QLabel):
                    text_lbl.setText("Remove Bookmark")
                if isinstance(icon_lbl, QLabel):
                    icon_lbl.setPixmap(get_tinted_icon("assets/star.svg", "#f59e0b", QSize(20, 20)).pixmap(QSize(20, 20)))
            else:
                if isinstance(text_lbl, QLabel):
                    text_lbl.setText("Bookmark this Tab")
                if isinstance(icon_lbl, QLabel):
                    icon_lbl.setPixmap(get_tinted_icon("assets/star.svg", ic, QSize(20, 20)).pixmap(QSize(20, 20)))

        self.zoom_widget.update_from_browser()
        
        # Smooth opening animation: slide down slightly and fade in
        self.setWindowOpacity(0.0)
        self.move(x, y - 8)
        self.show()
        self.raise_()
        self.setFocus(Qt.FocusReason.MouseFocusReason)

        self._pos_anim = QPropertyAnimation(self, b"pos", self)
        self._pos_anim.setDuration(160)
        self._pos_anim.setStartValue(QPoint(x, y - 8))
        self._pos_anim.setEndValue(QPoint(x, y))
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.setDuration(160)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._pos_anim.start()
        self._opacity_anim.start()

    def focusOutEvent(self, event):
        self.hide()
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        event.accept()
        super().mousePressEvent(event)

    def _add_menu_item(self, icon_path, name, shortcut, callback, action_type="utility"):
        btn = QPushButton()
        btn.setProperty("isMenuItem", True)
        btn.setProperty("actionType", action_type)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        
        btn_layout = QHBoxLayout(btn)
        btn_layout.setContentsMargins(10, 6, 10, 6)
        btn_layout.setSpacing(12)
        
        icon = QLabel()
        icon.setFixedSize(20, 20)
        btn_layout.addWidget(icon)
        
        text = QLabel(name)
        c = ThemeManager.instance().colors()
        text.setStyleSheet(f"font-family: 'Segoe UI', Roboto, sans-serif; font-size: 14px; font-weight: 500; color: {c['menu_text']};")
        btn_layout.addWidget(text, 1)
        
        if shortcut:
            shortcut_lbl = QLabel(shortcut)
            btn_layout.addWidget(shortcut_lbl)
            
        self.layout().addWidget(btn)
        return btn

    def _make_divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        c = ThemeManager.instance().colors()
        line.setStyleSheet(f"background-color: {c['menu_border']}; height: 1px; border: none; margin: 4px 6px;")
        return line

    # --- Actions ---
    def _trigger_new_tab(self):
        self.hide()
        self.parent_window.add_new_tab()

    def _trigger_new_window(self):
        self.hide()
        from browser_window import TronWindow
        new_win = TronWindow()
        new_win.show()

    def _trigger_incognito_window(self):
        self.hide()
        from browser_window import TronWindow
        incog_win = TronWindow(is_incognito=True)
        incog_win.show()

    def _trigger_bookmark_tab(self):
        self.hide()
        if hasattr(self.parent_window, "toggle_bookmark_current_page"):
            self.parent_window.toggle_bookmark_current_page()

    def _trigger_bookmarks(self):
        self.hide()
        self.parent_window.open_bookmarks_page()

    def _trigger_history(self):
        self.hide()
        self.parent_window.open_history_page()

    def _trigger_downloads(self):
        self.hide()
        self.parent_window.open_downloads_page()

    def _trigger_print(self):
        self.hide()
        if hasattr(self.parent_window, "print_page"):
            self.parent_window.print_page()

    def _trigger_find(self):
        self.hide()
        if hasattr(self.parent_window, "show_find_bar"):
            self.parent_window.show_find_bar()

    def _trigger_screenshot(self):
        self.hide()
        if hasattr(self.parent_window, "capture_screenshot"):
            self.parent_window.capture_screenshot()


    def _trigger_reader_mode(self):
        self.hide()
        self.parent_window.toggle_reader_mode()

    def _trigger_theme_toggle(self):
        self.hide()
        ThemeManager.instance().toggle_theme()

    def _trigger_settings(self):
        self.hide()
        self.parent_window.open_settings_page()

    def _trigger_about(self):
        self.hide()
        self.parent_window.open_about_page()

    def _trigger_exit(self):
        self.hide()
        self.parent_window.close()
