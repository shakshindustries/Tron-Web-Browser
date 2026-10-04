import sys
import platform
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout
)
import os
from theme_manager import ThemeManager, get_tinted_icon, resolve_resource

class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aboutPage")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setObjectName("aboutScroll")
        
        content = QWidget()
        content.setObjectName("aboutContent")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(32, 32, 32, 40)
        c_layout.setSpacing(28)
        
        # Center container constraint (max width feel)
        center_wrapper = QWidget()
        cw_layout = QVBoxLayout(center_wrapper)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setSpacing(28)
        
        # ==========================================
        # 1. HERO SECTION (Bigger Logo & Immersive Header)
        # ==========================================
        self.hero_card = QFrame()
        self.hero_card.setObjectName("heroCard")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(36, 40, 36, 40)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.setSpacing(16)
        
        # Logo Ring Wrapper
        logo_ring = QFrame()
        logo_ring.setObjectName("logoRing")
        logo_ring.setFixedSize(148, 148)
        lr_layout = QVBoxLayout(logo_ring)
        lr_layout.setContentsMargins(0, 0, 0, 0)
        lr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_lbl = QLabel()
        app_logo_path = resolve_resource("assets/app_icon.png")
        if not os.path.exists(app_logo_path):
            app_logo_path = resolve_resource("assets/app_icon.svg")
        self.icon_lbl.setPixmap(QIcon(app_logo_path).pixmap(QSize(128, 128)))
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lr_layout.addWidget(self.icon_lbl)
        hero_layout.addWidget(logo_ring, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.title_lbl = QLabel("TRON BROWSER")
        self.title_lbl.setObjectName("heroTitle")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self.title_lbl)
        
        self.sub_lbl = QLabel("Next-Generation Web Browsing Powered by PyQt6 & Chromium Core")
        self.sub_lbl.setObjectName("heroSub")
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self.sub_lbl)
        
        # Badges Row
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(10)
        badges_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        badges = [
            "v2.5.0 Stable",
            "Qt6 WebEngine",
            "Chromium Core",
            "64-Bit Architecture",
            "Python 3 Engine"
        ]
        
        for badge_text in badges:
            badge = QLabel(badge_text)
            badge.setObjectName("heroBadge")
            badges_layout.addWidget(badge)
            
        hero_layout.addLayout(badges_layout)
        cw_layout.addWidget(self.hero_card)
        
        # ==========================================
        # 2. FEATURE MATRIX SHOWCASE (6 Interactive Cards)
        # ==========================================
        self.feature_sec_header = self._create_section_header("Core Features & Engine Capabilities", "assets/info.svg")
        cw_layout.addWidget(self.feature_sec_header)
        
        features_grid_widget = QWidget()
        f_grid = QGridLayout(features_grid_widget)
        f_grid.setContentsMargins(0, 0, 0, 0)
        f_grid.setSpacing(16)
        
        features_data = [
            ("assets/globe.svg", "Chromium Web Engine", 
             "Powered by Qt6 WebEngine (Chromium). Delivers full HTML5, WebGL 2.0, WebAssembly, and V8 JS execution with ultra-fast page rendering."),
            ("assets/info.svg", "Native tron:// Protocol", 
             "Custom scheme handler routing native pages (tron://newtab, bookmarks, history, downloads, settings, about) with zero latency."),
            ("assets/window_new.svg", "Multi-Tab Architecture", 
             "Dynamic tab management with drag-and-drop reordering, audio/mute status indicators, Picture-in-Picture mode, and quick tab restoration."),
            ("assets/download.svg", "Concurrent Download Manager", 
             "Multi-threaded downloads with real-time transfer rate calculation, pause/resume controls, categorised sorting, and toast notifications."),
            ("assets/shield.svg", "Privacy & Shield Protection", 
             "Built-in ad-blocking filters, forced HTTPS options, private Incognito browsing mode, and isolated local storage persistence."),
            ("assets/sun.svg", "Dynamic Theme System", 
             "Instant Light & Dark mode switching with customizable accent color palettes (Tron Blue, Cyber Blue, Emerald Green, Purple, Rose).")
        ]
        
        self.feature_card_widgets = []
        for index, (icon_path, title, desc) in enumerate(features_data):
            row = index // 2
            col = index % 2
            card = QFrame()
            card.setObjectName("featureCard")
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(20, 20, 20, 20)
            c_lay.setSpacing(10)
            
            top_h = QHBoxLayout()
            top_h.setSpacing(12)
            
            icon_l = QLabel()
            icon_l.setFixedSize(28, 28)
            top_h.addWidget(icon_l)
            
            f_title = QLabel(title)
            f_title.setObjectName("featureTitle")
            top_h.addWidget(f_title, 1)
            
            c_lay.addLayout(top_h)
            
            f_desc = QLabel(desc)
            f_desc.setObjectName("featureDesc")
            f_desc.setWordWrap(True)
            c_lay.addWidget(f_desc)
            
            f_grid.addWidget(card, row, col)
            self.feature_card_widgets.append((card, icon_l, icon_path))
            
        cw_layout.addWidget(features_grid_widget)
        
        # ==========================================
        # 3. HOW TRON BROWSER WORKS (Architecture Workflow)
        # ==========================================
        self.arch_sec_header = self._create_section_header("How Tron Browser Works", "assets/cpu.svg")
        cw_layout.addWidget(self.arch_sec_header)
        
        arch_card = QFrame()
        arch_card.setObjectName("archCard")
        arch_layout = QVBoxLayout(arch_card)
        arch_layout.setContentsMargins(24, 24, 24, 24)
        arch_layout.setSpacing(16)
        
        workflow_steps = [
            ("1. Request & Protocol Routing", 
             "When a URL or search term is entered into the omnibar, Tron's internal URI scheme parser intercepts the request. It routes web traffic over http/https and native pages (tron://) to their respective views."),
            ("2. Multi-Process Rendering Pipeline", 
             "Web pages run isolated inside Qt WebEngine renderer processes, insulating the main browser GUI process from web page crashes while ensuring maximum security and sandbox isolation."),
            ("3. Local Persistence & State Sync", 
             "User data, history logs, bookmarks, and configuration settings are saved locally using SQLite and JSON data stores. State updates propagate instantly across all open tabs."),
            ("4. Reactive UI & Theme Layer", 
             "The user interface (Title Bar, Tab Bar, Toast Overlays) updates dynamically using ThemeManager's event bus, allowing seamless live color theme transitions without browser restarts.")
        ]
        
        for step_title, step_desc in workflow_steps:
            step_box = QFrame()
            step_box.setObjectName("stepBox")
            sb_layout = QVBoxLayout(step_box)
            sb_layout.setContentsMargins(16, 14, 16, 14)
            sb_layout.setSpacing(6)
            
            st_lbl = QLabel(step_title)
            st_lbl.setObjectName("stepTitle")
            sb_layout.addWidget(st_lbl)
            
            sd_lbl = QLabel(step_desc)
            sd_lbl.setObjectName("stepDesc")
            sd_lbl.setWordWrap(True)
            sb_layout.addWidget(sd_lbl)
            
            arch_layout.addWidget(step_box)
            
        cw_layout.addWidget(arch_card)
        
        # ==========================================
        # 4. SYSTEM ENVIRONMENT INFO PANEL
        # ==========================================
        self.sys_sec_header = self._create_section_header("System & Runtime Environment", "assets/settings.svg")
        cw_layout.addWidget(self.sys_sec_header)
        
        sys_card = QFrame()
        sys_card.setObjectName("settingCard")
        sys_layout = QGridLayout(sys_card)
        sys_layout.setContentsMargins(24, 20, 24, 20)
        sys_layout.setHorizontalSpacing(24)
        sys_layout.setVerticalSpacing(14)
        
        try:
            accent_name = SettingsManager.instance().get("accent_color", "Tron Blue (Default)")
        except Exception:
            accent_name = "Tron Blue (Default)"
            
        sys_info = [
            ("Browser Version", "Tron Browser v2.5.0 (Build 2026.1)"),
            ("GUI Framework", "PyQt6 (Qt 6.x)"),
            ("Rendering Engine", "QtWebEngine / Chromium Core"),
            ("Python Runtime", f"Python {sys.version.split()[0]} ({platform.architecture()[0]})"),
            ("Operating System", f"{platform.system()} {platform.release()} ({platform.machine()})"),
            ("Active Theme Accent", f"{accent_name}")
        ]
        
        for idx, (label_name, val_name) in enumerate(sys_info):
            r = idx // 2
            c_offset = (idx % 2) * 2
            
            lbl = QLabel(label_name)
            lbl.setObjectName("sysLabel")
            val = QLabel(val_name)
            val.setObjectName("sysVal")
            
            sys_layout.addWidget(lbl, r, c_offset)
            sys_layout.addWidget(val, r, c_offset + 1)
            
        cw_layout.addWidget(sys_card)
        
        # ==========================================
        # 5. KEYBOARD SHORTCUTS TABLE
        # ==========================================
        self.sc_sec_header = self._create_section_header("Keyboard Shortcuts", "assets/find.svg")
        cw_layout.addWidget(self.sc_sec_header)
        
        shortcuts_card = QFrame()
        shortcuts_card.setObjectName("settingCard")
        sc_layout = QVBoxLayout(shortcuts_card)
        sc_layout.setContentsMargins(20, 20, 20, 20)
        sc_layout.setSpacing(12)
        
        shortcuts_data = [
            ("Ctrl + T", "Open New Tab"),
            ("Ctrl + W", "Close Current Tab"),
            ("Ctrl + Tab", "Switch to Next Tab"),
            ("Ctrl + Shift + Tab", "Switch to Previous Tab"),
            ("Ctrl + H", "Open History Manager (tron://history)"),
            ("Ctrl + Shift + O", "Open Bookmarks Manager (tron://bookmarks)"),
            ("Ctrl + J", "Open Downloads Page (tron://downloads)"),
            ("Ctrl + ,", "Open Settings Page (tron://settings)"),
            ("Ctrl + Shift + N", "Open New Incognito Window"),
            ("Ctrl + P", "Print Page"),
            ("Ctrl + R / F5", "Reload Current Page"),
            ("Ctrl + Mouse Wheel", "Zoom In / Out Page Content"),
        ]
        
        self.table = QTableWidget(len(shortcuts_data), 2)
        self.table.setHorizontalHeaderLabels(["Shortcut Key", "Action Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 220)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFixedHeight(340)
        
        for i, (key, desc) in enumerate(shortcuts_data):
            key_item = QTableWidgetItem(key)
            desc_item = QTableWidgetItem(desc)
            self.table.setItem(i, 0, key_item)
            self.table.setItem(i, 1, desc_item)
            
        sc_layout.addWidget(self.table)
        cw_layout.addWidget(shortcuts_card)
        
        c_layout.addWidget(center_wrapper)
        c_layout.addStretch(1)
        
        self.scroll.setWidget(content)
        main_layout.addWidget(self.scroll, 1)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def _create_section_header(self, title_text, icon_path):
        header_widget = QWidget()
        h_lay = QHBoxLayout(header_widget)
        h_lay.setContentsMargins(4, 8, 4, 4)
        h_lay.setSpacing(10)
        
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(24, 24)
        h_lay.addWidget(icon_lbl)
        
        title_lbl = QLabel(title_text)
        title_lbl.setObjectName("sectionHeaderTitle")
        h_lay.addWidget(title_lbl, 1)
        
        header_widget.icon_lbl = icon_lbl
        header_widget.icon_path = icon_path
        return header_widget

    def update_styles(self):
        c = ThemeManager.instance().colors()
        accent = c.get('accent_blue', '#2563eb')
        accent_glow = c.get('accent_glow', 'rgba(37, 99, 235, 0.2)')
        
        # Tint section icons
        for sec in [self.feature_sec_header, self.arch_sec_header, self.sys_sec_header, self.sc_sec_header]:
            sec.icon_lbl.setPixmap(get_tinted_icon(sec.icon_path, accent, QSize(22, 22)).pixmap(QSize(22, 22)))
            
        # Tint feature card icons
        for card, icon_lbl, icon_path in self.feature_card_widgets:
            icon_lbl.setPixmap(get_tinted_icon(icon_path, accent, QSize(24, 24)).pixmap(QSize(24, 24)))
            
        self.setStyleSheet(f"""
            #aboutPage {{
                background-color: {c['page_bg']};
            }}
            #aboutContent {{
                background-color: {c['page_bg']};
            }}
            
            /* Custom Sleek Scrollbar */
            QScrollArea#aboutScroll {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['card_border']};
                min-height: 36px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QLabel {{
                background: transparent;
                border: none;
            }}

            /* Hero Card & Logo Ring */
            #heroCard {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 20px;
            }}
            #logoRing {{
                background: {accent_glow};
                border: 2px solid {accent};
                border-radius: 74px;
            }}
            QLabel#heroTitle {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 30px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            QLabel#heroSub {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 14px;
                font-weight: 500;
            }}
            QLabel#heroBadge {{
                background-color: {c['pill_bg']};
                color: {accent};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
                padding: 5px 12px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 12px;
                font-weight: 600;
            }}

            /* Section Headers */
            QLabel#sectionHeaderTitle {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 18px;
                font-weight: 700;
            }}

            /* Feature Cards */
            #featureCard {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 16px;
            }}
            #featureCard:hover {{
                border: 1px solid {accent};
            }}
            QLabel#featureTitle {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 15px;
                font-weight: 700;
            }}
            QLabel#featureDesc {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                line-height: 1.4;
            }}

            /* Architecture Cards */
            #archCard {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 16px;
            }}
            #stepBox {{
                background-color: {c['pill_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 10px;
            }}
            QLabel#stepTitle {{
                color: {accent};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 14px;
                font-weight: 700;
            }}
            QLabel#stepDesc {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
            }}

            /* System & Settings Cards */
            #settingCard {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 16px;
            }}
            QLabel#sysLabel {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#sysVal {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                font-weight: 500;
            }}

            /* Shortcuts Table */
            QTableWidget {{
                background: transparent;
                gridline-color: transparent;
                border: none;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
                color: {c['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {c['btn_bg']};
                color: {c['text_secondary']};
                border: none;
                padding: 8px 12px;
                font-weight: 700;
            }}
            QTableWidget::item {{
                padding: 6px 12px;
                border-bottom: 1px solid {c['card_border']};
            }}
        """)
