import os
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtSignal, pyqtProperty, QPoint, QRectF, QStandardPaths
from PyQt6.QtGui import QIcon, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QScrollArea, QFrame, QLineEdit, QStackedWidget,
    QSizePolicy, QFileDialog
)
from theme_manager import ThemeManager, parse_color, get_tinted_icon
from settings_manager import SettingsManager
from history_manager import HistoryManager
from bookmarks_manager import BookmarkManager

class TronSwitch(QWidget):
    """Modern iOS/macOS animated toggle switch."""
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._handle_x = 22.0 if checked else 2.0

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self._animate_handle()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def _animate_handle(self):
        target_x = 22.0 if self._checked else 2.0
        self.anim = QPropertyAnimation(self, b"handle_x")
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self._handle_x)
        self.anim.setEndValue(target_x)
        self.anim.start()

    def get_handle_x(self):
        return self._handle_x

    def set_handle_x(self, x):
        self._handle_x = float(x)
        self.update()

    handle_x = pyqtProperty(float, get_handle_x, set_handle_x)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(rect, 12.0, 12.0)

        if self._checked:
            track_bg = parse_color(c["accent_blue"])
        else:
            track_bg = parse_color("rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.12)")

        p.fillPath(path, track_bg)

        handle_r = 9.0
        handle_y = rect.center().y()
        hx = getattr(self, "_handle_x", 22.0 if self._checked else 2.0) + handle_r + 1.0

        p.setBrush(QColor("#ffffff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(int(hx), int(handle_y)), int(handle_r), int(handle_r))
        p.end()


class SelectableCardOption(QFrame):
    """Interactive visual card for selecting themes, search engines, and startup options."""
    clicked = pyqtSignal()

    def __init__(self, value_key, icon_path, title, description, selected=False, parent=None):
        super().__init__(parent)
        self.value_key = value_key
        self.icon_path = icon_path
        self._selected = selected
        self.setObjectName("optionCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)

        if icon_path:
            self.icon_lbl = QLabel()
            self.icon_lbl.setFixedSize(24, 24)
            layout.addWidget(self.icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("cardTitle")

        self.desc_lbl = QLabel(description)
        self.desc_lbl.setObjectName("cardDesc")

        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.desc_lbl)
        layout.addLayout(text_layout, 1)

        self.badge_lbl = QLabel()
        self.badge_lbl.setFixedSize(18, 18)
        layout.addWidget(self.badge_lbl)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def isSelected(self):
        return self._selected

    def setSelected(self, sel):
        self._selected = sel
        self.update_styles()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        accent = c["accent_blue"]

        if hasattr(self, "icon_lbl") and self.icon_path:
            icon_color = accent if self._selected else ic
            self.icon_lbl.setPixmap(get_tinted_icon(self.icon_path, icon_color, QSize(24, 24)).pixmap(QSize(24, 24)))

        if self._selected:
            self.badge_lbl.setPixmap(get_tinted_icon("assets/star.svg", accent, QSize(16, 16)).pixmap(QSize(16, 16)))
            self.setStyleSheet(f"""
                #optionCard {{
                    background-color: {c['btn_bg']};
                    border: 2px solid {accent};
                    border-radius: 12px;
                }}
                QLabel {{
                    background: transparent;
                    border: none;
                }}
                QLabel#cardTitle {{
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 14px;
                    font-weight: 700;
                    color: {accent};
                    background: transparent;
                }}
                QLabel#cardDesc {{
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 12px;
                    color: {c['text_secondary']};
                    background: transparent;
                }}
            """)
        else:
            self.badge_lbl.setPixmap(QIcon().pixmap(0, 0))
            self.setStyleSheet(f"""
                #optionCard {{
                    background-color: {c['card_bg']};
                    border: 1px solid {c['card_border']};
                    border-radius: 12px;
                }}
                #optionCard:hover {{
                    border: 1px solid {c['address_border']};
                    background-color: {c['btn_bg']};
                }}
                QLabel {{
                    background: transparent;
                    border: none;
                }}
                QLabel#cardTitle {{
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 14px;
                    font-weight: 600;
                    color: {c['text_primary']};
                    background: transparent;
                }}
                QLabel#cardDesc {{
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 12px;
                    color: {c['text_secondary']};
                    background: transparent;
                }}
            """)


class SettingRowWidget(QFrame):
    """Container row with icon, title, description, and control widget."""
    def __init__(self, icon_path, title, description, control_widget=None, parent=None):
        super().__init__(parent)
        self.setObjectName("settingRow")
        self.icon_path = icon_path

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        if icon_path:
            self.icon_lbl = QLabel()
            self.icon_lbl.setFixedSize(22, 22)
            layout.addWidget(self.icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("rowTitle")

        self.desc_lbl = QLabel(description)
        self.desc_lbl.setObjectName("rowDesc")

        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.desc_lbl)
        layout.addLayout(text_layout, 1)

        if control_widget:
            layout.addWidget(control_widget)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]

        if hasattr(self, "icon_lbl") and self.icon_path:
            self.icon_lbl.setPixmap(get_tinted_icon(self.icon_path, c["accent_blue"], QSize(22, 22)).pixmap(QSize(22, 22)))

        self.setStyleSheet(f"""
            #settingRow {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
            }}
            #settingRow:hover {{
                border: 1px solid {c['address_border']};
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QLabel#rowTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {c['text_primary']};
                background: transparent;
            }}
            QLabel#rowDesc {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                color: {c['text_secondary']};
                background: transparent;
            }}
        """)


class SettingsPage(QWidget):
    """Professional Multi-step Preferences Dashboard."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.sm = SettingsManager.instance()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        self.sidebar = QFrame()
        self.sidebar.setObjectName("settingsSidebar")
        self.sidebar.setFixedWidth(220)

        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(14, 24, 14, 24)
        sb_layout.setSpacing(6)

        sb_title = QLabel("Settings")
        sb_title.setObjectName("sidebarHeaderTitle")
        sb_layout.addWidget(sb_title)
        sb_layout.addSpacing(12)

        self.step_btns = []
        steps_data = [
            ("Appearance", "assets/sun.svg", 0),
            ("Search Engine", "assets/search.svg", 1),
            ("Startup Behavior", "assets/home.svg", 2),
            ("Toolbar Icons", "assets/star.svg", 3),
            ("Security & Privacy", "assets/shield.svg", 4),
            ("Downloads", "assets/download.svg", 5),
            ("Performance", "assets/cpu.svg", 6),
            ("Clear Data", "assets/trash.svg", 7),
        ]

        for name, icon_path, index in steps_data:
            btn = QPushButton(f"  {name}")
            btn.setProperty("stepIndex", index)
            btn.setProperty("iconPath", icon_path)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setFixedHeight(40)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda chk, idx=index: self.switch_step(idx))
            sb_layout.addWidget(btn)
            self.step_btns.append(btn)

        self.step_btns[0].setChecked(True)
        sb_layout.addStretch(1)

        main_layout.addWidget(self.sidebar)

        # 2. Right Content Stack inside a ScrollArea
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")

        # Add steps
        self.content_stack.addWidget(self._build_appearance_step())
        self.content_stack.addWidget(self._build_search_step())
        self.content_stack.addWidget(self._build_startup_step())
        self.content_stack.addWidget(self._build_toolbar_step())
        self.content_stack.addWidget(self._build_security_step())
        self.content_stack.addWidget(self._build_downloads_step())
        self.content_stack.addWidget(self._build_performance_step())
        self.content_stack.addWidget(self._build_clear_data_step())

        scroll.setWidget(self.content_stack)
        main_layout.addWidget(scroll, 1)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def switch_step(self, index):
        self.content_stack.setCurrentIndex(index)
        for btn in self.step_btns:
            btn.setChecked(btn.property("stepIndex") == index)

    # --- Step 0: Appearance ---
    def _build_appearance_step(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("Appearance & Themes")
        title.setObjectName("stepPageTitle")
        layout.addWidget(title)

        sub = QLabel("Customize the visual theme and look of Tron Browser")
        sub.setObjectName("stepSubTitle")
        layout.addWidget(sub)

        self.theme_cards = []
        is_dark = ThemeManager.instance().is_dark()

        card_light = SelectableCardOption(
            value_key="light",
            icon_path="assets/sun.svg",
            title="Light Mode",
            description="Crisp slate background with dark charcoal icons and high contrast",
            selected=not is_dark
        )
        card_light.clicked.connect(lambda: self._select_theme("light"))
        layout.addWidget(card_light)
        self.theme_cards.append(card_light)

        card_dark = SelectableCardOption(
            value_key="dark",
            icon_path="assets/moon.svg",
            title="Dark Mode",
            description="Sleek dark violet background with bright slate icons for night browsing",
            selected=is_dark
        )
        card_dark.clicked.connect(lambda: self._select_theme("dark"))
        layout.addWidget(card_dark)
        self.theme_cards.append(card_dark)

        layout.addStretch(1)
        return w

    def _select_theme(self, theme_key):
        ThemeManager.instance().set_theme(theme_key)
        for card in self.theme_cards:
            card.setSelected(card.value_key == theme_key)

    # --- Step 1: Search Engine ---
    def _build_search_step(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Search Engine & Omnibar")
        title.setObjectName("stepPageTitle")
        layout.addWidget(title)

        sub = QLabel("Select your preferred search engine for address bar queries")
        sub.setObjectName("stepSubTitle")
        layout.addWidget(sub)

        current_engine = self.sm.get("search_engine", "Google")
        self.engine_cards = []

        engines_info = [
            ("Google", "assets/search.svg", "Google Search", "World's primary web search engine with rich suggestions"),
            ("DuckDuckGo", "assets/shield.svg", "DuckDuckGo", "Privacy-focused search engine that doesn't track user history"),
            ("Bing", "assets/globe.svg", "Microsoft Bing", "Feature-rich search engine powered by Microsoft AI"),
            ("Ecosia", "assets/globe.svg", "Ecosia", "Green search engine that plants trees with search revenues"),
            ("Custom", "assets/settings.svg", "Custom Search Provider", "Use your own custom search engine endpoint URL"),
        ]

        for key, icon, name, desc in engines_info:
            card = SelectableCardOption(
                value_key=key,
                icon_path=icon,
                title=name,
                description=desc,
                selected=(current_engine == key)
            )
            card.clicked.connect(lambda k=key: self._select_search_engine(k))
            layout.addWidget(card)
            self.engine_cards.append(card)

        # Custom Search URL Box
        self.custom_search_card = QFrame()
        self.custom_search_card.setObjectName("sectionCard")
        cs_l = QHBoxLayout(self.custom_search_card)
        cs_l.setContentsMargins(16, 12, 16, 12)

        cs_lbl = QLabel("Custom Search URL")
        cs_lbl.setObjectName("rowTitle")
        self.input_custom_search = QLineEdit()
        self.input_custom_search.setObjectName("settingInput")
        self.input_custom_search.setPlaceholderText("https://example.com/search?q=")
        self.input_custom_search.setText(self.sm.get("custom_search_url", "https://www.google.com/search?q="))
        self.input_custom_search.textChanged.connect(lambda txt: self.sm.set("custom_search_url", txt))

        cs_l.addWidget(cs_lbl)
        cs_l.addSpacing(14)
        cs_l.addWidget(self.input_custom_search, 1)
        layout.addWidget(self.custom_search_card)
        self.custom_search_card.setVisible(current_engine == "Custom")

        # Autocomplete Switch
        self.switch_auto = TronSwitch(checked=self.sm.get("autocomplete_enabled", True))
        self.switch_auto.toggled.connect(lambda chk: self.sm.set("autocomplete_enabled", chk))
        row_auto = SettingRowWidget(
            icon_path="assets/search.svg",
            title="Real-Time Search Suggestions",
            description="Display live Google search completion suggestions while typing in the address bar",
            control_widget=self.switch_auto
        )
        layout.addWidget(row_auto)

        layout.addStretch(1)
        return w

    def _select_search_engine(self, engine_key):
        self.sm.set("search_engine", engine_key)
        for card in self.engine_cards:
            card.setSelected(card.value_key == engine_key)
        self.custom_search_card.setVisible(engine_key == "Custom")

    # --- Step 2: Startup Behavior ---
    def _build_startup_step(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Startup Behavior")
        title.setObjectName("stepPageTitle")
        layout.addWidget(title)

        sub = QLabel("Configure what opens when launching the browser or pressing Home")
        sub.setObjectName("stepSubTitle")
        layout.addWidget(sub)

        current_startup = self.sm.get("startup_behavior", "home")
        self.startup_cards = []

        startup_info = [
            ("home", "assets/home.svg", "Open Home Dashboard", "Loads the default interactive web portal (https://tronexplorer.netlify.app/)"),
            ("blank", "assets/window_new.svg" if os.path.exists("assets/window_new.svg") else "assets/home.svg", "Open Blank Page", "Opens a clean blank page (about:blank) for maximum speed"),
            ("custom", "assets/globe.svg", "Open Specific Page", "Opens a custom user-defined web URL on launch"),
        ]

        for key, icon, name, desc in startup_info:
            card = SelectableCardOption(
                value_key=key,
                icon_path=icon,
                title=name,
                description=desc,
                selected=(current_startup == key)
            )
            card.clicked.connect(lambda k=key: self._select_startup_behavior(k))
            layout.addWidget(card)
            self.startup_cards.append(card)

        # Custom Startup URL Input Box
        self.custom_startup_card = QFrame()
        self.custom_startup_card.setObjectName("sectionCard")
        cs_l = QHBoxLayout(self.custom_startup_card)
        cs_l.setContentsMargins(16, 12, 16, 12)

        cs_lbl = QLabel("Custom Page URL")
        cs_lbl.setObjectName("rowTitle")
        self.input_custom_startup = QLineEdit()
        self.input_custom_startup.setObjectName("settingInput")
        self.input_custom_startup.setPlaceholderText("https://example.com")
        self.input_custom_startup.setText(self.sm.get("custom_startup_url", "https://tronexplorer.netlify.app/"))
        self.input_custom_startup.textChanged.connect(lambda txt: self.sm.set("custom_startup_url", txt))

        cs_l.addWidget(cs_lbl)
        cs_l.addSpacing(14)
        cs_l.addWidget(self.input_custom_startup, 1)
        layout.addWidget(self.custom_startup_card)
        self.custom_startup_card.setVisible(current_startup == "custom")

        layout.addStretch(1)
        return w

    def _select_startup_behavior(self, key):
        self.sm.set("startup_behavior", key)
        for card in self.startup_cards:
            card.setSelected(card.value_key == key)
        self.custom_startup_card.setVisible(key == "custom")

    # --- Step 3: Toolbar Icons ---
    def _build_toolbar_step(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Title Bar Toolbar Buttons")
        title.setObjectName("stepPageTitle")
        layout.addWidget(title)

        sub = QLabel("Customize which action buttons appear in the upper Title Bar")
        sub.setObjectName("stepSubTitle")
        layout.addWidget(sub)

        self.switch_bm = TronSwitch(checked=self.sm.get("show_bookmark_btn", True))
        self.switch_bm.toggled.connect(lambda chk: self.sm.set("show_bookmark_btn", chk))
        row_bm = SettingRowWidget(
            icon_path="assets/bookmark.svg",
            title="Bookmarks Manager Button",
            description="Quick access to Bookmarks Manager (Ctrl+Shift+O)",
            control_widget=self.switch_bm
        )
        layout.addWidget(row_bm)

        self.switch_dl = TronSwitch(checked=self.sm.get("show_download_btn", True))
        self.switch_dl.toggled.connect(lambda chk: self.sm.set("show_download_btn", chk))
        row_dl = SettingRowWidget(
            icon_path="assets/download.svg",
            title="Downloads Progress & History Button",
            description="Display active download speed arc and history popup (Ctrl+J)",
            control_widget=self.switch_dl
        )
        layout.addWidget(row_dl)

        self.switch_home = TronSwitch(checked=self.sm.get("show_home_btn", True))
        self.switch_home.toggled.connect(lambda chk: self.sm.set("show_home_btn", chk))
        row_home = SettingRowWidget(
            icon_path="assets/home.svg",
            title="Home Navigation Button",
            description="Display quick access button to navigate to your home dashboard",
            control_widget=self.switch_home
        )
        layout.addWidget(row_home)

        self.switch_star = TronSwitch(checked=self.sm.get("show_star_btn", True))
        self.switch_star.toggled.connect(lambda chk: self.sm.set("show_star_btn", chk))
        row_star = SettingRowWidget(
            icon_path="assets/star.svg",
            title="Star Bookmark Current Page Button",
            description="One-click star button to bookmark or unbookmark the active web page",
            control_widget=self.switch_star
        )
        layout.addWidget(row_star)

        layout.addStretch(1)
        return w

    # --- Step 4: Security & Privacy Protections ---
    def _build_security_step(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Security & Content Protections")
        title.setObjectName("stepPageTitle")
        layout.addWidget(title)

        sub = QLabel("Configure web security rules, tracking protection, and network privacy")
        sub.setObjectName("stepSubTitle")
        layout.addWidget(sub)

        # Ad & Tracker Blocker
        self.switch_adblock = TronSwitch(checked=self.sm.get("adblock_enabled", True))
        self.switch_adblock.toggled.connect(lambda chk: self.sm.set("adblock_enabled", chk))
        row_ad = SettingRowWidget(
            icon_path="assets/shield.svg",
            title="Ad & Tracker Protection",
            description="Block malicious ad network requests and telemetry scripts",
            control_widget=self.switch_adblock
        )
        layout.addWidget(row_ad)

        # Force HTTPS
        self.switch_https = TronSwitch(checked=self.sm.get("force_https", True))
        self.switch_https.toggled.connect(lambda chk: self.sm.set("force_https", chk))
        row_https = SettingRowWidget(
            icon_path="assets/lock.svg",
            title="Force Secure HTTPS Connections",
            description="Automatically upgrade http:// connection requests to secure https://",
            control_widget=self.switch_https
        )
        layout.addWidget(row_https)

        # Do Not Track Header
        self.switch_dnt = TronSwitch(checked=self.sm.get("dnt_header", True))
        self.switch_dnt.toggled.connect(lambda chk: self.sm.set("dnt_header", chk))
        row_dnt = SettingRowWidget(
            icon_path="assets/globe.svg",
            title="Send 'Do Not Track' (DNT) Header",
            description="Send DNT request header with all outbound HTTP network requests",
            control_widget=self.switch_dnt
        )
        layout.addWidget(row_dnt)

        layout.addStretch(1)
        return w

    # --- Step 5: Downloads Preferences ---
    def _build_downloads_step(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Downloads Preferences")
        title.setObjectName("stepPageTitle")
        layout.addWidget(title)

        sub = QLabel("Manage file download locations and save prompts")
        sub.setObjectName("stepSubTitle")
        layout.addWidget(sub)

        # Download Directory Selector
        dir_controls = QWidget()
        dir_layout = QHBoxLayout(dir_controls)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(8)

        self.btn_dir = QPushButton("Change Folder")
        self.btn_dir.setObjectName("actionBtn")
        self.btn_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dir.clicked.connect(self._change_download_dir)
        dir_layout.addWidget(self.btn_dir)

        self.btn_reset_dir = QPushButton("Reset to Default")
        self.btn_reset_dir.setObjectName("actionBtn")
        self.btn_reset_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_dir.clicked.connect(self._reset_download_dir)
        dir_layout.addWidget(self.btn_reset_dir)

        current_dir = self.sm.get("download_dir", "")
        row_dir = SettingRowWidget(
            icon_path="assets/folder.svg",
            title="Default Download Directory",
            description=f"Save files to: {current_dir}",
            control_widget=dir_controls
        )
        layout.addWidget(row_dir)
        self.row_dir_widget = row_dir

        # Ask Download Location Toggle
        self.switch_ask_dir = TronSwitch(checked=self.sm.get("ask_download_dir", False))
        self.switch_ask_dir.toggled.connect(lambda chk: self.sm.set("ask_download_dir", chk))
        row_ask = SettingRowWidget(
            icon_path="assets/download.svg",
            title="Always Ask Download Location",
            description="Prompt file save dialog before starting each download",
            control_widget=self.switch_ask_dir
        )
        layout.addWidget(row_ask)

        layout.addStretch(1)
        return w

    def _change_download_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.sm.get("download_dir", ""))
        if dir_path:
            self.sm.set("download_dir", dir_path)
            if hasattr(self, "row_dir_widget"):
                self.row_dir_widget.desc_lbl.setText(f"Save files to: {dir_path}")

    def _reset_download_dir(self):
        default_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        self.sm.set("download_dir", default_dir)
        if hasattr(self, "row_dir_widget"):
            self.row_dir_widget.desc_lbl.setText(f"Save files to: {default_dir}")

    # --- Step 6: Performance ---
    def _build_performance_step(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Performance & System")
        title.setObjectName("stepPageTitle")
        layout.addWidget(title)

        sub = QLabel("Configure RAM optimization and hardware acceleration settings")
        sub.setObjectName("stepSubTitle")
        layout.addWidget(sub)

        # Tab Suspension
        self.switch_susp = TronSwitch(checked=self.sm.get("tab_suspension", True))
        self.switch_susp.toggled.connect(lambda chk: self.sm.set("tab_suspension", chk))
        row_susp = SettingRowWidget(
            icon_path="assets/cpu.svg",
            title="Memory Saver (Tab Memory Suspension)",
            description="Automatically free RAM memory from inactive background tabs",
            control_widget=self.switch_susp
        )
        layout.addWidget(row_susp)

        # Tab Sleep Timeout ComboBox
        self.combo_timeout = QComboBox()
        self.combo_timeout.setObjectName("settingCombo")
        self.combo_timeout.addItems(["5 Minutes", "15 Minutes (Default)", "30 Minutes", "60 Minutes"])
        
        current_timeout = self.sm.get("tab_sleep_timeout_minutes", 15)
        timeout_map = {5: 0, 15: 1, 30: 2, 60: 3}
        self.combo_timeout.setCurrentIndex(timeout_map.get(current_timeout, 1))
        
        def on_timeout_changed(idx):
            val_map = [5, 15, 30, 60]
            self.sm.set("tab_sleep_timeout_minutes", val_map[idx])
            
        self.combo_timeout.currentIndexChanged.connect(on_timeout_changed)
        
        row_timeout = SettingRowWidget(
            icon_path="assets/moon.svg",
            title="Tab Sleeping Inactivity Timeout",
            description="Duration of inactivity before background tabs are put to sleep",
            control_widget=self.combo_timeout
        )
        layout.addWidget(row_timeout)

        # Hardware Acceleration
        self.switch_gpu = TronSwitch(checked=self.sm.get("hardware_accel", True))
        self.switch_gpu.toggled.connect(lambda chk: self.sm.set("hardware_accel", chk))
        row_gpu = SettingRowWidget(
            icon_path="assets/cpu.svg",
            title="GPU Hardware Acceleration",
            description="Use graphics card hardware acceleration for smoother WebGL & video playback",
            control_widget=self.switch_gpu
        )
        layout.addWidget(row_gpu)

        layout.addStretch(1)
        return w

    # --- Step 7: Clear Data ---
    def _build_clear_data_step(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("Privacy & Data Actions")
        title.setObjectName("stepPageTitle")
        layout.addWidget(title)

        sub = QLabel("Manage your browsing history, saved bookmarks, and stored data separately")
        sub.setObjectName("stepSubTitle")
        layout.addWidget(sub)

        # Action 1: Clear History Only
        btn_hist = QPushButton("Clear History Only")
        btn_hist.setObjectName("actionBtn")
        btn_hist.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hist.clicked.connect(self.clear_history_only)

        row_hist = SettingRowWidget(
            icon_path="assets/history.svg",
            title="Clear Browsing History",
            description="Delete all recorded page visits and timestamps without affecting bookmarks",
            control_widget=btn_hist
        )
        layout.addWidget(row_hist)

        # Action 2: Clear Bookmarks Only
        btn_bm = QPushButton("Clear Bookmarks Only")
        btn_bm.setObjectName("actionBtn")
        btn_bm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bm.clicked.connect(self.clear_bookmarks_only)

        row_bm = SettingRowWidget(
            icon_path="assets/bookmark.svg",
            title="Clear Saved Bookmarks",
            description="Delete all saved bookmarks and bookmark folders without clearing history",
            control_widget=btn_bm
        )
        layout.addWidget(row_bm)

        # Action 3: Complete Reset
        btn_reset_all = QPushButton("Clear All Data At Once")
        btn_reset_all.setObjectName("dangerBtn")
        btn_reset_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_all.clicked.connect(self.clear_all_data_at_once)

        row_all = SettingRowWidget(
            icon_path="assets/trash.svg",
            title="Complete Reset — Clear All At Once",
            description="Delete browsing history, saved bookmarks, and reset settings to default all at once",
            control_widget=btn_reset_all
        )
        layout.addWidget(row_all)

        layout.addStretch(1)
        return w

    def clear_history_only(self):
        HistoryManager.instance().clear_history()
        main_win = self.window()
        if hasattr(main_win, "show_browser_toast"):
            main_win.show_browser_toast("Browsing history cleared!")

    def clear_bookmarks_only(self):
        BookmarkManager.instance().clear_all()
        main_win = self.window()
        if hasattr(main_win, "show_browser_toast"):
            main_win.show_browser_toast("Saved bookmarks cleared!")

    def clear_all_data_at_once(self):
        HistoryManager.instance().clear_history()
        BookmarkManager.instance().clear_all()
        main_win = self.window()
        if hasattr(main_win, "show_browser_toast"):
            main_win.show_browser_toast("All browsing history and saved bookmarks cleared at once!", is_error=True)

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]

        for btn in self.step_btns:
            icon_path = btn.property("iconPath")
            idx = btn.property("stepIndex")
            is_checked = (idx == self.content_stack.currentIndex())
            icon_color = c["accent_blue"] if is_checked else ic
            btn.setIcon(get_tinted_icon(icon_path, icon_color, QSize(18, 18)))
            btn.setIconSize(QSize(18, 18))

        self.setStyleSheet(f"""
            #settingsPage {{
                background-color: {c['page_bg']};
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            #settingsSidebar {{
                background-color: {c['card_bg']};
                border-right: 1px solid {c['card_border']};
            }}
            QLabel#sidebarHeaderTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 18px;
                font-weight: 700;
                color: {c['text_primary']};
            }}
            QPushButton[stepIndex] {{
                text-align: left;
                padding-left: 14px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {c['text_secondary']};
                background: transparent;
                border: none;
                border-radius: 8px;
            }}
            QPushButton[stepIndex]:hover {{
                background-color: {c['btn_bg']};
                color: {c['text_primary']};
            }}
            QPushButton[stepIndex]:checked {{
                background-color: {c['btn_bg']};
                color: {c['accent_blue']};
                font-weight: 600;
            }}
            QLabel#stepPageTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 22px;
                font-weight: 700;
                color: {c['text_primary']};
            }}
            QLabel#stepSubTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {c['text_secondary']};
            }}
            #sectionCard {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
            }}
            QLabel#rowTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {c['text_primary']};
            }}
            QLineEdit#settingInput {{
                background-color: {c['btn_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 8px;
                padding: 6px 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {c['text_primary']};
            }}
            QLineEdit#settingInput:focus {{
                border: 1px solid {c['accent_blue']};
            }}
            QPushButton#actionBtn {{
                background-color: {c['btn_bg']};
                color: {c['text_primary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 500;
                border-radius: 6px;
                padding: 6px 14px;
                border: 1px solid {c['card_border']};
            }}
            QPushButton#actionBtn:hover {{
                background-color: {c['btn_hover']};
            }}
            QPushButton#dangerBtn {{
                background-color: #ef4444;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
                padding: 6px 14px;
                border: none;
            }}
            QPushButton#dangerBtn:hover {{
                background-color: #dc2626;
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
            QScrollArea#settingsScroll {{
                background: transparent;
                border: none;
            }}
            QScrollArea#settingsScroll QScrollBar:vertical {{
                width: 6px;
                background: transparent;
                margin: 0px 2px 0px 0px;
                border: none;
            }}
            QScrollArea#settingsScroll QScrollBar::handle:vertical {{
                background: rgba(140, 140, 160, 0.4);
                min-height: 30px;
                border-radius: 3px;
            }}
            QScrollArea#settingsScroll QScrollBar::handle:vertical:hover {{
                background: rgba(140, 140, 160, 0.7);
            }}
            QScrollArea#settingsScroll QScrollBar::add-line:vertical,
            QScrollArea#settingsScroll QScrollBar::sub-line:vertical,
            QScrollArea#settingsScroll QScrollBar::add-page:vertical,
            QScrollArea#settingsScroll QScrollBar::sub-page:vertical {{
                background: transparent;
                border: none;
                height: 0px;
            }}
        """)
