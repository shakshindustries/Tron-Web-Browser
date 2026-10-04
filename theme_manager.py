import re
from PyQt6.QtCore import QObject, pyqtSignal, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter

def parse_color(val):
    """Parse any color format (hex, rgba string, QColor) safely into a valid QColor."""
    if isinstance(val, QColor):
        return val
    if not isinstance(val, str):
        return QColor(val)
        
    val = val.strip()
    if val.startswith("rgba"):
        match = re.search(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", val)
        if match:
            r, g, b, a = int(match.group(1)), int(match.group(2)), int(match.group(3)), float(match.group(4))
            return QColor(r, g, b, int(a * 255))
    elif val.startswith("rgb"):
        match = re.search(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", val)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return QColor(r, g, b)
            
    col = QColor(val)
    return col if col.isValid() else QColor(128, 128, 128)


import os
import sys
from PyQt6.QtSvg import QSvgRenderer

def resolve_resource(rel_path):
    """Resolve a relative resource path for both regular execution and PyInstaller bundles."""
    if not rel_path:
        return rel_path
    if os.path.isabs(rel_path) and os.path.exists(rel_path):
        return rel_path

    norm_rel = os.path.normpath(rel_path).lstrip('\\/')

    candidates = [
        norm_rel,
        rel_path,
    ]

    # Frozen executable paths
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.extend([
            os.path.join(exe_dir, norm_rel),
            os.path.join(exe_dir, '_internal', norm_rel),
            os.path.join(exe_dir, 'assets', os.path.basename(norm_rel)),
            os.path.join(exe_dir, '_internal', 'assets', os.path.basename(norm_rel)),
        ])
        if hasattr(sys, '_MEIPASS'):
            candidates.extend([
                os.path.join(sys._MEIPASS, norm_rel),
                os.path.join(sys._MEIPASS, 'assets', os.path.basename(norm_rel)),
            ])

    # Script/source dir
    src_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.extend([
        os.path.join(src_dir, norm_rel),
        os.path.join(src_dir, 'assets', os.path.basename(norm_rel)),
        os.path.join(os.getcwd(), norm_rel),
    ])

    for c in candidates:
        if c and os.path.exists(c):
            return c

    return rel_path


def get_tinted_icon(icon_path, color, size=QSize(20, 20)):
    """Dynamically tint an SVG/PNG icon mask to the specified theme color."""
    real_path = resolve_resource(icon_path)
    pixmap = None

    if os.path.exists(real_path):
        if real_path.lower().endswith(".svg"):
            try:
                renderer = QSvgRenderer(real_path)
                if renderer.isValid():
                    pm = QPixmap(size)
                    pm.fill(Qt.GlobalColor.transparent)
                    p = QPainter(pm)
                    renderer.render(p)
                    p.end()
                    if not pm.isNull():
                        pixmap = pm
            except Exception:
                pass

        if pixmap is None or pixmap.isNull():
            pixmap = QIcon(real_path).pixmap(size)
    else:
        pixmap = QIcon(real_path).pixmap(size)

    if pixmap.isNull():
        return QIcon(real_path)

    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), parse_color(color))
    painter.end()

    return QIcon(tinted)


ACCENT_HEX_MAP = {
    "Tron Blue (Default)": "#1a73e8",
    "Default (Chrome Blue)": "#1a73e8",
    "Cyber Blue": "#2563eb",
    "Ocean Cyan": "#0284c7",
    "Emerald Green": "#059669",
    "Mint Lime": "#10b981",
    "Sunset Rose": "#e11d48",
    "Coral Orange": "#f97316",
    "Vibrant Purple": "#7c3aed",
    "Amber Gold": "#f59e0b",
    "Crimson Red": "#dc2626",
    "Obsidian Slate": "#475569",
}

def hex_to_rgb(hex_str):
    try:
        hex_str = str(hex_str).strip().lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join([c*2 for c in hex_str])
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (26, 115, 232)

