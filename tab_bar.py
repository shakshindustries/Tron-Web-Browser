import sys
from PyQt6.QtCore import Qt, QSize, QPoint, QPointF, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QRectF, QTimer
from PyQt6.QtGui import QIcon, QColor, QPainter, QPainterPath, QPen, QLinearGradient
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSizePolicy, QGraphicsDropShadowEffect, QFrame, QApplication
)
from theme_manager import ThemeManager, parse_color, get_tinted_icon, hex_to_rgb, blend_colors, resolve_resource

class WindowControlButton(QPushButton):
    """Sleek fully rounded circular caption button (minimize, maximize, close)."""
    def __init__(self, icon_path=None, is_close=False, btn_type=None, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.is_close = is_close
        if btn_type:
            self.btn_type = btn_type
        elif is_close:
            self.btn_type = "close"
        elif icon_path and "min" in icon_path:
            self.btn_type = "minimize"
        elif icon_path and ("max" in icon_path or "restore" in icon_path):
            self.btn_type = "restore" if "restore" in icon_path else "maximize"
        else:
            self.btn_type = "minimize"
            
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._pressed = False
        self.setMouseTracking(True)
        ThemeManager.instance().theme_changed.connect(self.update)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def update_icon(self, icon_path):
        self.icon_path = icon_path
        if "restore" in icon_path:
            self.btn_type = "restore"
        elif "max" in icon_path:
            self.btn_type = "maximize"
        self.update()

    def update_style(self):
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        if self.is_close:
            if self._pressed:
                p.setBrush(QColor("#be123c"))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(rect, 6.0, 6.0)
                icon_color = QColor("#ffffff")
            elif self._hovered:
                p.setBrush(QColor("#e11d48"))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(rect, 6.0, 6.0)
                icon_color = QColor("#ffffff")
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(Qt.PenStyle.NoPen)
                icon_color = QColor("#475569") if not is_dark else parse_color(c["icon_stroke"])
        else:
            if self._pressed:
                p.setBrush(QColor(0, 0, 0, 20) if not is_dark else parse_color(c["btn_bg"]))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(rect, 6.0, 6.0)
                icon_color = parse_color(c["text_primary"])
            elif self._hovered:
                p.setBrush(QColor(0, 0, 0, 10) if not is_dark else parse_color(c["btn_hover"]))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(rect, 6.0, 6.0)
                icon_color = parse_color(c["text_primary"])
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(Qt.PenStyle.NoPen)
                icon_color = QColor("#475569") if not is_dark else parse_color(c["icon_stroke"])

        pen = QPen(icon_color)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        if self.btn_type == "close":
            pen.setWidthF(1.5)
            p.setPen(pen)
            arm = 4.2
            p.drawLine(QPointF(cx - arm, cy - arm), QPointF(cx + arm, cy + arm))
            p.drawLine(QPointF(cx + arm, cy - arm), QPointF(cx - arm, cy + arm))
        elif self.btn_type == "minimize":
            pen.setWidthF(1.6)
            p.setPen(pen)
            arm = 4.5
            p.drawLine(QPointF(cx - arm, cy + 0.5), QPointF(cx + arm, cy + 0.5))
        elif self.btn_type == "maximize":
            pen.setWidthF(1.3)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            half = 4.2
            p.drawRoundedRect(QRectF(cx - half, cy - half, half * 2, half * 2), 1.5, 1.5)
        elif self.btn_type == "restore":
            pen.setWidthF(1.2)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(cx - 2.5, cy - 5.0, 7.0, 7.0), 1.0, 1.0)
            p.drawRoundedRect(QRectF(cx - 5.0, cy - 2.5, 7.0, 7.0), 1.0, 1.0)

        p.end()


