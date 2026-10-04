from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsDropShadowEffect, QGraphicsOpacityEffect

class TronToastOverlay(QWidget):
    """A sleek native Qt floating toast notification overlay."""
    def __init__(self, parent_container):
        super().__init__(parent_container)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setFixedHeight(44)
        self.setObjectName("nativeToastOverlay")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 18, 8)
        layout.setSpacing(10)

        self.icon_label = QLabel("ℹ️")
        self.icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        
        self.text_label = QLabel()
        self.text_label.setStyleSheet("""
            font-family: 'Segoe UI', 'Roboto', sans-serif;
            font-size: 13px;
            font-weight: 500;
            background: transparent;
        """)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

        # Soft drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        # Opacity animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.pos_anim = QPropertyAnimation(self, b"pos")
        self.pos_anim.setDuration(280)
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(280)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_toast)

        self.hide()

    def show_message(self, message, is_error=False, duration_ms=4000):
        self.hide_timer.stop()
        self.pos_anim.stop()
        self.opacity_anim.stop()

        from theme_manager import ThemeManager
        colors = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()

        bg_color = "#2a1b1b" if (is_dark and is_error) else ("#1e293b" if is_dark else ("#fef2f2" if is_error else "#ffffff"))
        text_color = "#f87171" if is_error else colors["text_primary"]
        border_color = "rgba(239, 68, 68, 0.4)" if is_error else colors["card_border"]

        self.setStyleSheet(f"""
            #nativeToastOverlay {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 22px;
            }}
        """)
        self.text_label.setStyleSheet(f"""
            font-family: 'Segoe UI', 'Roboto', sans-serif;
            font-size: 13px;
            font-weight: 500;
            color: {text_color};
            background: transparent;
        """)

        self.icon_label.setText("⚠️" if is_error else "ℹ️")
        self.text_label.setText(message)
        self.adjustSize()

        parent = self.parentWidget()
        if parent:
            p_width = parent.width()
            p_height = parent.height()
            w = self.width()
            h = self.height()
            
            end_x = p_width - w - 24
            end_y = p_height - h - 24
            start_y = p_height + 20

            self.move(end_x, start_y)
            self.opacity_effect.setOpacity(0.0)
            self.show()
            self.raise_()

            self.pos_anim.setStartValue(QPoint(end_x, start_y))
            self.pos_anim.setEndValue(QPoint(end_x, end_y))
            self.pos_anim.start()

            self.opacity_anim.setStartValue(0.0)
            self.opacity_anim.setEndValue(1.0)
            self.opacity_anim.start()

            self.hide_timer.start(duration_ms)

    def hide_toast(self):
        parent = self.parentWidget()
        if parent:
            end_y = parent.height() + 20
            self.pos_anim.setStartValue(self.pos())
            self.pos_anim.setEndValue(QPoint(self.x(), end_y))
            self.opacity_anim.setStartValue(1.0)
            self.opacity_anim.setEndValue(0.0)
            self.pos_anim.start()
            self.opacity_anim.start()
            self.pos_anim.finished.connect(self.hide)