def blend_colors(hex1, hex2, weight):
    """Blends hex1 with hex2 by weight (0.0 = hex1, 1.0 = hex2)."""
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    r = int(r1 * (1 - weight) + r2 * weight)
    g = int(g1 * (1 - weight) + g2 * weight)
    b = int(b1 * (1 - weight) + b2 * weight)
    return f"#{r:02x}{g:02x}{b:02x}"


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str) # 'light' or 'dark'

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        try:
            from settings_manager import SettingsManager
            saved_theme = SettingsManager.instance().get("theme", "light")
            self._current_theme = saved_theme if saved_theme in ["light", "dark"] else "light"
        except Exception:
            self._current_theme = "light"

    @property
    def current_theme(self):
        return self._current_theme

    def is_dark(self):
        return self._current_theme == "dark"

    def toggle_theme(self):
        new_theme = "dark" if self._current_theme == "light" else "light"
        self.set_theme(new_theme)

    def set_theme(self, theme_name):
        if theme_name in ["light", "dark"] and theme_name != self._current_theme:
            self._current_theme = theme_name
            try:
                from settings_manager import SettingsManager
                SettingsManager.instance().set("theme", theme_name)
            except Exception:
                pass
            self.theme_changed.emit(self._current_theme)

    def set_accent_color(self, accent_name):
        try:
            from settings_manager import SettingsManager
            SettingsManager.instance().set("accent_color", accent_name)
        except Exception:
            pass
        self.theme_changed.emit(self._current_theme)

    def get_accent_base_hex(self):
        try:
            from settings_manager import SettingsManager
            accent_name = SettingsManager.instance().get("accent_color", "Tron Blue (Default)")
        except Exception:
            accent_name = "Tron Blue (Default)"

        if accent_name in ACCENT_HEX_MAP:
            return ACCENT_HEX_MAP[accent_name]
        if str(accent_name).startswith('#'):
            return str(accent_name)
        return "#1a73e8"

    def get_accent_colors(self):
        base_hex = self.get_accent_base_hex()
        r, g, b = hex_to_rgb(base_hex)
        light_hex = base_hex
        dark_hex = blend_colors(base_hex, "#ffffff", 0.35)
        light_glow = f"rgba({r}, {g}, {b}, 0.2)"
        dark_glow = f"rgba({r}, {g}, {b}, 0.35)"

        if self.is_dark():
            return dark_hex, dark_glow
        return light_hex, light_glow

    # --- Modern Sleek Scrollbar QSS ---
    def scrollbar_style(self):
        is_dark = self.is_dark()
        handle_col = "rgba(255, 255, 255, 0.22)" if is_dark else "rgba(0, 0, 0, 0.22)"
        handle_hover = "rgba(255, 255, 255, 0.38)" if is_dark else "rgba(0, 0, 0, 0.38)"
        return f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 7px;
                margin: 0px 0px 0px 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {handle_col};
                min-height: 28px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 7px;
                margin: 0px 0px 0px 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:horizontal {{
                background: {handle_col};
                min-width: 28px;
                border-radius: 3px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {handle_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

    def colors(self):
        acc_blue, acc_glow = self.get_accent_colors()
        base_hex = self.get_accent_base_hex()

        # Compute dynamic tints from chosen accent color (like Chrome)
        r, g, b = hex_to_rgb(base_hex)
        header_tint = blend_colors("#ffffff", base_hex, 0.20)
        header_tint_end = blend_colors("#ffffff", base_hex, 0.28)
        border_tint = f"rgba({r}, {g}, {b}, 0.25)"
        window_tint = blend_colors("#ffffff", base_hex, 0.08)
        nav_container_light = blend_colors("#ffffff", base_hex, 0.12)
        
        if self.is_dark():
            # Dark mode: titlebar and tabs
            tab_start = blend_colors("#13131e", base_hex, 0.14)
            tab_end = blend_colors("#181826", base_hex, 0.20)
            window_bg = "#1e1e2e"
            nav_container_dark = "#1e1e2e"
            border_col = "rgba(255, 255, 255, 0.09)"

            return {
                # Title & Window Headers
                "title_grad_start": tab_start,
                "title_grad_mid": tab_start,
                "title_grad_end": tab_end,
                "title_border": border_col,
                "window_bg": window_bg,
                "nav_container_bg": nav_container_dark,

                # Tab Bar
                "tab_bar_grad_start": tab_start,
                "tab_bar_grad_end": tab_end,
                "tab_active_bg": nav_container_dark,  # Seamlessly matches toolbar and webengine like Chrome
                "tab_active_text": "#ffffff",
                "tab_inactive_bg": "transparent",      # Clearly distinct from active tab
                "tab_inactive_text": "#94a3b8",
                "tab_hover_bg": "rgba(255, 255, 255, 0.08)",
                "accent_blue": base_hex,
                "accent_glow": f"rgba({r}, {g}, {b}, 0.35)",

                # Address Bar & Omnibar
                "address_bg": "#161622",
                "address_bg_hover": "#1a1a28",
                "address_border": "rgba(255, 255, 255, 0.12)",
                "address_text": "#f8fafc",
                "address_placeholder": "#94a3b8",

                # Menus & Cards
                "menu_bg": "#1e1e2e",
                "menu_border": "rgba(255, 255, 255, 0.12)",
                "menu_text": "#f8fafc",
                "menu_hover": f"rgba({r}, {g}, {b}, 0.18)",
                "page_bg": "#1e1e2e",
                "card_bg": "#24243a",
                "card_border": "rgba(255, 255, 255, 0.10)",

                # Text & Icons
                "text_primary": "#f8fafc",
                "text_secondary": "#94a3b8",
                "btn_bg": "rgba(255, 255, 255, 0.08)",
                "btn_hover": "rgba(255, 255, 255, 0.14)",
                "pill_bg": "rgba(255, 255, 255, 0.08)",
                "icon_stroke": "#e2e8f0",
            }
        else:
            # Light mode: active tab and toolbar are clean solid white blending with WebEngine like Chrome
            tab_start = blend_colors("#e4ebf5", base_hex, 0.14)
            tab_end = blend_colors("#dae3f0", base_hex, 0.20)
            nav_container_light = "#ffffff"
            border_tint = "#dbe3ee"

            return {
                # Title & Window Headers
                "title_grad_start": tab_start,
                "title_grad_mid": tab_start,
                "title_grad_end": tab_end,
                "title_border": border_tint,
                "window_bg": "#f1f5f9",
                "nav_container_bg": nav_container_light,

                # Tab Bar
                "tab_bar_grad_start": tab_start,
                "tab_bar_grad_end": tab_end,
                "tab_active_bg": nav_container_light,  # Solid pure white blending into toolbar & webengine like Chrome
                "tab_active_text": "#0f172a",
                "tab_inactive_bg": "transparent",       # Transparent on tab strip - clearly distinct
                "tab_inactive_text": "#475569",
                "tab_hover_bg": "rgba(255, 255, 255, 0.70)",
                "accent_blue": base_hex,
                "accent_glow": f"rgba({r}, {g}, {b}, 0.25)",

                # Address Bar & Omnibar
                "address_bg": "#f1f5f9",
                "address_bg_hover": "#e2e8f0",
                "address_border": "#dbe3ee",
                "address_text": "#0f172a",
                "address_placeholder": "#64748b",

                # Menus & Cards
                "menu_bg": "#ffffff",
                "menu_border": "#e2e8f0",
                "menu_text": "#0f172a",
                "menu_hover": f"rgba({r}, {g}, {b}, 0.10)",
                "page_bg": "#ffffff",
                "card_bg": "#ffffff",
                "card_border": "#e2e8f0",

                # Text & Icons
                "text_primary": "#0f172a",
                "text_secondary": "#475569",
                "btn_bg": "rgba(0, 0, 0, 0.05)",
                "btn_hover": "rgba(0, 0, 0, 0.10)",
                "pill_bg": "rgba(0, 0, 0, 0.06)",
                "icon_stroke": "#334155",
            }