class TabCloseButton(QPushButton):
    """Minimal circular close button for tab pills."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._pressed = False

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = ThemeManager.instance().is_dark()
        c = ThemeManager.instance().colors()
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        if not is_dark:
            # Light mode: clean black / dark charcoal cross for maximum visibility
            base_icon = QColor("#0f172a")
            hover_bg = QColor(0, 0, 0, 25)
            pressed_bg = QColor(0, 0, 0, 45)
            hover_icon = QColor("#000000")
            pressed_icon = QColor("#000000")
        else:
            # Dark mode: clean bright icon for contrast against dark tab
            base_icon = QColor("#cbd5e1")
            hover_bg = QColor(255, 255, 255, 28)
            pressed_bg = QColor(255, 255, 255, 50)
            hover_icon = QColor("#ffffff")
            pressed_icon = QColor("#ffffff")

        if self._pressed:
            p.setBrush(pressed_bg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
            pen_color = pressed_icon
        elif self._hovered:
            p.setBrush(hover_bg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
            pen_color = hover_icon
        else:
            pen_color = base_icon

        pen = QPen(pen_color)
        pen.setWidthF(1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        arm = 3.2
        p.drawLine(QPointF(cx - arm, cy - arm), QPointF(cx + arm, cy + arm))
        p.drawLine(QPointF(cx + arm, cy - arm), QPointF(cx - arm, cy + arm))
        p.end()


class TabWidget(QWidget):
    """Chrome-style connected tab widget that merges seamlessly with the toolbar when active."""
    clicked = pyqtSignal()
    close_requested = pyqtSignal()
    context_menu_requested = pyqtSignal(QPoint)
    mute_requested = pyqtSignal()

    def __init__(self, title="New Tab", parent=None):
        super().__init__(parent)
        self._is_active = False
        self._hovered = False
        self._is_sleeping = False
        self._title = title
        self._icon = None
        self._is_loading = False
        self._loading_angle = 0
        self._is_audible = False
        self._is_muted = False
        
        self.setFixedHeight(34)
        self.setMinimumWidth(100)
        self.setMaximumWidth(220)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Loading animation timer
        self.loading_timer = QTimer(self)
        self.loading_timer.setInterval(30)
        self.loading_timer.timeout.connect(self._rotate_loading)

        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(6)

        # Favicon
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setScaledContents(True)
        layout.addWidget(self.icon_label)

        # Title
        self.title_label = QLabel(title, self)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.title_label, 1)

        # Speaker icon / Mute button
        self.speaker_btn = QPushButton(self)
        self.speaker_btn.setFixedSize(16, 16)
        self.speaker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.speaker_btn.setToolTip("Mute / Unmute tab")
        self.speaker_btn.setStyleSheet("background: transparent; border: none;")
        self.speaker_btn.clicked.connect(self.mute_requested.emit)
        self.speaker_btn.hide()
        layout.addWidget(self.speaker_btn)

        # Close button (hidden by default, shown on active or hover)
        self.close_btn = TabCloseButton(self)
        self.close_btn.clicked.connect(self.close_requested.emit)
        self.close_btn.hide()
        layout.addWidget(self.close_btn)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self._is_dragging = False
        self.update_styles()

    def set_loading(self, is_loading):
        self._is_loading = is_loading
        if is_loading:
            self.icon_label.clear()
            self.loading_timer.start()
        else:
            self.loading_timer.stop()
            if self._is_sleeping:
                c = ThemeManager.instance().colors()
                moon_icon = get_tinted_icon("assets/moon.svg", c.get("accent_blue", "#2563eb"), QSize(16, 16))
                self.icon_label.setPixmap(moon_icon.pixmap(QSize(16, 16)))
            elif not self._icon or self._icon.isNull():
                if self._title == "New Tab":
                    self.icon_label.setPixmap(QIcon(resolve_resource("assets/app_icon.png")).pixmap(QSize(16, 16)))
                else:
                    c = ThemeManager.instance().colors()
                    default_icon = get_tinted_icon("assets/globe.svg", c["icon_stroke"], QSize(16, 16))
                    self.icon_label.setPixmap(default_icon.pixmap(QSize(16, 16)))
        self.update()

    def set_sleeping(self, is_sleeping):
        self._is_sleeping = is_sleeping
        if is_sleeping:
            c = ThemeManager.instance().colors()
            moon_icon = get_tinted_icon("assets/moon.svg", c.get("accent_blue", "#2563eb"), QSize(16, 16))
            self.icon_label.setPixmap(moon_icon.pixmap(QSize(16, 16)))
        else:
            self.set_icon(self._icon)
        self.update_styles()

    def _rotate_loading(self):
        self._loading_angle = (self._loading_angle + 12) % 360
        self.update()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        if self._is_sleeping:
            color = c["text_secondary"]
            weight = "400"
            font_style = "font-style: italic;"
        else:
            color = c["tab_active_text"] if self._is_active else c["tab_inactive_text"]
            weight = "600" if self._is_active else "400"
            font_style = ""
        
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                font-size: 12px;
                font-weight: {weight};
                {font_style}
                background: transparent;
                border: none;
            }}
        """)
        if self._is_sleeping:
            moon_icon = get_tinted_icon("assets/moon.svg", c.get("accent_blue", "#2563eb"), QSize(16, 16))
            self.icon_label.setPixmap(moon_icon.pixmap(QSize(16, 16)))
        elif not self._icon or self._icon.isNull():
            if self._title == "New Tab":
                self.icon_label.setPixmap(QIcon(resolve_resource("assets/app_icon.png")).pixmap(QSize(16, 16)))
            else:
                default_icon = get_tinted_icon("assets/globe.svg", c["icon_stroke"], QSize(16, 16))
                self.icon_label.setPixmap(default_icon.pixmap(QSize(16, 16)))

        if self._is_audible:
            self._update_speaker_icon()

        if self._is_active or self._hovered:
            self.close_btn.show()
        else:
            self.close_btn.hide()

        self.update()

    def set_active(self, active):
        self._is_active = active
        self.update_styles()

    def set_title(self, title):
        self._title = title
        metrics = self.title_label.fontMetrics()
        elided = metrics.elidedText(title, Qt.TextElideMode.ElideRight, 130)
        self.title_label.setText(elided)

    def set_icon(self, icon):
        self._icon = icon
        if self._is_sleeping:
            c = ThemeManager.instance().colors()
            moon_icon = get_tinted_icon("assets/moon.svg", c.get("accent_blue", "#2563eb"), QSize(16, 16))
            self.icon_label.setPixmap(moon_icon.pixmap(QSize(16, 16)))
        elif icon and not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(QSize(16, 16)))
        else:
            if self._title == "New Tab":
                self.icon_label.setPixmap(QIcon(resolve_resource("assets/app_icon.png")).pixmap(QSize(16, 16)))
            else:
                c = ThemeManager.instance().colors()
                default_icon = get_tinted_icon("assets/globe.svg", c["icon_stroke"], QSize(16, 16))
                self.icon_label.setPixmap(default_icon.pixmap(QSize(16, 16)))

    def set_audible(self, audible, is_muted=False):
        self._is_audible = audible
        self._is_muted = is_muted
        if audible:
            self.speaker_btn.show()
            self._update_speaker_icon()
        else:
            self.speaker_btn.hide()

    def set_muted(self, is_muted):
        self._is_muted = is_muted
        self._update_speaker_icon()

    def _update_speaker_icon(self):
        c = ThemeManager.instance().colors()
        color = c["accent_blue"] if self._is_active else c["text_secondary"]
        self.speaker_btn.setIcon(get_tinted_icon("assets/speaker.svg", color, QSize(14, 14)))
        self.speaker_btn.setIconSize(QSize(14, 14))
        self.speaker_btn.setToolTip("Unmute tab" if self._is_muted else "Mute tab")

    def enterEvent(self, event):
        self._hovered = True
        self.close_btn.show()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        if not self._is_active:
            self.close_btn.hide()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.clicked.emit()
            self._drag_start_pos = event.position().toPoint()
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if not self._is_active:
                super().mouseMoveEvent(event)
                return
            if not getattr(self, '_is_dragging', False) and hasattr(self, '_drag_start_pos'):
                diff = event.position().toPoint() - self._drag_start_pos
                if diff.manhattanLength() > 12:
                    p = self.parent()
                    while p and not hasattr(p, 'start_drag'):
                        p = p.parent()
                    if p and hasattr(p, 'start_drag'):
                        p.start_drag(self, event.globalPosition().toPoint())
            elif getattr(self, '_is_dragging', False):
                p = self.parent()
                while p and not hasattr(p, 'handle_drag_move'):
                    p = p.parent()
                if p and hasattr(p, 'handle_drag_move'):
                    p.handle_drag_move(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_is_dragging', False):
            self._is_dragging = False
            p = self.parent()
            while p and not hasattr(p, 'end_drag'):
                p = p.parent()
            if p and hasattr(p, 'end_drag'):
                p.end_drag()
        if hasattr(self, '_drag_start_pos'):
            delattr(self, '_drag_start_pos')
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()

        if self._is_active:
            # Active tab: blends seamlessly into toolbar and webengine like Chrome!
            # Extends from rounded top corners all the way to the bottom edge (h)
            r = 9.0
            path = QPainterPath()
            path.moveTo(0.0, h)
            path.lineTo(0.0, r)
            path.quadTo(0.0, 0.0, r, 0.0)
            path.lineTo(w - r, 0.0)
            path.quadTo(w, 0.0, w, r)
            path.lineTo(w, h)
            path.closeSubpath()

            active_bg = parse_color(c.get("tab_active_bg", "#ffffff" if not is_dark else "#1e1e2e"))
            p.fillPath(path, active_bg)
            
            # Subtle soft highlight on active tab edge
            highlight_col = QColor(0, 0, 0, 22) if not is_dark else QColor(255, 255, 255, 25)
            p.setPen(QPen(highlight_col, 0.8))
            p.drawPath(path)

        elif self._hovered:
            # Hover state: soft pill highlight
            r = 7.0
            pill_rect = QRectF(2.0, 3.0, w - 4.0, h - 6.0)
            path = QPainterPath()
            path.addRoundedRect(pill_rect, r, r)
            hover_col = parse_color(c.get("tab_hover_bg", "rgba(255, 255, 255, 0.70)" if not is_dark else "rgba(255, 255, 255, 0.08)"))
            p.fillPath(path, hover_col)
        else:
            # Inactive tab: completely transparent so tab strip background shows through
            # Subtle vertical separator line on right edge between tabs (matching Chrome)
            sep_col = QColor(0, 0, 0, 35) if not is_dark else QColor(255, 255, 255, 24)
            p.setPen(QPen(sep_col, 1.0))
            p.drawLine(QPointF(w - 1.0, 10.0), QPointF(w - 1.0, h - 10.0))

        # Loading spinner arc
        if self._is_loading:
            pen = QPen(parse_color(c["accent_blue"]), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            icon_geo = self.icon_label.geometry()
            r = QRectF(icon_geo).adjusted(1, 1, -1, -1)
            p.drawArc(r, -self._loading_angle * 16, 270 * 16)

        p.end()


class AddTabButton(QPushButton):
    """Floating fully rounded circular + button with dedicated background and smooth hover effect."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._pressed = False
        self.setToolTip("New tab (Ctrl+T)")
        ThemeManager.instance().theme_changed.connect(self.update)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()

        acc_hex = c["accent_blue"]
        if not is_dark:
            r, g, b = hex_to_rgb(acc_hex)
            if self._pressed:
                p.setBrush(QColor(r, g, b, 70))
                p.setPen(Qt.PenStyle.NoPen)
                icon_color = parse_color(blend_colors(acc_hex, "#000000", 0.3))
            elif self._hovered:
                p.setBrush(QColor(r, g, b, 50))
                p.setPen(QPen(QColor(r, g, b, 90), 1.0))
                icon_color = parse_color(blend_colors(acc_hex, "#000000", 0.2))
            else:
                p.setBrush(QColor(r, g, b, 35))
                p.setPen(QPen(QColor(r, g, b, 60), 1.0))
                icon_color = parse_color(acc_hex)
        else:
            if self._pressed:
                p.setBrush(parse_color(c["btn_bg"]))
                p.setPen(QPen(parse_color(c["accent_blue"]), 1.2))
                icon_color = parse_color(c["accent_blue"])
            elif self._hovered:
                p.setBrush(parse_color(c["btn_hover"]))
                p.setPen(QPen(parse_color(c["accent_blue"]), 1.1))
                icon_color = parse_color(c["accent_blue"])
            else:
                p.setBrush(QColor(255, 255, 255, 18))
                p.setPen(QPen(QColor(255, 255, 255, 25), 1.0))
                icon_color = parse_color(c["icon_stroke"])

        p.drawEllipse(rect)

        pen = QPen(icon_color)
        pen.setWidthF(1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        arm = 4.2
        p.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))
        p.drawLine(QPointF(cx, cy - arm), QPointF(cx, cy + arm))
        p.end()


class TronHistoryButton(QPushButton):
    """Tron sleek corner-rounded squircle button on the left of the tab strip to show tab search and history."""
    def __init__(self, browser_window, parent=None):
        super().__init__(parent)
        self.browser_window = browser_window
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._pressed = False
        self.setMouseTracking(True)
        self.setToolTip("Search tabs & history (Ctrl+H)")
        self.clicked.connect(self.show_history_popup)
        ThemeManager.instance().theme_changed.connect(self.update)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        if self._pressed:
            p.setBrush(parse_color(c["btn_bg"]))
            p.setPen(QPen(parse_color(c["accent_blue"]), 1.2))
            icon_color = parse_color(c["accent_blue"])
        elif self._hovered:
            p.setBrush(QColor(255, 255, 255, 250) if not is_dark else parse_color(c["btn_hover"]))
            p.setPen(QPen(parse_color(c["accent_blue"]), 1.1))
            icon_color = parse_color(c["accent_blue"])
        else:
            idle_bg = QColor(255, 255, 255, 140) if not is_dark else QColor(255, 255, 255, 16)
            idle_border = parse_color(c["title_border"])
            p.setBrush(idle_bg)
            p.setPen(QPen(idle_border, 1.0))
            icon_color = parse_color(c["icon_stroke"])

        p.drawRoundedRect(rect, 7.5, 7.5)

        # Draw clean vector clock icon
        cx, cy = w / 2.0, h / 2.0
        r = 5.2
        pen = QPen(icon_color)
        pen.setWidthF(1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawLine(QPointF(cx, cy), QPointF(cx, cy - 3.0))
        p.drawLine(QPointF(cx, cy), QPointF(cx + 2.5, cy))
        p.end()

    def show_history_popup(self):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        menu = QMenu(self)
        c = ThemeManager.instance().colors()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {c['menu_bg']};
                border: 1px solid {c['menu_border']};
                border-radius: 12px;
                padding: 6px;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            QMenu::item {{
                padding: 8px 24px 8px 12px;
                border-radius: 6px;
                color: {c['menu_text']};
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background-color: {c['menu_hover']};
                color: {c['accent_blue']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {c['title_border']};
                margin: 4px 8px;
            }}
        """)
        
        header_act = QAction("🕒 Recently Closed & History", menu)
        header_act.setEnabled(False)
        menu.addAction(header_act)
        menu.addSeparator()

        try:
            from history_manager import HistoryManager
            items = HistoryManager.instance().get_history()[:10]
            if items:
                for it in items:
                    title = it.get("title") or it.get("url")
                    url = it.get("url", "")
                    short_title = title if len(title) <= 45 else title[:42] + "..."
                    act = QAction(get_tinted_icon("assets/history.svg", c["icon_stroke"], QSize(14, 14)), short_title, menu)
                    act.setToolTip(url)
                    act.triggered.connect(lambda checked=False, u=url: self.browser_window.add_new_tab(u))
                    menu.addAction(act)
            else:
                empty_act = QAction("No recent browsing history", menu)
                empty_act.setEnabled(False)
                menu.addAction(empty_act)
        except Exception:
            pass

        menu.addSeparator()
        full_act = QAction(get_tinted_icon("assets/open.svg", c["icon_stroke"], QSize(14, 14)), "Open full history (Ctrl+H)", menu)
        full_act.triggered.connect(self.browser_window.open_history_page)
        menu.addAction(full_act)

        menu.exec(self.mapToGlobal(QPoint(0, self.height() + 4)))


ChromeHistoryButton = TronHistoryButton


class TabBarContainer(QWidget):
    """Top-level title and tab strip holding Tab Search & History, connected tabs, drag area, and circular caption controls."""
    tab_context_menu_requested = pyqtSignal(int, QPoint)
    tab_mute_requested = pyqtSignal(int)

    def __init__(self, browser_window, parent=None):
        super().__init__(parent)
        self.browser_window = browser_window
        self.tabs = []
        self._active_index = -1
        self._drag_tab = None
        self._drag_start_index = -1
        self.setFixedHeight(42)
        self.setMouseTracking(True)
        self.setObjectName("tabBarContainer")

        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(8, 6, 8, 0)
        self._main_layout.setSpacing(6)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        # App icon permanently removed from title bar to match Chrome clean layout
        self.brand_container = QWidget(self)
        self.brand_container.hide()
        self.brand_logo_btn = QPushButton(self.brand_container)
        self.brand_logo_btn.hide()

        self.history_btn_container = QWidget(self)
        self.history_btn_container.hide() # Hidden to match reference layout with logo on left

        self.app_icon_label = QLabel(self)
        self.app_icon_label.hide()

        # Incognito Pill Badge
        self.incognito_badge = QLabel("🕵️ Incognito", self)
        self.incognito_badge.setObjectName("incognitoBadge")
        self.incognito_badge.hide()
        self._main_layout.addWidget(self.incognito_badge)

        if getattr(self.browser_window, "is_incognito", False):
            self.incognito_badge.show()

        # PWA Title Label (for PWA mode)
        self.pwa_title_label = QLabel("Web App", self)
        self.pwa_title_label.setObjectName("pwaTitleLabel")
        self.pwa_title_label.hide()
        self._main_layout.addWidget(self.pwa_title_label)

        # 2. Tabs Container (grouped on left, sits flush at bottom)
        self.tabs_container = QWidget(self)
        self.tabs_container.setObjectName("tabsContainer")
        self.tabs_container.setFixedHeight(36)
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(2)
        self.tabs_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        self.add_btn = AddTabButton(self.tabs_container)
        self.add_btn.clicked.connect(lambda checked=False: self.browser_window.add_new_tab())
        self.tabs_layout.addWidget(self.add_btn)

        self._main_layout.addWidget(self.tabs_container)

        # 3. Empty Draggable Space (takes all remaining room between tabs and window controls)
        self.empty_drag = QWidget(self)
        self.empty_drag.setObjectName("emptyDragArea")
        self.empty_drag.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._main_layout.addWidget(self.empty_drag)

        # 4. Right Section: Window Controls (Sleek full rounded circular buttons)
        self.win_controls = QWidget(self)
        self.win_controls.setObjectName("winControlsPill")
        win_layout = QHBoxLayout(self.win_controls)
        win_layout.setContentsMargins(0, 0, 4, 0)
        win_layout.setSpacing(6)
        win_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        is_max = getattr(self.browser_window, "isMaximized", lambda: False)()
        self.min_btn = WindowControlButton("assets/minimize.svg", is_close=False, btn_type="minimize", parent=self.win_controls)
        self.max_btn = WindowControlButton("assets/maximize.svg", is_close=False, btn_type="restore" if is_max else "maximize", parent=self.win_controls)
        self.close_btn = WindowControlButton("assets/close.svg", is_close=True, btn_type="close", parent=self.win_controls)

        self.min_btn.clicked.connect(self.browser_window.showMinimized)
        self.max_btn.clicked.connect(self._toggle_max_restore)
        self.close_btn.clicked.connect(self.browser_window.close)

        win_layout.addWidget(self.min_btn)
        win_layout.addWidget(self.max_btn)
        win_layout.addWidget(self.close_btn)
        self._main_layout.addWidget(self.win_controls)

        ThemeManager.instance().theme_changed.connect(self.update_theme_styles)
        self.update_theme_styles()

    def set_pwa_mode(self, is_pwa, title="Web App"):
        if is_pwa:
            self.tabs_container.hide()
            self.pwa_title_label.setText(title)
            self.pwa_title_label.show()
        else:
            self.tabs_container.show()
            self.pwa_title_label.hide()

    def update_theme_styles(self):
        c = ThemeManager.instance().colors()
        for tab in getattr(self, "tabs", []):
            tab.update_styles()
        if hasattr(self, "history_btn"):
            self.history_btn.update()
        if hasattr(self, "add_btn"):
            self.add_btn.update()
        if getattr(self.browser_window, "is_incognito", False):
            self.incognito_badge.setStyleSheet("""
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
                color: #c4a7e7;
                background: rgba(196, 167, 231, 0.18);
                border-radius: 6px;
                padding: 3px 8px;
                margin-bottom: 6px;
            """)
        self.pwa_title_label.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 600;
            color: {c['text_primary']};
            background: transparent;
            padding-left: 8px;
            margin-bottom: 6px;
        """)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()

        w = float(self.width())
        h = float(self.height())

        # Dynamic header gradient based on theme and accent
        tab_start = parse_color(c["tab_bar_grad_start"])
        tab_end = parse_color(c["tab_bar_grad_end"])
        grad = QLinearGradient(0.0, 0.0, w, 0.0)
        grad.setColorAt(0.0, tab_start)
        grad.setColorAt(1.0, tab_end)
        p.fillRect(self.rect(), grad)

        # Curved decorative swoosh / crest on the top-right caption area matching reference
        # (Preserved consistently in BOTH Light and Dark mode)
        swoosh_path = QPainterPath()
        swoosh_start_x = max(0.0, w - 170.0)
        swoosh_path.moveTo(swoosh_start_x, h)
        swoosh_path.cubicTo(swoosh_start_x + 35.0, h, swoosh_start_x + 40.0, 0.0, swoosh_start_x + 85.0, 0.0)
        swoosh_path.lineTo(w, 0.0)
        swoosh_path.lineTo(w, h)
        swoosh_path.closeSubpath()

        swoosh_grad = QLinearGradient(swoosh_start_x, 0.0, w, h)
        if not is_dark:
            swoosh_grad.setColorAt(0.0, QColor(147, 197, 253, 110))
            swoosh_grad.setColorAt(1.0, QColor(191, 219, 254, 180))
            highlight_color = QColor(96, 165, 250, 140)
        else:
            swoosh_grad.setColorAt(0.0, QColor(255, 255, 255, 12))
            swoosh_grad.setColorAt(1.0, QColor(255, 255, 255, 24))
            highlight_color = QColor(255, 255, 255, 35)

        p.fillPath(swoosh_path, swoosh_grad)

        # Delicate swoosh edge highlight line
        edge_path = QPainterPath()
        edge_path.moveTo(swoosh_start_x, h)
        edge_path.cubicTo(swoosh_start_x + 35.0, h, swoosh_start_x + 40.0, 0.0, swoosh_start_x + 85.0, 0.0)
        edge_path.lineTo(w, 0.0)
        p.setPen(QPen(highlight_color, 1.2))
        p.drawPath(edge_path)

        # Bottom separator line between tab strip and toolbar (leaving active tab open to blend like Chrome!)
        sep_color = parse_color(c["title_border"])
        p.setPen(QPen(sep_color, 1.0))
        y_bot = int(h - 1)
        
        active_tab = None
        for t in getattr(self, "tabs", []):
            if getattr(t, "_is_active", False) and t.isVisible():
                active_tab = t
                break

        if active_tab:
            p1 = active_tab.mapTo(self, QPoint(0, 0))
            x_start = max(0, p1.x())
            x_end = min(int(w), p1.x() + active_tab.width())
            if x_start > 0:
                p.drawLine(0, y_bot, x_start, y_bot)
            if x_end < int(w):
                p.drawLine(x_end, y_bot, int(w), y_bot)
        else:
            p.drawLine(0, y_bot, int(w), y_bot)
        p.end()

    def add_tab(self, title):
        tab = TabWidget(title, self.tabs_container)
        tab.clicked.connect(lambda t=tab: self._on_tab_widget_clicked(t))
        tab.close_requested.connect(lambda t=tab: self._on_tab_widget_close_requested(t))
        tab.context_menu_requested.connect(lambda pos, t=tab: self._on_tab_widget_context_menu(t, pos))
        tab.mute_requested.connect(lambda t=tab: self._on_tab_widget_mute_requested(t))
        self.tabs.append(tab)

        add_btn_pos = self.tabs_layout.indexOf(self.add_btn)
        self.tabs_layout.insertWidget(add_btn_pos, tab)

        # Tab width defaults
        tab.setMinimumWidth(100)
        tab.setMaximumWidth(220)

        # Smooth Chrome-style tab expand animation for subsequent tabs
        if len(self.tabs) > 1:
            tab.setMaximumWidth(0)
            anim = QPropertyAnimation(tab, b"maximumWidth", tab)
            anim.setDuration(160)
            anim.setStartValue(0)
            anim.setEndValue(200)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            def _restore_limits():
                tab.setMinimumWidth(100)
                tab.setMaximumWidth(220)

            anim.finished.connect(_restore_limits)
            anim.start()
            tab._open_anim = anim

        return len(self.tabs) - 1

    def _on_tab_widget_clicked(self, tab_widget):
        if tab_widget in self.tabs:
            index = self.tabs.index(tab_widget)
            self.set_active(index)
            self.browser_window.switch_tab(index)

    def _on_tab_widget_close_requested(self, tab_widget):
        if tab_widget in self.tabs:
            index = self.tabs.index(tab_widget)
            self.browser_window.close_tab(index)

    def _on_tab_widget_context_menu(self, tab_widget, pos):
        if tab_widget in self.tabs:
            index = self.tabs.index(tab_widget)
            self.tab_context_menu_requested.emit(index, pos)

    def _on_tab_widget_mute_requested(self, tab_widget):
        if tab_widget in self.tabs:
            index = self.tabs.index(tab_widget)
            self.tab_mute_requested.emit(index)

    def set_active(self, index):
        self._active_index = index
        for i, tab in enumerate(self.tabs):
            tab.set_active(i == index)
        self.update()

    def remove_tab(self, index):
        if 0 <= index < len(self.tabs):
            tab = self.tabs.pop(index)
            # Smooth Chrome-style tab collapse animation
            tab.close_btn.hide()
            tab.title_label.hide()
            tab.icon_label.hide()
            tab.setMinimumWidth(0)

            anim = QPropertyAnimation(tab, b"maximumWidth", tab)
            anim.setDuration(130)
            anim.setStartValue(tab.width())
            anim.setEndValue(0)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)

            def _cleanup():
                self.tabs_layout.removeWidget(tab)
                tab.deleteLater()
                self.update()

            anim.finished.connect(_cleanup)
            anim.start()
            tab._close_anim = anim

    def set_tab_title(self, index, title):
        if 0 <= index < len(self.tabs):
            self.tabs[index].set_title(title)

    def set_tab_icon(self, index, icon):
        if 0 <= index < len(self.tabs):
            self.tabs[index].set_icon(icon)

    def set_tab_loading(self, index, is_loading):
        if 0 <= index < len(self.tabs):
            self.tabs[index].set_loading(is_loading)

    def set_tab_audible(self, index, audible, is_muted=False):
        if 0 <= index < len(self.tabs):
            self.tabs[index].set_audible(audible, is_muted)

    def set_tab_muted(self, index, is_muted):
        if 0 <= index < len(self.tabs):
            self.tabs[index].set_muted(is_muted)

    def set_tab_sleeping(self, index, is_sleeping):
        if 0 <= index < len(self.tabs):
            self.tabs[index].set_sleeping(is_sleeping)

    def _toggle_max_restore(self):
        if self.browser_window.isMaximized():
            self.browser_window.showNormal()
            self.browser_window.setWindowState(Qt.WindowState.WindowNoState)
            if hasattr(self.browser_window, "_last_normal_geometry") and self.browser_window._last_normal_geometry:
                self.browser_window.setGeometry(self.browser_window._last_normal_geometry)
        else:
            self.browser_window._last_normal_geometry = self.browser_window.geometry()
            self.browser_window.showMaximized()
        self.update_max_icon(self.browser_window.isMaximized())

    def update_max_icon(self, is_maximized):
        self.max_btn.btn_type = "restore" if is_maximized else "maximize"
        self.max_btn.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child in (None, self, self.empty_drag, self.app_icon_label):
                self._toggle_max_restore()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child in (None, self, self.empty_drag, self.app_icon_label):
                self.drag_pos = event.globalPosition().toPoint() - self.browser_window.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_drag_tab', None) and event.buttons() & Qt.MouseButton.LeftButton:
            self.handle_drag_move(event.globalPosition().toPoint())
        elif event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, 'drag_pos') and self.drag_pos:
            if self.browser_window.isMaximized():
                self.browser_window.showNormal()
                if hasattr(self.browser_window, "_last_normal_geometry") and self.browser_window._last_normal_geometry:
                    self.browser_window.setGeometry(self.browser_window._last_normal_geometry)
            self.browser_window.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self, 'drag_pos'):
            delattr(self, 'drag_pos')
        if getattr(self, '_drag_tab', None):
            self.end_drag()
        super().mouseReleaseEvent(event)

    # --- Animated Drag Reorder ---
    def start_drag(self, tab_widget, global_pos):
        if tab_widget not in self.tabs or not getattr(tab_widget, '_is_active', False):
            return
        self._drag_tab = tab_widget
        self._drag_tab._is_dragging = True
        self._drag_start_index = self.tabs.index(tab_widget)
        self.handle_drag_move(global_pos)

    def handle_drag_move(self, global_pos):
        if not self._drag_tab or self._drag_start_index == -1:
            return
        local_pos = self.tabs_container.mapFromGlobal(global_pos)
        x = local_pos.x()
        for i, tab in enumerate(self.tabs):
            if tab == self._drag_tab:
                continue
            tab_center = tab.geometry().center().x()

            if i < self._drag_start_index and x < tab_center:
                self._swap_tabs(self._drag_start_index, i)
                break
            elif i > self._drag_start_index and x > tab_center:
                self._swap_tabs(self._drag_start_index, i)
                break

    def end_drag(self):
        if self._drag_tab:
            if hasattr(self._drag_tab, '_is_dragging'):
                self._drag_tab._is_dragging = False
            self._drag_tab = None
            self._drag_start_index = -1

    def _swap_tabs(self, from_idx, to_idx):
        old_positions = {tab: tab.pos() for tab in self.tabs}
        self.tabs[from_idx], self.tabs[to_idx] = self.tabs[to_idx], self.tabs[from_idx]

        for tab in self.tabs:
            self.tabs_layout.removeWidget(tab)

        for i, tab in enumerate(self.tabs):
            self.tabs_layout.insertWidget(i, tab)

        self.tabs_layout.activate()

        for tab in self.tabs:
            if tab == self._drag_tab:
                continue
            old_p = old_positions.get(tab)
            new_p = tab.pos()
            if old_p and old_p != new_p:
                if not hasattr(tab, "_reorder_anim"):
                    tab._reorder_anim = QPropertyAnimation(tab, b"pos")
                    tab._reorder_anim.setDuration(180)
                    tab._reorder_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                tab._reorder_anim.stop()
                tab._reorder_anim.setStartValue(old_p)
                tab._reorder_anim.setEndValue(new_p)
                tab._reorder_anim.start()

        if self._active_index == from_idx:
            self._active_index = to_idx
        elif self._active_index == to_idx:
            self._active_index = from_idx

        self._drag_start_index = to_idx
        self.set_active(self._active_index)
        self.browser_window.swap_browser_tabs(from_idx, to_idx)

    @property
    def tab_bar(self):
        return self
    
    def count(self):
        return len(self.tabs)

    def setCurrentIndex(self, index):
        self.set_active(index)
