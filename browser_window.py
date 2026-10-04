import sys
import os
import time
import ctypes
from ctypes import wintypes
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, QRect, QTimer, QEvent, QUrl, QObject, pyqtSignal, QPoint, QPointF, QThread, QStandardPaths, QMarginsF
from PyQt6.QtGui import QIcon, QCursor, QColor, QKeySequence, QShortcut, QPageLayout, QPageSize, QPageRanges
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QMenu, QFrame, QLineEdit, QDialog,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QScrollArea
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineScript, QWebEngineSettings

from download_manager import DownloadTracker, DownloadsPage, DownloadBubblePopup
from bookmarks_manager import BookmarkManager
from history_manager import HistoryManager
from bookmarks_page import BookmarksPage
from history_page import HistoryPage
from settings_page import SettingsPage
from about_page import AboutPage
from new_tab_page import NewTabPage
from title_bar import TitleBar
from tab_bar import TabBarContainer
from toast_overlay import TronToastOverlay
from theme_manager import ThemeManager, parse_color, get_tinted_icon, resolve_resource
from settings_manager import SettingsManager

class ZoomEventFilter(QObject):
    zoom_changed = pyqtSignal(float)

    def __init__(self, browser, window=None, parent=None):
        super().__init__(parent or browser)
        self.browser = browser
        self.window = window
        self.browser.installEventFilter(self)
        for child in self.browser.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                current_zoom = self.browser.zoomFactor()
                if delta > 0:
                    new_zoom = min(current_zoom + 0.1, 5.0)
                else:
                    new_zoom = max(current_zoom - 0.1, 0.25)

                new_zoom = round(new_zoom, 2)
                if abs(new_zoom - current_zoom) > 0.01:
                    self.browser.setZoomFactor(new_zoom)
                    self.zoom_changed.emit(new_zoom)
                    if self.window and hasattr(self.window, "show_zoom_toast"):
                        self.window.show_zoom_toast(new_zoom)
                event.accept()
                return True
        elif event.type() == QEvent.Type.ChildAdded:
            child = event.child()
            if isinstance(child, QWidget):
                child.installEventFilter(self)
        return super().eventFilter(obj, event)


class ZoomOverlay(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(96, 36)
        self.hide()

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.finished.connect(self.hide)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        self.update_style()
        ThemeManager.instance().theme_changed.connect(self.update_style)

    def update_style(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        bg = "rgba(24, 24, 37, 0.95)" if is_dark else "rgba(255, 255, 255, 0.96)"
        text_col = "#f8fafc" if is_dark else "#0f172a"
        border_col = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.14)"
        self.setStyleSheet(f"""
            QLabel {{
                color: {text_col};
                background-color: {bg};
                border: 1.5px solid {border_col};
                border-radius: 18px;
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                font-size: 13px;
                font-weight: 700;
                padding: 4px 12px;
            }}
        """)

    def show_zoom(self, factor):
        self.timer.stop()
        self.anim.stop()
        self.opacity_effect.setOpacity(1.0)
        self.update_style()

        percentage = int(round(factor * 100))
        self.setText(f"{percentage}%")

        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = 90
            self.move(x, y)

        self.show()
        self.raise_()
        self.timer.start(1200)

    def fade_out(self):
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.start()


class PermissionPopup(QWidget):
    def __init__(self, parent_browser, *args):
        super().__init__(parent_browser)
        self.parent_browser = parent_browser
        self.args = args
        self.origin = ""
        self.type_str = "microphone and camera"
        self.icon_path = "assets/lock.svg"
        
        if len(args) == 1:
            self.permission = args[0]
            self.origin = self.permission.origin().toString()
            perm_type = self.permission.permissionType()
            
            from PyQt6.QtWebEngineCore import QWebEnginePermission
            if perm_type == QWebEnginePermission.PermissionType.MediaAudioCapture:
                self.type_str = "microphone"
                self.icon_path = "assets/microphone.svg"
            elif perm_type == QWebEnginePermission.PermissionType.MediaVideoCapture:
                self.type_str = "camera"
                self.icon_path = "assets/camera.svg"
            elif perm_type == QWebEnginePermission.PermissionType.MediaAudioVideoCapture:
                self.type_str = "microphone and camera"
                self.icon_path = "assets/microphone.svg"
            elif perm_type == QWebEnginePermission.PermissionType.Geolocation:
                self.type_str = "location"
                self.icon_path = "assets/location.svg"
            elif perm_type == QWebEnginePermission.PermissionType.DesktopVideoCapture:
                self.type_str = "screen sharing"
                self.icon_path = "assets/screen.svg"
        elif len(args) == 2:
            self.origin_url, self.feature = args
            self.origin = self.origin_url.toString()
            
            from PyQt6.QtWebEngineCore import QWebEnginePage
            if self.feature == QWebEnginePage.Feature.MediaAudioCapture:
                self.type_str = "microphone"
                self.icon_path = "assets/microphone.svg"
            elif self.feature == QWebEnginePage.Feature.MediaVideoCapture:
                self.type_str = "camera"
                self.icon_path = "assets/camera.svg"
            elif self.feature == QWebEnginePage.Feature.MediaAudioVideoCapture:
                self.type_str = "microphone and camera"
                self.icon_path = "assets/microphone.svg"
            elif self.feature == QWebEnginePage.Feature.Geolocation:
                self.type_str = "location"
                self.icon_path = "assets/location.svg"

        self.setObjectName("permissionPopup")
        self.setFixedWidth(340)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)
        
        self.icon_label = QLabel()
        self.icon_label.setPixmap(QIcon(self.icon_path).pixmap(QSize(18, 18)))
        header.addWidget(self.icon_label)

        origin_clean = self.origin.replace("https://", "").replace("http://", "").rstrip("/")
        if len(origin_clean) > 30:
            origin_clean = origin_clean[:27] + "..."
            
        self.title_label = QLabel(f"<b>{origin_clean}</b> wants to use your {self.type_str}")
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName("permTitle")
        header.addWidget(self.title_label, 1)

        layout.addLayout(header)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch(1)

        self.block_btn = QPushButton("Block")
        self.block_btn.setObjectName("permBlockBtn")
        self.block_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.block_btn.clicked.connect(self.handle_block)
        btn_layout.addWidget(self.block_btn)

        self.allow_btn = QPushButton("Allow")
        self.allow_btn.setObjectName("permAllowBtn")
        self.allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.allow_btn.clicked.connect(self.handle_allow)
        btn_layout.addWidget(self.allow_btn)

        layout.addLayout(btn_layout)
        
        self.hide()
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        self.setStyleSheet(f"""
            #permissionPopup {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
            }}
            QLabel#permTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                color: {c['text_primary']};
            }}
            QPushButton#permBlockBtn {{
                background-color: {c['btn_bg']};
                color: {c['text_primary']};
                border: 1px solid {c['card_border']};
                border-radius: 6px;
                padding: 4px 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#permBlockBtn:hover {{
                background-color: {c['btn_hover']};
            }}
            QPushButton#permAllowBtn {{
                background-color: {c['accent_blue']};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 4px 14px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#permAllowBtn:hover {{
                background-color: {c['btn_hover']};
            }}
        """)

    def show_prompt(self):
        self.adjustSize()
        h = max(self.sizeHint().height(), 110)
        self.resize(340, h)
        x = 20
        start_y = -h - 20
        end_y = 16
        
        self.move(x, start_y)
        self.show()
        self.raise_()
        
        self.anim.stop()
        self.anim.setStartValue(QPoint(x, start_y))
        self.anim.setEndValue(QPoint(x, end_y))
        self.anim.start()

    def dismiss(self):
        h = max(self.height(), 110)
        x = self.x()
        start_y = self.y()
        end_y = -h - 30
        
        self.anim.stop()
        self.anim.setStartValue(QPoint(x, start_y))
        self.anim.setEndValue(QPoint(x, end_y))
        try:
            self.anim.finished.disconnect()
        except Exception:
            pass
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()

    def handle_allow(self):
        if len(self.args) == 1:
            self.permission.grant()
        elif len(self.args) == 2:
            page = self.parent_browser.page()
            page.setFeaturePermission(self.args[0], self.args[1], QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)
        self.dismiss()

    def handle_block(self):
        if len(self.args) == 1:
            self.permission.deny()
        elif len(self.args) == 2:
            page = self.parent_browser.page()
            page.setFeaturePermission(self.args[0], self.args[1], QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
        self.dismiss()


class SpeechRecognitionThread(QThread):
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def run(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.2)
                audio = r.listen(source, timeout=6, phrase_time_limit=10)
                text = r.recognize_google(audio)
                self.result_ready.emit(text)
        except Exception as e:
            self.error_occurred.emit(str(e))


class TronPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.speech_thread = None

    def _get_window(self):
        parent = self.parent()
        if parent and hasattr(parent, "window"):
            return parent.window()
        return None

    def createWindow(self, type_):
        win = self._get_window()
        if win and hasattr(win, "add_new_tab"):
            new_browser = win.add_new_tab(skip_default_load=True)
            if new_browser:
                return new_browser.page()
        return super().createWindow(type_)

    def chooseFiles(self, mode, old_files, accepted_mime_types):
        from PyQt6.QtWidgets import QFileDialog
        filters = ";;".join(accepted_mime_types) if accepted_mime_types else "All Files (*.*)"
        if mode == QWebEnginePage.FileSelectionMode.FileSelectOpenMultiple:
            files, _ = QFileDialog.getOpenFileNames(None, "Select Files to Upload", "", filters)
            return files
        elif mode == QWebEnginePage.FileSelectionMode.FileSelectSave:
            file, _ = QFileDialog.getSaveFileName(None, "Save File", "", filters)
            return [file] if file else []
        else:
            file, _ = QFileDialog.getOpenFileName(None, "Select File to Upload", "", filters)
            return [file] if file else []

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)
        if message == "TRON_SPEECH_CONTROL:START":
            self.start_speech_recognition()
        elif message in ["TRON_SPEECH_CONTROL:STOP", "TRON_SPEECH_CONTROL:ABORT"]:
            self.stop_speech_recognition()
        elif message == "TRON_PWA_INSTALLABLE:true":
            win = self._get_window()
            if win and hasattr(win, "set_pwa_installable"):
                win.set_pwa_installable(True)
        elif message == "TRON_PWA_INSTALLABLE:false":
            win = self._get_window()
            if win and hasattr(win, "set_pwa_installable"):
                win.set_pwa_installable(False)

    def start_speech_recognition(self):
        if self.speech_thread and self.speech_thread.isRunning():
            return
        self.speech_thread = SpeechRecognitionThread(self)
        self.speech_thread.result_ready.connect(self.on_speech_result)
        self.speech_thread.error_occurred.connect(self.on_speech_error)
        self.speech_thread.start()

    def stop_speech_recognition(self):
        if self.speech_thread and self.speech_thread.isRunning():
            self.speech_thread.terminate()
            self.speech_thread.wait()
            self.speech_thread = None

    def on_speech_result(self, text):
        escaped_text = text.replace("'", "\\'").replace('"', '\\"')
        js = f"""
            if (window._tronRecognition) {{
                const mockEvent = {{
                    resultIndex: 0,
                    results: [
                        [{{ transcript: '{escaped_text}' }}]
                    ]
                }};
                mockEvent.results[0].isFinal = true;
                if (window._tronRecognition.onresult) window._tronRecognition.onresult(mockEvent);
                if (window._tronRecognition.onend) window._tronRecognition.onend();
            }}
        """
        self.runJavaScript(js)

    def on_speech_error(self, error):
        err_type = 'no-speech'
        if 'pyaudio' in error.lower() or 'microphone' in error.lower():
            err_type = 'audio-capture'
        js = f"""
            if (window._tronRecognition) {{
                const errEvent = {{ error: '{err_type}', message: 'Speech recognition error: {error}' }};
                if (window._tronRecognition.onerror) window._tronRecognition.onerror(errEvent);
                if (window._tronRecognition.onend) window._tronRecognition.onend();
            }}
        """
class TronPrintDialog(QDialog):
    """Chrome-style default print dialogue with real-time PDF preview and full settings."""
    def __init__(self, web_page=None, page_title="Page", page_url="", parent=None):
        super().__init__(parent)
        self.web_page = web_page
        self.page_title = page_title or "Page"
        self.page_url = page_url or ""
        self.parent_win = parent

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.resize(1040, 690)
        self.setMinimumSize(850, 580)
        self.setObjectName("tronPrintDialog")
        self.setWindowTitle(f"Print — {self.page_title}")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 110))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)

        self._init_ui()

        temp_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
        self.temp_pdf_path = os.path.join(temp_dir, "tron_print_preview.pdf")

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.generate_pdf_preview)

        QTimer.singleShot(100, self.generate_pdf_preview)

        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

        if parent and hasattr(parent, "geometry"):
            parent_rect = parent.geometry()
            x = parent_rect.x() + max(0, (parent_rect.width() - self.width()) // 2)
            y = parent_rect.y() + max(0, (parent_rect.height() - self.height()) // 2)
            self.move(x, y)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Frame
        header_frame = QFrame()
        header_frame.setObjectName("printHeaderFrame")
        header_frame.setFixedHeight(54)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(18, 10, 18, 10)
        h_layout.setSpacing(12)

        self.hdr_icon_lbl = QLabel()
        h_layout.addWidget(self.hdr_icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.title_lbl = QLabel("Print")
        self.title_lbl.setObjectName("printTitleText")
        
        display_url = self.page_url.replace("https://", "").replace("http://", "").rstrip("/")
        if len(display_url) > 50:
            display_url = display_url[:47] + "..."
        sub_text = f"{self.page_title} — {display_url}" if display_url else self.page_title
        if len(sub_text) > 70:
            sub_text = sub_text[:67] + "..."
        self.subtitle_lbl = QLabel(sub_text)
        self.subtitle_lbl.setObjectName("printSubtitleText")
        title_box.addWidget(self.title_lbl)
        title_box.addWidget(self.subtitle_lbl)
        h_layout.addLayout(title_box, 1)

        self.close_hdr_btn = QPushButton()
        self.close_hdr_btn.setObjectName("printHeaderCloseBtn")
        self.close_hdr_btn.setFixedSize(30, 30)
        self.close_hdr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_hdr_btn.clicked.connect(self.reject)
        h_layout.addWidget(self.close_hdr_btn)

        main_layout.addWidget(header_frame)

        # Split content
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Left Sidebar
        left_sidebar = QFrame()
        left_sidebar.setObjectName("printSidebar")
        left_sidebar.setFixedWidth(360)
        sidebar_layout = QVBoxLayout(left_sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("printScrollArea")
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        form_widget = QWidget()
        form_widget.setObjectName("printFormWidget")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(20, 16, 20, 16)
        form_layout.setSpacing(16)

        form_layout.addLayout(self._create_form_row("Destination", self._build_destination_combo()))
        form_layout.addLayout(self._create_form_row("Pages", self._build_pages_widget()))
        form_layout.addLayout(self._create_form_row("Copies", self._build_copies_widget()))
        form_layout.addLayout(self._create_form_row("Layout", self._build_layout_combo()))
        form_layout.addLayout(self._create_form_row("Color", self._build_color_combo()))

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("printRowSep")
        form_layout.addWidget(sep)

        self.more_settings_btn = QPushButton("More settings  ▼")
        self.more_settings_btn.setObjectName("moreSettingsBtn")
        self.more_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_settings_btn.clicked.connect(self._toggle_more_settings)
        form_layout.addWidget(self.more_settings_btn)

        self.more_settings_container = QWidget()
        self.more_settings_container.setObjectName("moreSettingsContainer")
        self.more_settings_container.hide()
        ms_layout = QVBoxLayout(self.more_settings_container)
        ms_layout.setContentsMargins(0, 4, 0, 4)
        ms_layout.setSpacing(14)

        ms_layout.addLayout(self._create_form_row("Paper size", self._build_paper_size_combo()))
        ms_layout.addLayout(self._create_form_row("Pages per sheet", self._build_pages_per_sheet_combo()))
        ms_layout.addLayout(self._create_form_row("Margins", self._build_margins_widget()))
        ms_layout.addLayout(self._create_form_row("Scale", self._build_scale_widget()))

        options_lbl = QLabel("Options")
        options_lbl.setObjectName("printFormLabel")
        ms_layout.addWidget(options_lbl)

        self.headers_footers_cb = QCheckBox("Headers and footers")
        self.headers_footers_cb.setObjectName("printCheckBox")
        self.headers_footers_cb.setChecked(True)
        self.headers_footers_cb.stateChanged.connect(self._on_setting_changed)
        ms_layout.addWidget(self.headers_footers_cb)

        self.bg_graphics_cb = QCheckBox("Background graphics")
        self.bg_graphics_cb.setObjectName("printCheckBox")
        self.bg_graphics_cb.setChecked(False)
        self.bg_graphics_cb.stateChanged.connect(self._on_setting_changed)
        ms_layout.addWidget(self.bg_graphics_cb)

        form_layout.addWidget(self.more_settings_container)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setObjectName("printRowSep")
        form_layout.addWidget(sep2)

        self.system_dialog_btn = QPushButton("Print using system dialog... (Ctrl+Shift+P)")
        self.system_dialog_btn.setObjectName("systemDialogBtn")
        self.system_dialog_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.system_dialog_btn.clicked.connect(self.open_system_dialog)
        form_layout.addWidget(self.system_dialog_btn)

        form_layout.addStretch(1)
        scroll_area.setWidget(form_widget)
        sidebar_layout.addWidget(scroll_area, 1)

        footer_frame = QFrame()
        footer_frame.setObjectName("printFooterFrame")
        footer_frame.setFixedHeight(64)
        f_layout = QHBoxLayout(footer_frame)
        f_layout.setContentsMargins(18, 12, 18, 12)
        f_layout.setSpacing(12)
        f_layout.addStretch(1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("printCancelBtn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedSize(90, 36)
        self.cancel_btn.clicked.connect(self.reject)
        f_layout.addWidget(self.cancel_btn)

        self.print_btn = QPushButton("Save")
        self.print_btn.setObjectName("printAcceptBtn")
        self.print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.print_btn.setFixedSize(90, 36)
        self.print_btn.clicked.connect(self._on_print_accepted)
        f_layout.addWidget(self.print_btn)

        sidebar_layout.addWidget(footer_frame)
        content_layout.addWidget(left_sidebar)

        # Right Preview Pane
        preview_pane = QFrame()
        preview_pane.setObjectName("printPreviewPane")
        preview_layout = QVBoxLayout(preview_pane)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("previewToolbar")
        toolbar.setFixedHeight(44)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 6, 16, 6)
        tb_layout.setSpacing(10)

        self.prev_page_btn = QPushButton()
        self.prev_page_btn.setObjectName("previewToolBtn")
        self.prev_page_btn.setFixedSize(28, 28)
        self.prev_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_page_btn.clicked.connect(self._prev_page)
        tb_layout.addWidget(self.prev_page_btn)

        self.page_indicator = QLabel("1 of 1")
        self.page_indicator.setObjectName("pageIndicatorLabel")
        tb_layout.addWidget(self.page_indicator)

        self.next_page_btn = QPushButton()
        self.next_page_btn.setObjectName("previewToolBtn")
        self.next_page_btn.setFixedSize(28, 28)
        self.next_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_page_btn.clicked.connect(self._next_page)
        tb_layout.addWidget(self.next_page_btn)

        tb_layout.addStretch(1)

        self.zoom_out_btn = QPushButton()
        self.zoom_out_btn.setObjectName("previewToolBtn")
        self.zoom_out_btn.setFixedSize(28, 28)
        self.zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        tb_layout.addWidget(self.zoom_out_btn)

        self.zoom_badge = QLabel("Fit")
        self.zoom_badge.setObjectName("zoomBadgeLabel")
        tb_layout.addWidget(self.zoom_badge)

        self.zoom_in_btn = QPushButton()
        self.zoom_in_btn.setObjectName("previewToolBtn")
        self.zoom_in_btn.setFixedSize(28, 28)
        self.zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        tb_layout.addWidget(self.zoom_in_btn)

        self.fit_width_btn = QPushButton("Fit width")
        self.fit_width_btn.setObjectName("zoomOptionBtn")
        self.fit_width_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fit_width_btn.clicked.connect(self._fit_width)
        tb_layout.addWidget(self.fit_width_btn)

        self.fit_page_btn = QPushButton("Fit page")
        self.fit_page_btn.setObjectName("zoomOptionBtn")
        self.fit_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fit_page_btn.clicked.connect(self._fit_page)
        tb_layout.addWidget(self.fit_page_btn)

        preview_layout.addWidget(toolbar)

        self.pdf_doc = QPdfDocument(self)
        self.pdf_view = QPdfView(self)
        self.pdf_view.setDocument(self.pdf_doc)
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.pdf_view.setObjectName("pdfPreviewWidget")

        preview_layout.addWidget(self.pdf_view, 1)

        content_layout.addWidget(preview_pane, 1)
        main_layout.addWidget(content_widget, 1)

    def _create_form_row(self, label_text, widget):
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label_text)
        lbl.setObjectName("printFormLabel")
        lbl.setFixedWidth(110)
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        return row

    def _build_destination_combo(self):
        self.dest_combo = QComboBox()
        self.dest_combo.setObjectName("printCombo")
        self.dest_combo.addItem("Save as PDF")
        
        printers = QPrinterInfo.availablePrinterNames()
        for p in printers:
            self.dest_combo.addItem(p)

        self.dest_combo.currentIndexChanged.connect(self._on_destination_changed)
        return self.dest_combo

    def _on_destination_changed(self, index):
        is_pdf = (self.dest_combo.currentText() == "Save as PDF")
        self.print_btn.setText("Save" if is_pdf else "Print")
        if hasattr(self, "copies_spin"):
            self.copies_spin.setEnabled(not is_pdf)
        self._on_setting_changed()

    def _build_pages_widget(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.pages_combo = QComboBox()
        self.pages_combo.setObjectName("printCombo")
        self.pages_combo.addItems(["All", "Odd pages only", "Even pages only", "Custom"])
        self.pages_combo.currentIndexChanged.connect(self._on_pages_combo_changed)
        layout.addWidget(self.pages_combo)

        self.custom_pages_input = QLineEdit()
        self.custom_pages_input.setObjectName("printInput")
        self.custom_pages_input.setPlaceholderText("e.g. 1-5, 8, 11-13")
        self.custom_pages_input.hide()
        self.custom_pages_input.textChanged.connect(self._on_setting_changed)
        layout.addWidget(self.custom_pages_input)

        return w

    def _on_pages_combo_changed(self, index):
        is_custom = (self.pages_combo.currentText() == "Custom")
        self.custom_pages_input.setVisible(is_custom)
        self._on_setting_changed()

    def _build_copies_widget(self):
        self.copies_spin = QSpinBox()
        self.copies_spin.setObjectName("printSpin")
        self.copies_spin.setRange(1, 99)
        self.copies_spin.setValue(1)
        self.copies_spin.setEnabled(False)
        return self.copies_spin

    def _build_layout_combo(self):
        self.orient_combo = QComboBox()
        self.orient_combo.setObjectName("printCombo")
        self.orient_combo.addItems(["Portrait", "Landscape"])
        self.orient_combo.currentIndexChanged.connect(self._on_setting_changed)
        return self.orient_combo

    def _build_color_combo(self):
        self.color_combo = QComboBox()
        self.color_combo.setObjectName("printCombo")
        self.color_combo.addItems(["Color", "Black and white"])
        self.color_combo.currentIndexChanged.connect(self._on_setting_changed)
        return self.color_combo

    def _build_paper_size_combo(self):
        self.paper_size_combo = QComboBox()
        self.paper_size_combo.setObjectName("printCombo")
        self.paper_sizes = {
            "A4": QPageSize.PageSizeId.A4,
            "Letter": QPageSize.PageSizeId.Letter,
            "Legal": QPageSize.PageSizeId.Legal,
            "Executive": QPageSize.PageSizeId.Executive,
            "A3": QPageSize.PageSizeId.A3,
            "A5": QPageSize.PageSizeId.A5,
            "B5": QPageSize.PageSizeId.B5,
            "Tabloid": QPageSize.PageSizeId.Tabloid,
        }
        for k in self.paper_sizes.keys():
            self.paper_size_combo.addItem(k)
        self.paper_size_combo.currentIndexChanged.connect(self._on_setting_changed)
        return self.paper_size_combo

    def _build_pages_per_sheet_combo(self):
        self.pages_per_sheet_combo = QComboBox()
        self.pages_per_sheet_combo.setObjectName("printCombo")
        self.pages_per_sheet_combo.addItems(["1", "2", "4", "6", "9", "16"])
        self.pages_per_sheet_combo.currentIndexChanged.connect(self._on_setting_changed)
        return self.pages_per_sheet_combo

    def _build_margins_widget(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.margins_combo = QComboBox()
        self.margins_combo.setObjectName("printCombo")
        self.margins_combo.addItems(["Default", "None", "Minimum", "Custom"])
        self.margins_combo.currentIndexChanged.connect(self._on_margins_combo_changed)
        layout.addWidget(self.margins_combo)

        self.custom_margins_widget = QWidget()
        self.custom_margins_widget.hide()
        cm_layout = QHBoxLayout(self.custom_margins_widget)
        cm_layout.setContentsMargins(0, 4, 0, 0)
        cm_layout.setSpacing(4)

        self.margin_top = QDoubleSpinBox()
        self.margin_top.setRange(0, 100)
        self.margin_top.setValue(10)
        self.margin_top.setSuffix("mm")
        self.margin_top.valueChanged.connect(self._on_setting_changed)

        self.margin_bottom = QDoubleSpinBox()
        self.margin_bottom.setRange(0, 100)
        self.margin_bottom.setValue(10)
        self.margin_bottom.setSuffix("mm")
        self.margin_bottom.valueChanged.connect(self._on_setting_changed)

        self.margin_left = QDoubleSpinBox()
        self.margin_left.setRange(0, 100)
        self.margin_left.setValue(10)
        self.margin_left.setSuffix("mm")
        self.margin_left.valueChanged.connect(self._on_setting_changed)

        self.margin_right = QDoubleSpinBox()
        self.margin_right.setRange(0, 100)
        self.margin_right.setValue(10)
        self.margin_right.setSuffix("mm")
        self.margin_right.valueChanged.connect(self._on_setting_changed)

        cm_layout.addWidget(self.margin_top)
        cm_layout.addWidget(self.margin_bottom)
        cm_layout.addWidget(self.margin_left)
        cm_layout.addWidget(self.margin_right)

        layout.addWidget(self.custom_margins_widget)
        return w

    def _on_margins_combo_changed(self, index):
        is_custom = (self.margins_combo.currentText() == "Custom")
        self.custom_margins_widget.setVisible(is_custom)
        self._on_setting_changed()

    def _build_scale_widget(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.scale_combo = QComboBox()
        self.scale_combo.setObjectName("printCombo")
        self.scale_combo.addItems(["Default (100%)", "Custom"])
        self.scale_combo.currentIndexChanged.connect(self._on_scale_combo_changed)
        layout.addWidget(self.scale_combo, 1)

        self.scale_spin = QSpinBox()
        self.scale_spin.setObjectName("printSpin")
        self.scale_spin.setRange(10, 200)
        self.scale_spin.setValue(100)
        self.scale_spin.setSuffix("%")
        self.scale_spin.hide()
        self.scale_spin.valueChanged.connect(self._on_setting_changed)
        layout.addWidget(self.scale_spin)

        return w

    def _on_scale_combo_changed(self, index):
        is_custom = (self.scale_combo.currentText() == "Custom")
        self.scale_spin.setVisible(is_custom)
        self._on_setting_changed()

    def _toggle_more_settings(self):
        is_hidden = self.more_settings_container.isHidden()
        if is_hidden:
            self.more_settings_container.show()
            self.more_settings_btn.setText("Fewer settings  ▲")
        else:
            self.more_settings_container.hide()
            self.more_settings_btn.setText("More settings  ▼")

    def _on_setting_changed(self):
        self.preview_timer.start(250)

    def get_configured_page_layout(self):
        paper_key = self.paper_size_combo.currentText() if hasattr(self, "paper_size_combo") else "A4"
        size_id = self.paper_sizes.get(paper_key, QPageSize.PageSizeId.A4)
        page_size = QPageSize(size_id)

        orient = QPageLayout.Orientation.Landscape if (hasattr(self, "orient_combo") and self.orient_combo.currentText() == "Landscape") else QPageLayout.Orientation.Portrait

        margin_type = self.margins_combo.currentText() if hasattr(self, "margins_combo") else "Default"
        if margin_type == "None":
            margins = QMarginsF(0, 0, 0, 0)
        elif margin_type == "Minimum":
            margins = QMarginsF(3, 3, 3, 3)
        elif margin_type == "Custom":
            margins = QMarginsF(self.margin_left.value(), self.margin_top.value(), self.margin_right.value(), self.margin_bottom.value())
        else:
            margins = QMarginsF(10, 10, 10, 10)

        return QPageLayout(page_size, orient, margins)

    def get_configured_page_ranges(self):
        pr = QPageRanges()
        if not hasattr(self, "pages_combo"):
            return pr

        mode = self.pages_combo.currentText()
        if mode == "Custom" and self.custom_pages_input.text().strip():
            text = self.custom_pages_input.text().strip()
            parts = text.split(",")
            for p in parts:
                p = p.strip()
                if "-" in p:
                    sub = p.split("-")
                    if len(sub) == 2 and sub[0].isdigit() and sub[1].isdigit():
                        pr.addRange(int(sub[0]), int(sub[1]))
                elif p.isdigit():
                    pr.addPage(int(p))
        return pr

    def generate_pdf_preview(self):
        if not self.web_page:
            return

        page_layout = self.get_configured_page_layout()
        page_ranges = self.get_configured_page_ranges()

        bg_graphics = self.bg_graphics_cb.isChecked() if hasattr(self, "bg_graphics_cb") else False
        self.web_page.settings().setAttribute(QWebEngineSettings.WebAttribute.PrintElementBackgrounds, bg_graphics)

        try:
            self.web_page.pdfPrintingFinished.disconnect(self._on_pdf_preview_generated)
        except Exception:
            pass

        self.web_page.pdfPrintingFinished.connect(self._on_pdf_preview_generated)
        self.web_page.printToPdf(self.temp_pdf_path, page_layout, page_ranges)

    def _on_pdf_preview_generated(self, file_path, success):
        if success and os.path.exists(file_path):
            self.pdf_doc.load(file_path)
            cnt = self.pdf_doc.pageCount()
            nav = self.pdf_view.pageNavigator()
            cur_page = nav.currentPage() + 1 if hasattr(nav, "currentPage") else 1
            self.page_indicator.setText(f"{cur_page} of {cnt}")

    def _prev_page(self):
        nav = self.pdf_view.pageNavigator()
        if nav and hasattr(nav, "jump"):
            cur = nav.currentPage()
            if cur > 0:
                nav.jump(cur - 1, QPointF(0, 0))
                self.page_indicator.setText(f"{cur} of {self.pdf_doc.pageCount()}")

    def _next_page(self):
        nav = self.pdf_view.pageNavigator()
        if nav and hasattr(nav, "jump"):
            cur = nav.currentPage()
            if cur < self.pdf_doc.pageCount() - 1:
                nav.jump(cur + 1, QPointF(0, 0))
                self.page_indicator.setText(f"{cur + 2} of {self.pdf_doc.pageCount()}")

    def _zoom_in(self):
        factor = self.pdf_view.zoomFactor() * 1.15
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(min(factor, 4.0))
        self.zoom_badge.setText(f"{int(round(self.pdf_view.zoomFactor() * 100))}%")

    def _zoom_out(self):
        factor = self.pdf_view.zoomFactor() / 1.15
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(max(factor, 0.25))
        self.zoom_badge.setText(f"{int(round(self.pdf_view.zoomFactor() * 100))}%")

    def _fit_width(self):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.zoom_badge.setText("Width")

    def _fit_page(self):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.zoom_badge.setText("Fit")

    def _on_print_accepted(self):
        dest = self.dest_combo.currentText()
        page_layout = self.get_configured_page_layout()
        page_ranges = self.get_configured_page_ranges()

        if dest == "Save as PDF":
            from PyQt6.QtWidgets import QFileDialog
            safe_title = "".join(c for c in self.page_title if c.isalnum() or c in (" ", "_", "-")).strip() or "WebPage"
            suggested = f"{safe_title}.pdf"
            file_path, _ = QFileDialog.getSaveFileName(self, "Save As PDF", suggested, "PDF Documents (*.pdf)")
            if file_path:
                def on_saved(path, success):
                    try:
                        self.web_page.pdfPrintingFinished.disconnect(on_saved)
                    except Exception:
                        pass
                    if success and self.parent_win and hasattr(self.parent_win, "show_browser_toast"):
                        self.parent_win.show_browser_toast(f"Saved PDF to '{os.path.basename(path)}'")
                
                self.web_page.pdfPrintingFinished.connect(on_saved)
                self.web_page.printToPdf(file_path, page_layout, page_ranges)
                self.accept()
        else:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPrinterName(dest)
            printer.setCopyCount(self.copies_spin.value())
            
            if self.color_combo.currentText() == "Color":
                printer.setColorMode(QPrinter.ColorMode.Color)
            else:
                printer.setColorMode(QPrinter.ColorMode.Monochrome)

            printer.setPageLayout(page_layout)

            def on_printed(success):
                if self.parent_win and hasattr(self.parent_win, "show_browser_toast"):
                    if success:
                        self.parent_win.show_browser_toast(f"Sent job to '{dest}'")
                    else:
                        self.parent_win.show_browser_toast("Printing failed or was cancelled", is_error=True)

            self.web_page.print(printer, on_printed)
            self.accept()

    def open_system_dialog(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.web_page.print(printer, lambda success: None)
            if self.parent_win and hasattr(self.parent_win, "show_browser_toast"):
                self.parent_win.show_browser_toast("Printing via system dialog...")
            self.accept()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        
    def update_styles(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        
        ic = c["icon_stroke"]
        close_icon = get_tinted_icon("assets/close.svg", ic, QSize(14, 14))
        back_icon = get_tinted_icon("assets/back.svg", ic, QSize(14, 14))
        forward_icon = get_tinted_icon("assets/forward.svg", ic, QSize(14, 14))
        minus_icon = get_tinted_icon("assets/minus.svg", ic, QSize(14, 14))
        plus_icon = get_tinted_icon("assets/plus.svg", ic, QSize(14, 14))
        print_hdr_icon = get_tinted_icon("assets/print.svg", c["accent_blue"], QSize(22, 22))

        if hasattr(self, "hdr_icon_lbl"):
            self.hdr_icon_lbl.setPixmap(print_hdr_icon.pixmap(QSize(22, 22)))

        self.close_hdr_btn.setIcon(close_icon)
        self.prev_page_btn.setIcon(back_icon)
        self.prev_page_btn.setText("")
        self.next_page_btn.setIcon(forward_icon)
        self.next_page_btn.setText("")
        self.zoom_out_btn.setIcon(minus_icon)
        self.zoom_out_btn.setText("")
        self.zoom_in_btn.setIcon(plus_icon)
        self.zoom_in_btn.setText("")

        self.setStyleSheet(f"""
            #tronPrintDialog {{
                background-color: {c['page_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 16px;
            }}
            #printHeaderFrame {{
                background-color: {c['card_bg']};
                border-bottom: 1px solid {c['card_border']};
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
            QLabel#printTitleText {{
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                font-size: 16px;
                font-weight: 700;
                color: {c['text_primary']};
            }}
            QLabel#printSubtitleText {{
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                font-size: 12px;
                color: {c['text_secondary']};
            }}
            QPushButton#printHeaderCloseBtn {{
                background: transparent;
                border: none;
                border-radius: 15px;
            }}
            QPushButton#printHeaderCloseBtn:hover {{
                background: {c['btn_hover']};
            }}
            #printSidebar {{
                background-color: {c['card_bg']};
                border-right: 1px solid {c['card_border']};
            }}
            #printScrollArea, #printFormWidget {{
                background: transparent;
            }}
            QLabel#printFormLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
                color: {c['text_primary']};
            }}
            QComboBox#printCombo, QSpinBox#printSpin, QDoubleSpinBox, QLineEdit#printInput {{
                background-color: {c['card_bg']};
                color: {c['text_primary']};
                border: 1px solid {c['card_border']};
                border-radius: 8px;
                padding: 6px 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }}
            QComboBox#printCombo QAbstractItemView {{
                background-color: {c['card_bg']};
                color: {c['text_primary']};
                selection-background-color: {c['btn_hover']};
                selection-color: {c['text_primary']};
                border: 1px solid {c['card_border']};
                border-radius: 6px;
            }}
            QComboBox#printCombo:hover, QSpinBox#printSpin:hover, QLineEdit#printInput:hover {{
                border-color: {c['accent_blue']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QCheckBox#printCheckBox {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {c['text_primary']};
                spacing: 8px;
            }}
            #printRowSep {{
                color: {c['card_border']};
                background-color: {c['card_border']};
                height: 1px;
                border: none;
                margin: 4px 0;
            }}
            QPushButton#moreSettingsBtn {{
                background: transparent;
                border: none;
                color: {c['accent_blue']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
                padding: 4px 0;
            }}
            QPushButton#moreSettingsBtn:hover {{
                text-decoration: underline;
            }}
            QPushButton#systemDialogBtn {{
                background: transparent;
                border: none;
                color: {c['accent_blue']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
                padding: 4px 0;
            }}
            QPushButton#systemDialogBtn:hover {{
                text-decoration: underline;
            }}
            #printFooterFrame {{
                background-color: {c['card_bg']};
                border-top: 1px solid {c['card_border']};
            }}
            QPushButton#printCancelBtn {{
                background: {c['card_bg']};
                color: {c['text_primary']};
                border: 1px solid {c['card_border']};
                border-radius: 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#printCancelBtn:hover {{
                background: {c['btn_hover']};
            }}
            QPushButton#printAcceptBtn {{
                background: {c['accent_blue']};
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#printAcceptBtn:hover {{
                opacity: 0.9;
            }}
            #printPreviewPane {{
                background-color: {'#181825' if is_dark else '#e2e8f0'};
            }}
            #previewToolbar {{
                background-color: {c['card_bg']};
                border-bottom: 1px solid {c['card_border']};
            }}
            QLabel#pageIndicatorLabel, QLabel#zoomBadgeLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                color: {c['text_primary']};
            }}
            QPushButton#previewToolBtn {{
                background: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 6px;
                color: {c['text_primary']};
            }}
            QPushButton#previewToolBtn:hover {{
                background: {c['btn_hover']};
                border-color: {c['accent_blue']};
            }}
            QPushButton#zoomOptionBtn {{
                background: {c['card_bg']};
                color: {c['text_primary']};
                border: 1px solid {c['card_border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#zoomOptionBtn:hover {{
                background: {c['btn_hover']};
                border-color: {c['accent_blue']};
            }}
            #pdfPreviewWidget {{
                background-color: {'#11111b' if is_dark else '#cbd5e1'};
            }}
        """)
        
        self.close_hdr_btn.setIcon(close_icon)


class TronWindow(QMainWindow):
    MARGIN = 6

    def __init__(self, is_pwa_mode=False, pwa_url=None, is_incognito=False):
        super().__init__()
        ico_file = resolve_resource("assets/app_icon.ico")
        if os.path.exists(ico_file):
            self.setWindowIcon(QIcon(ico_file))
        self.is_pwa_mode = is_pwa_mode
        self.pwa_url = pwa_url
        self.is_incognito = is_incognito
        self.current_tab_installable = False
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setMouseTracking(True)
        self.resize_pos = None

        if self.is_incognito:
            self.profile = QWebEngineProfile("IncognitoProfile", self)
            self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
            self.profile.setPersistentStoragePath("")
        else:
            self.profile = QWebEngineProfile("TronProfile", self)
        self.profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True)
        self.profile.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)

        self.MIN_WIDTH = 400
        self.MIN_HEIGHT = 300

        sm = SettingsManager.instance()
        saved_geo = sm.get("window_geometry", None)
        if saved_geo and isinstance(saved_geo, list) and len(saved_geo) == 4:
            x, y, w, h = saved_geo
            self.setGeometry(x, y, w, h)
            self._last_normal_geometry = QRect(x, y, w, h)
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            w, h = 1050, 680
            x = screen.center().x() - w // 2
            y = screen.center().y() - h // 2
            self._last_normal_geometry = QRect(x, y, w, h)
            self.setGeometry(x, y, w, h)

        self._should_maximize = sm.get("window_maximized", False)

        self.cursor_reset_timer = QTimer()
        self.cursor_reset_timer.setSingleShot(True)
        self.cursor_reset_timer.timeout.connect(self._reset_cursor_to_arrow)

        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setMouseTracking(True)
        self.setCentralWidget(self.container)

        self.browsers = []

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Tab Strip (Tabs + Caption Controls)
        self.tab_container = TabBarContainer(self)
        main_layout.addWidget(self.tab_container)

        # 2. Navigation Toolbar (Omnibox + Navigation)
        self.title_bar = TitleBar(self.container, self)
        main_layout.addWidget(self.title_bar)
        
        self.title_bar.back_btn.clicked.connect(self.go_back)
        self.title_bar.fwd_btn.clicked.connect(self.go_forward)
        self.title_bar.reload_btn.clicked.connect(self.reload_page)
        self.title_bar.home_btn.clicked.connect(self.go_home)
        self.title_bar.star_btn.clicked.connect(self.toggle_bookmark_current_page)
        if hasattr(self.title_bar, "reader_btn"):
            self.title_bar.reader_btn.clicked.connect(self.toggle_reader_mode)

        if self.is_pwa_mode:
            self.title_bar.hide()
            self.tab_container.set_pwa_mode(True, self.pwa_url or "Web App")

        # 3. Stacked Widget for Browser Views
        self.browser_stack = QStackedWidget()
        main_layout.addWidget(self.browser_stack, 1)

        # Native Toast Overlay
        self.toast_overlay = TronToastOverlay(self.container)

        self.drag_pos = None
        self.resizing = False
        self.resize_dir = None

        ThemeManager.instance().theme_changed.connect(self.update_theme_styles)
        self.update_theme_styles()

        # Pre-warm Chromium GPU compositor early in the window lifecycle so the
        # top-level DirectComposition swapchain is bound before the window is displayed.
        # This completely eliminates the first-navigation DWM compositor flicker/reload blink.
        self._warmup_engine = QWebEngineView(self.container)
        self._warmup_engine.setGeometry(0, 0, 1, 1)
        self._warmup_engine.lower()
        self._warmup_engine.show()

        if self.is_pwa_mode and self.pwa_url:
            self.add_new_tab(self.pwa_url)
        else:
            self.add_new_tab()

        self.profile.downloadRequested.connect(self.handle_download_requested)
        self.download_bubble = DownloadBubblePopup(self)
        
        self.title_bar.download_btn.clicked.connect(self.toggle_downloads_flyout)
        
        # Bottom-left floating link preview pill
        self.hover_link_label = QLabel(self)
        self.hover_link_label.setObjectName("hoverLinkLabel")
        self.hover_link_label.hide()
        
        tracker = DownloadTracker.instance()
        tracker.download_started.connect(self.on_download_started)
        tracker.download_completed.connect(self.on_download_completed)
        tracker.download_failed.connect(self.on_download_failed)
        self.tab_container.tab_context_menu_requested.connect(self.show_tab_context_menu)
        self.tab_container.tab_mute_requested.connect(self.toggle_tab_mute)

        # Tab Sleeping Background Timer
        self.tab_sleep_timer = QTimer(self)
        self.tab_sleep_timer.setInterval(30000)
        self.tab_sleep_timer.timeout.connect(self._check_tab_sleeping)
        self.tab_sleep_timer.start()

        # --- Register Global Keyboard Shortcuts ---
        self._init_keyboard_shortcuts()

    def _init_keyboard_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self, self.add_new_tab)
        QShortcut(QKeySequence("Ctrl+N"), self, lambda: TronWindow().show())
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, self.open_incognito_window)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.capture_screenshot)
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self.toggle_pip_video)
        QShortcut(QKeySequence("Ctrl+Alt+R"), self, self.toggle_reader_mode)
        QShortcut(QKeySequence("Ctrl+W"), self, lambda: self.close_tab(self.browser_stack.currentIndex()))
        QShortcut(QKeySequence("Ctrl+J"), self, self.open_downloads_page)
        QShortcut(QKeySequence("Ctrl+H"), self, self.open_history_page)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, self.open_bookmarks_page)
        QShortcut(QKeySequence("Ctrl+B"), self, self.open_bookmarks_page)
        QShortcut(QKeySequence("Ctrl+,"), self, self.open_settings_page)
        QShortcut(QKeySequence("Ctrl+Shift+L"), self, lambda: ThemeManager.instance().toggle_theme())
        QShortcut(QKeySequence("Ctrl+P"), self, self.print_page)
        QShortcut(QKeySequence("Ctrl+F"), self, self.show_find_bar)
        QShortcut(QKeySequence("Escape"), self, self._close_find_bar)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.reset_zoom)

    def open_incognito_window(self):
        incog_win = TronWindow(is_incognito=True)
        incog_win.show()

    def update_theme_styles(self):
        c = ThemeManager.instance().colors()
        is_dark = ThemeManager.instance().is_dark()
        container_border = "1px solid rgba(147, 197, 253, 0.6)" if not is_dark else f"1px solid {c['card_border']}"
        self.container.setStyleSheet(f"""
            #container {{
                background: {c['page_bg']};
                border: {container_border};
            }}
            {ThemeManager.instance().scrollbar_style()}
        """)
        self.browser_stack.setStyleSheet(f"background: {c['page_bg']}; border: none;")
        if hasattr(self, "hover_link_label"):
            self.hover_link_label.setStyleSheet(f"""
                QLabel#hoverLinkLabel {{
                    background: {c['menu_bg']};
                    color: {c['text_primary']};
                    border: 1px solid {c['card_border']};
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 11.5px;
                }}
            """)
        if hasattr(self, "title_bar"):
            self.title_bar.update_theme_styles()

    def add_new_tab(self, url=None, skip_default_load=False):
        if isinstance(url, bool):
            url = None
        behavior = SettingsManager.instance().get("startup_behavior", "home")
        is_new_tab = (url in ("tron://newtab", "tron://home", "about:newtab")) or (url is None and not skip_default_load and behavior == "home")
        if is_new_tab:
            page = NewTabPage(self)
            self.browsers.append(page)
            self.browser_stack.addWidget(page)
            index = self.tab_container.add_tab("New Tab")
            self.tab_container.set_tab_icon(index, QIcon(resolve_resource("assets/app_icon.png")))
            self.switch_tab(index)
            self.title_bar.url_bar.clear()
            self.title_bar.url_bar.setPlaceholderText("Search Google or type a URL")
            self.title_bar.search_icon.show()
            self.title_bar.lock_icon.hide()
            return page

        c = ThemeManager.instance().colors()
        browser = QWebEngineView()
        page = TronPage(self.profile, browser)
        page.setBackgroundColor(parse_color(c["page_bg"]))
        browser.setPage(page)
        page.linkHovered.connect(lambda u, b=browser: self._on_link_hovered(u, b))
        
        browser._last_active_time = time.time()
        browser._is_sleeping = False
        browser._saved_url = url or ""
        browser._saved_title = "New Tab"
        
        if hasattr(page, "permissionRequested"):
            page.permissionRequested.connect(self.handle_permission_requested)
        page.featurePermissionRequested.connect(self.handle_permission_requested)
        if hasattr(page, "printRequested"):
            page.printRequested.connect(self.print_page)
        if hasattr(page, "renderProcessTerminated"):
            page.renderProcessTerminated.connect(
                lambda status, exit_code, b=browser: self._on_render_process_terminated(status, exit_code, b)
            )
        
        overlay = ZoomOverlay(browser)
        browser._zoom_overlay = overlay
        browser._zoom_filter = ZoomEventFilter(browser, self)
        
        self.browsers.append(browser)
        self.browser_stack.addWidget(browser)
        
        index = self.tab_container.add_tab("New Tab")
        self.switch_tab(index)

        browser.urlChanged.connect(lambda qurl, b=browser: self._on_url_changed(qurl, b))
        browser.titleChanged.connect(lambda title, b=browser: self._on_title_changed(title, b))
        browser.loadProgress.connect(lambda progress, b=browser: self._on_load_progress(progress, b))
        browser.loadStarted.connect(lambda b=browser: self._on_load_started(b))
        browser.loadFinished.connect(lambda ok, b=browser: self._on_load_finished(ok, b))
        browser.iconChanged.connect(lambda icon, b=browser: self._on_icon_changed(icon, b))
        
        if hasattr(browser.page(), "recentlyAudibleChanged"):
            browser.page().recentlyAudibleChanged.connect(lambda audible, b=browser: self._on_recently_audible_changed(audible, b))

        if url:
            browser.setUrl(QUrl(url))
        elif not skip_default_load:
            behavior = SettingsManager.instance().get("startup_behavior", "home")
            if behavior == "blank":
                browser.setUrl(QUrl("about:blank"))
            elif behavior == "custom":
                custom_url = SettingsManager.instance().get("custom_startup_url", "https://tronexplorer.netlify.app/")
                if not custom_url.startswith("http"):
                    custom_url = "https://" + custom_url
                browser.setUrl(QUrl(custom_url))
            else:
                browser.setUrl(QUrl("https://tronexplorer.netlify.app/"))

        return browser

    def navigate_from_newtab(self, newtab_page, target_url):
        if newtab_page in self.browsers:
            index = self.browsers.index(newtab_page)
            self._convert_custom_tab_to_webengine(index, target_url)
        else:
            self.add_new_tab(target_url)

    def _convert_custom_tab_to_webengine(self, index, target_url):
        if not (0 <= index < len(self.browsers)):
            self.add_new_tab(target_url)
            return

        old_widget = self.browsers[index]
        c = ThemeManager.instance().colors()

        browser = QWebEngineView()
        page = TronPage(self.profile, browser)
        page.setBackgroundColor(parse_color(c["page_bg"]))
        browser.setPage(page)
        page.linkHovered.connect(lambda u, b=browser: self._on_link_hovered(u, b))

        browser._last_active_time = time.time()
        browser._is_sleeping = False
        url_str = target_url.toString() if isinstance(target_url, QUrl) else target_url
        browser._saved_url = url_str
        browser._saved_title = "Loading..."

        if hasattr(page, "permissionRequested"):
            page.permissionRequested.connect(self.handle_permission_requested)
        page.featurePermissionRequested.connect(self.handle_permission_requested)
        if hasattr(page, "printRequested"):
            page.printRequested.connect(self.print_page)
        if hasattr(page, "renderProcessTerminated"):
            page.renderProcessTerminated.connect(
                lambda status, exit_code, b=browser: self._on_render_process_terminated(status, exit_code, b)
            )

        overlay = ZoomOverlay(browser)
        browser._zoom_overlay = overlay
        browser._zoom_filter = ZoomEventFilter(browser, self)

        # Connect all signals first
        browser.urlChanged.connect(lambda qurl, b=browser: self._on_url_changed(qurl, b))
        browser.titleChanged.connect(lambda title, b=browser: self._on_title_changed(title, b))
        browser.loadProgress.connect(lambda progress, b=browser: self._on_load_progress(progress, b))
        browser.loadFinished.connect(lambda ok, b=browser: self._on_load_finished(ok, b))
        browser.iconChanged.connect(lambda icon, b=browser: self._on_icon_changed(icon, b))
        if hasattr(browser.page(), "recentlyAudibleChanged"):
            browser.page().recentlyAudibleChanged.connect(lambda audible, b=browser: self._on_recently_audible_changed(audible, b))

        # Connect loadStarted to tab loading spinner before initiating load
        browser.loadStarted.connect(lambda b=browser: self._on_load_started(b))

        # ── Truly atomic and seamless widget transition ───────────────────────
        # Insert new browser at the target index BEFORE removing the old widget.
        # This guarantees the stacked widget is never empty (count > 0 at all times),
        # preventing black/white layout dropouts or reload blinks.
        self.browsers[index] = browser
        self.browser_stack.insertWidget(index, browser)
        self.browser_stack.setCurrentWidget(browser)
        self.browser_stack.removeWidget(old_widget)
        old_widget.hide()
        old_widget.deleteLater()

        url_obj = target_url if isinstance(target_url, QUrl) else QUrl(target_url)
        browser.setUrl(url_obj)
        self.title_bar.url_bar.setText(url_str)
        self.tab_container.set_tab_loading(index, True)
        self.tab_container.set_tab_title(index, "Loading...")


    def open_new_tab_page(self):
        self._open_custom_page(NewTabPage, "tron://newtab", "New Tab", "assets/app_icon.png")

    def navigate_internal_url(self, url_str):
        if url_str in ("tron://newtab", "tron://home"):
            self.open_new_tab_page()
        elif url_str == "tron://downloads":
            self.open_downloads_page()
        elif url_str == "tron://bookmarks":
            self.open_bookmarks_page()
        elif url_str == "tron://history":
            self.open_history_page()
        elif url_str == "tron://settings":
            self.open_settings_page()
        elif url_str == "tron://about":
            self.open_about_page()

    def show_zoom_toast(self, factor):
        if not hasattr(self, "zoom_toast") or not self.zoom_toast:
            self.zoom_toast = ZoomOverlay(self)
        self.zoom_toast.show_zoom(factor)
        toast_w = self.zoom_toast.width()
        x = (self.width() - toast_w) // 2
        y = 96
        self.zoom_toast.move(x, y)
        self.zoom_toast.raise_()

    def zoom_in(self):
        curr = self.browser_stack.currentWidget()
        if not curr:
            return
        current_val = curr.zoomFactor() if hasattr(curr, "zoomFactor") else 1.0
        new_val = min(round(current_val + 0.1, 2), 3.0)
        if hasattr(curr, "setZoomFactor"):
            curr.setZoomFactor(new_val)
        self.show_zoom_toast(new_val)

    def zoom_out(self):
        curr = self.browser_stack.currentWidget()
        if not curr:
            return
        current_val = curr.zoomFactor() if hasattr(curr, "zoomFactor") else 1.0
        new_val = max(round(current_val - 0.1, 2), 0.3)
        if hasattr(curr, "setZoomFactor"):
            curr.setZoomFactor(new_val)
        self.show_zoom_toast(new_val)

    def reset_zoom(self):
        curr = self.browser_stack.currentWidget()
        if not curr:
            return
        if hasattr(curr, "setZoomFactor"):
            curr.setZoomFactor(1.0)
        self.show_zoom_toast(1.0)

    def toggle_downloads_flyout(self):
        if hasattr(self, "download_bubble"):
            self.download_bubble.toggle_bubble()
        else:
            self.open_downloads_page()

    def _on_link_hovered(self, url, browser):
        if browser != self.browser_stack.currentWidget():
            return
        if not hasattr(self, "hover_link_label"):
            return
        if not url:
            self.hover_link_label.hide()
        else:
            metrics = self.hover_link_label.fontMetrics()
            elided = metrics.elidedText(url, Qt.TextElideMode.ElideMiddle, max(140, self.width() // 2))
            self.hover_link_label.setText(elided)
            self.hover_link_label.adjustSize()
            h = self.hover_link_label.height()
            self.hover_link_label.move(14, self.height() - h - 14)
            self.hover_link_label.show()
            self.hover_link_label.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "hover_link_label") and self.hover_link_label.isVisible():
            h = self.hover_link_label.height()
            self.hover_link_label.move(14, self.height() - h - 14)

    def handle_permission_requested(self, *args):
        page = self.sender()
        current_browser = None
        for browser in self.browsers:
            if hasattr(browser, "page") and browser.page() == page:
                current_browser = browser
                break
        
        if not current_browser:
            current_browser = self.browser_stack.currentWidget()
            
        if current_browser:
            popup = PermissionPopup(current_browser, *args)
            popup.show_prompt()

    def close_tab(self, index):
        if self.tab_container.count() <= 1:
            self.close()
            return
            
        if 0 <= index < len(self.browsers):
            widget = self.browsers[index]
            self.browser_stack.removeWidget(widget)
            self.browsers.remove(widget)

            if isinstance(widget, QWebEngineView):
                widget.stop()
                widget.setUrl(QUrl("about:blank"))
            widget.deleteLater()
            
            self.tab_container.remove_tab(index)
            
            new_index = min(index, self.tab_container.count() - 1)
            if new_index >= 0:
                self.tab_container.set_active(new_index)
                self.switch_tab(new_index)

    def swap_browser_tabs(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.browsers) and 0 <= to_idx < len(self.browsers):
            self.browsers[from_idx], self.browsers[to_idx] = self.browsers[to_idx], self.browsers[from_idx]
            for browser in self.browsers:
                self.browser_stack.removeWidget(browser)
            for i, browser in enumerate(self.browsers):
                self.browser_stack.insertWidget(i, browser)
            active_idx = self.tab_container._active_index
            if 0 <= active_idx < len(self.browsers):
                self.switch_tab(active_idx)

    # --- Internal Page Loaders ---
    def open_downloads_page(self):
        self._open_custom_page(DownloadsPage, "tron://downloads", "Downloads", "assets/download.svg")

    def open_bookmarks_page(self):
        self._open_custom_page(BookmarksPage, "tron://bookmarks", "Bookmarks", "assets/bookmark.svg")

    def open_history_page(self):
        self._open_custom_page(HistoryPage, "tron://history", "History", "assets/history.svg")

    def open_settings_page(self):
        self._open_custom_page(SettingsPage, "tron://settings", "Settings", "assets/settings.svg")

    def open_about_page(self):
        self._open_custom_page(AboutPage, "tron://about", "About Tron", "assets/info.svg")

    def _open_custom_page(self, page_cls, url_str, tab_title, icon_path):
        for i, browser in enumerate(self.browsers):
            if isinstance(browser, page_cls):
                self.tab_container.set_active(i)
                self.browser_stack.setCurrentIndex(i)
                self.title_bar.url_bar.setText(url_str)
                return
                
        page = page_cls(self)
        self.browsers.append(page)
        index = self.browser_stack.addWidget(page)
        tab_idx = self.tab_container.add_tab(tab_title)
        
        self.tab_container.set_tab_icon(tab_idx, QIcon(icon_path))
        self.tab_container.set_active(tab_idx)
        self.browser_stack.setCurrentIndex(index)
        self.title_bar.url_bar.setText(url_str)

    def update_bookmark_star_state(self):
        current_browser = self.browser_stack.currentWidget()
        if isinstance(current_browser, QWebEngineView):
            url = current_browser.url().toString()
            is_bm = BookmarkManager.instance().is_bookmarked(url)
            self.title_bar.set_bookmark_star_active(is_bm)
        else:
            self.title_bar.set_bookmark_star_active(False)

    def toggle_bookmark_current_page(self):
        current_browser = self.browser_stack.currentWidget()
        if isinstance(current_browser, QWebEngineView):
            url = current_browser.url().toString()
            title = current_browser.title() or url
            added = BookmarkManager.instance().toggle_bookmark(title, url)
            if added:
                self.show_browser_toast(f"Bookmarked '{title[:25]}'")
            else:
                self.show_browser_toast("Removed bookmark")
            self.update_bookmark_star_state()

    def handle_download_requested(self, download):
        sm = SettingsManager.instance()
        default_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        configured_dir = sm.get("download_dir", default_dir)
        
        if not configured_dir or not os.path.exists(configured_dir):
            configured_dir = default_dir
            
        downloads_dir = configured_dir
        suggested_name = download.suggestedFileName()
        
        always_ask = sm.get("ask_download_dir", False)
        
        if always_ask:
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File As",
                os.path.join(downloads_dir, suggested_name),
                "All Files (*.*)"
            )
            if not file_path:
                download.cancel()
                return
            downloads_dir = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
        else:
            filename = suggested_name

        target_path = os.path.join(downloads_dir, filename)
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception as e:
                print(f"File replace cleanup warning: {e}")

        try:
            import shutil
            usage = shutil.disk_usage(downloads_dir)
            if download.totalBytes() > 0 and download.totalBytes() > usage.free:
                self.show_browser_toast("Warning: Insufficient disk space for this download!", is_error=True)
        except Exception as e:
            print(f"Disk space check error: {e}")

        download.setDownloadDirectory(downloads_dir)
        download.setDownloadFileName(filename)
        download.accept()
        
        self.title_bar.download_btn.show()
        DownloadTracker.instance().add_download(download)
        
        if len(DownloadTracker.instance().downloads) > 0:
            recent_item = DownloadTracker.instance().downloads[0]
            self.download_bubble.show_for_item(recent_item)

    def on_download_started(self, filename):
        self.title_bar.download_btn.show()
        self.update_download_button_state()
        self.show_browser_toast(f"Started downloading: {filename}")

    def on_download_completed(self, filename):
        self.update_download_button_state()
        self.show_browser_toast(f"Download completed: {filename}")

    def on_download_failed(self, filename):
        self.update_download_button_state()
        self.show_browser_toast(f"Download failed: {filename}", is_error=True)

    def update_download_button_state(self):
        tracker = DownloadTracker.instance()
        self.title_bar.download_btn.set_progress(tracker.get_overall_progress())
        self.title_bar.download_btn.set_active(tracker.is_any_downloading())
        self.title_bar.update_toolbar_button_visibility()

    # =====================================================================
    # TAB CRASH PROTECTION & RECOVERY
    # =====================================================================
    def _on_render_process_terminated(self, status, exit_code, browser):
        from PyQt6.QtWebEngineCore import QWebEnginePage
        if status == QWebEnginePage.RenderProcessTerminationStatus.NormalTerminationStatus:
            return

        status_name = "Crashed"
        if status == QWebEnginePage.RenderProcessTerminationStatus.KilledTerminationStatus:
            status_name = "Killed"
        elif status == QWebEnginePage.RenderProcessTerminationStatus.AbnormalTerminationStatus:
            status_name = "Abnormal Exit"

        print(f"[Tron Crash Protection] Tab process terminated: {status_name} (code: {exit_code})")

        crashed_url = getattr(browser, "_saved_url", "")
        if not crashed_url or crashed_url == "about:blank":
            try:
                crashed_url = browser.url().toString()
            except Exception:
                crashed_url = "https://tronexplorer.netlify.app/"

        browser._last_crashed_url = crashed_url

        if hasattr(self, "show_browser_toast"):
            self.show_browser_toast(f"Tab process crashed ({status_name}). Recovered cleanly!", is_error=True)

        new_page = TronPage(self.profile, browser)
        new_page.setBackgroundColor(Qt.GlobalColor.transparent)

        if hasattr(new_page, "permissionRequested"):
            new_page.permissionRequested.connect(self.handle_permission_requested)
        new_page.featurePermissionRequested.connect(self.handle_permission_requested)
        if hasattr(new_page, "printRequested"):
            new_page.printRequested.connect(self.print_page)

        new_page.renderProcessTerminated.connect(
            lambda s, c, b=browser: self._on_render_process_terminated(s, c, b)
        )

        browser.setPage(new_page)

        c = ThemeManager.instance().colors()
        crash_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Aw, Snap! — Tab Crashed</title>
            <style>
                body {{
                    background-color: {c['page_bg']};
                    color: {c['text_primary']};
                    font-family: 'Segoe UI', Roboto, Helvetica, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    padding: 20px;
                    box-sizing: border-box;
                }}
                .card {{
                    background-color: {c['card_bg']};
                    border: 1px solid {c['card_border']};
                    border-radius: 16px;
                    padding: 40px 48px;
                    max-width: 500px;
                    width: 100%;
                    box-shadow: 0 12px 32px rgba(0,0,0,0.15);
                    text-align: left;
                }}
                .icon {{
                    font-size: 44px;
                    margin-bottom: 16px;
                }}
                h1 {{
                    font-size: 24px;
                    font-weight: 700;
                    margin: 0 0 10px 0;
                    color: {c['text_primary']};
                }}
                p {{
                    font-size: 14px;
                    color: {c['text_secondary']};
                    line-height: 1.6;
                    margin: 0 0 24px 0;
                }}
                .err-code {{
                    font-family: monospace;
                    font-size: 12px;
                    background: {c['btn_bg']};
                    padding: 4px 8px;
                    border-radius: 6px;
                    display: inline-block;
                    margin-bottom: 24px;
                    color: {c['text_secondary']};
                }}
                .actions {{
                    display: flex;
                    gap: 12px;
                }}
                .btn {{
                    background-color: {c['accent_blue']};
                    color: #ffffff;
                    border: none;
                    border-radius: 10px;
                    padding: 10px 22px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                    transition: opacity 0.2s;
                }}
                .btn:hover {{
                    opacity: 0.9;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">🙁</div>
                <h1>Aw, Snap!</h1>
                <p>Something went wrong while displaying this web page. The web tab process terminated unexpectedly, but Tron Browser protected your other tabs.</p>
                <div class="err-code">Error Code: {status_name.upper()}_CODE_{exit_code}</div>
                <div class="actions">
                    <button class="btn" onclick="location.href='{crashed_url}'">Reload Tab</button>
                </div>
            </div>
        </body>
        </html>
        """
        browser.setHtml(crash_html, QUrl(crashed_url))

    # =====================================================================
    # PRINT PAGE
    # =====================================================================
    def print_page(self):
        current_browser = self.browser_stack.currentWidget()
        if isinstance(current_browser, QWebEngineView):
            page_title = current_browser.title() or "Web Page"
            page_url = current_browser.url().toString()
            dialog = TronPrintDialog(web_page=current_browser.page(), page_title=page_title, page_url=page_url, parent=self)
            dialog.exec()
        else:
            self.show_browser_toast("Cannot print internal pages", is_error=True)


    # =====================================================================
    # FIND IN PAGE
    # =====================================================================
    def show_find_bar(self):
        current_browser = self.browser_stack.currentWidget()
        if not isinstance(current_browser, QWebEngineView):
            self.show_browser_toast("Find is only available on web pages", is_error=True)
            return

        if hasattr(self, "_find_bar") and self._find_bar and self._find_bar.isVisible():
            self._find_input.setFocus()
            self._find_input.selectAll()
            return

        c = ThemeManager.instance().colors()

        self._find_bar = QFrame(self)
        self._find_bar.setObjectName("findBar")
        self._find_bar.setStyleSheet(f"""
            #findBar {{
                background: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
            }}
            QLineEdit {{
                background: {c['btn_bg']};
                color: {c['text_primary']};
                border: 1px solid {c['card_border']};
                border-radius: 8px;
                padding: 6px 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {c['accent_blue']};
            }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px;
            }}
            QPushButton:hover {{
                background: {c['btn_hover']};
            }}
            QLabel {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }}
        """)

        bar_layout = QHBoxLayout(self._find_bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)
        bar_layout.setSpacing(6)

        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("Find in page...")
        self._find_input.setFixedWidth(220)
        self._find_input.textChanged.connect(self._find_text)
        self._find_input.returnPressed.connect(self._find_next)
        bar_layout.addWidget(self._find_input)

        self._find_count_label = QLabel("")
        self._find_count_label.setFixedWidth(70)
        bar_layout.addWidget(self._find_count_label)

        ic = c["icon_stroke"]
        prev_btn = QPushButton()
        prev_btn.setIcon(get_tinted_icon("assets/back.svg", ic, QSize(16, 16)))
        prev_btn.setFixedSize(28, 28)
        prev_btn.setToolTip("Previous match")
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.clicked.connect(self._find_prev)
        bar_layout.addWidget(prev_btn)

        next_btn = QPushButton()
        next_btn.setIcon(get_tinted_icon("assets/forward.svg", ic, QSize(16, 16)))
        next_btn.setFixedSize(28, 28)
        next_btn.setToolTip("Next match")
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.clicked.connect(self._find_next)
        bar_layout.addWidget(next_btn)

        close_btn = QPushButton()
        close_btn.setIcon(get_tinted_icon("assets/close.svg", ic, QSize(16, 16)))
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("Close find bar")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._close_find_bar)
        bar_layout.addWidget(close_btn)

        self._find_bar.adjustSize()
        bar_w = self._find_bar.sizeHint().width()
        top_offset = (self.tab_container.height() if hasattr(self, "tab_container") and self.tab_container.isVisible() else 0) + (self.title_bar.height() if hasattr(self, "title_bar") and self.title_bar.isVisible() else 0)
        self._find_bar.move(self.width() - bar_w - 20, top_offset + 8)
        self._find_bar.show()
        self._find_input.setFocus()

    def _find_text(self, text):
        current_browser = self.browser_stack.currentWidget()
        if isinstance(current_browser, QWebEngineView):
            if text:
                def on_result(result):
                    count = result.numberOfMatches() if hasattr(result, 'numberOfMatches') else 0
                    active = result.activeMatch() if hasattr(result, 'activeMatch') else 0
                    if count > 0:
                        self._find_count_label.setText(f"{active}/{count}")
                    else:
                        self._find_count_label.setText("No matches")
                current_browser.findText(text, QWebEnginePage.FindFlag(0), on_result)
            else:
                current_browser.findText("")
                self._find_count_label.setText("")

    def _find_next(self):
        if hasattr(self, "_find_input") and self._find_input.text():
            current_browser = self.browser_stack.currentWidget()
            if isinstance(current_browser, QWebEngineView):
                def on_result(result):
                    count = result.numberOfMatches() if hasattr(result, 'numberOfMatches') else 0
                    active = result.activeMatch() if hasattr(result, 'activeMatch') else 0
                    if count > 0:
                        self._find_count_label.setText(f"{active}/{count}")
                current_browser.findText(self._find_input.text(), QWebEnginePage.FindFlag(0), on_result)

    def _find_prev(self):
        if hasattr(self, "_find_input") and self._find_input.text():
            current_browser = self.browser_stack.currentWidget()
            if isinstance(current_browser, QWebEngineView):
                def on_result(result):
                    count = result.numberOfMatches() if hasattr(result, 'numberOfMatches') else 0
                    active = result.activeMatch() if hasattr(result, 'activeMatch') else 0
                    if count > 0:
                        self._find_count_label.setText(f"{active}/{count}")
                current_browser.findText(self._find_input.text(), QWebEnginePage.FindFlag.FindBackward, on_result)

    def _close_find_bar(self):
        if hasattr(self, "_find_bar") and self._find_bar and self._find_bar.isVisible():
            current_browser = self.browser_stack.currentWidget()
            if isinstance(current_browser, QWebEngineView):
                current_browser.findText("")
            self._find_bar.hide()
            self._find_bar.deleteLater()
            self._find_bar = None

    def capture_screenshot(self):
        current_browser = self.browser_stack.currentWidget()
        if isinstance(current_browser, QWebEngineView):
            pixmap = current_browser.grab()
            pictures_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
            os.makedirs(pictures_dir, exist_ok=True)
            import time
            filename = f"Tron_Screenshot_{int(time.time())}.png"
            file_path = os.path.join(pictures_dir, filename)
            pixmap.save(file_path, "PNG")
            
            QApplication.clipboard().setPixmap(pixmap)
            self.show_browser_toast("Screenshot saved to Pictures & copied to Clipboard!")
        else:
            self.show_browser_toast("Cannot capture screenshot of internal page", is_error=True)

    def toggle_pip_video(self):
        current_browser = self.browser_stack.currentWidget()
        if isinstance(current_browser, QWebEngineView):
            js = """
                (function() {
                    const v = document.querySelector('video');
                    if (v) {
                        if (document.pictureInPictureElement) {
                            document.exitPictureInPicture();
                            return "EXITED";
                        } else {
                            v.requestPictureInPicture();
                            return "ENTERED";
                        }
                    }
                    return "NO_VIDEO";
                })()
            """
            def on_result(res):
                if res == "ENTERED":
                    self.show_browser_toast("Picture-in-Picture Video Player activated!")
                elif res == "EXITED":
                    self.show_browser_toast("Exited Picture-in-Picture mode")
                else:
                    self.show_browser_toast("No HTML5 video element found on this page", is_error=True)
            current_browser.page().runJavaScript(js, on_result)
        else:
            self.show_browser_toast("Picture-in-Picture is only available on web pages", is_error=True)

    def toggle_reader_mode(self):
        current_browser = self.browser_stack.currentWidget()
        if isinstance(current_browser, QWebEngineView):
            js = """
                (function() {
                    if (window._tronReaderActive) {
                        location.reload();
                        return "EXITED";
                    }
                    const mainElem = document.querySelector('article') || document.querySelector('main') || document.body;
                    if (mainElem) {
                        window._tronReaderActive = true;
                        const title = document.title || "Article";
                        const content = mainElem.innerHTML;
                        const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                        const text = isDark ? "#cdd6f4" : "#222222";
                        const cardBg = isDark ? "#1e1e2e" : "#ffffff";
                        
                        document.body.innerHTML = `
                            <div style="max-width: 740px; margin: 40px auto; font-family: 'Georgia', serif; font-size: 19px; line-height: 1.8; color: ${text}; background: ${cardBg}; padding: 48px; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.12);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid rgba(128,128,128,0.2); padding-bottom: 16px;">
                                    <span style="font-family: sans-serif; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #2563eb;">📖 Reader Mode</span>
                                    <button onclick="location.reload()" style="padding: 6px 16px; background: #2563eb; color: #ffffff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Exit Reader</button>
                                </div>
                                <h1 style="font-size: 32px; font-weight: 700; margin-bottom: 24px; font-family: sans-serif;">${title}</h1>
                                <div>${content}</div>
                            </div>
                        `;
                        return "ENTERED";
                    }
                    return "NO_ARTICLE";
                })()
            """
            def on_result(res):
                if res == "ENTERED":
                    self.show_browser_toast("Reader Mode activated!")
                elif res == "EXITED":
                    self.show_browser_toast("Exited Reader Mode")
                else:
                    self.show_browser_toast("Could not extract readable article content", is_error=True)
            current_browser.page().runJavaScript(js, on_result)
        else:
            self.show_browser_toast("Reader Mode is only available on web pages", is_error=True)

    def show_browser_toast(self, message, is_error=False):
        if hasattr(self, "toast_overlay"):
            self.toast_overlay.show_message(message, is_error=is_error)

    def switch_tab(self, index):
        if 0 <= index < len(self.browsers):
            self.tab_container.set_active(index)
            self.browser_stack.setCurrentIndex(index)
            current_browser = self.browsers[index]
            if current_browser:
                current_browser._last_active_time = time.time()
                if getattr(current_browser, "_is_sleeping", False):
                    self.wake_tab(index)
                    return

                if isinstance(current_browser, DownloadsPage):
                    self.title_bar.url_bar.setText("tron://downloads")
                    self.title_bar.search_icon.show()
                    self.title_bar.lock_icon.hide()
                    return
                elif isinstance(current_browser, BookmarksPage):
                    self.title_bar.url_bar.setText("tron://bookmarks")
                    self.title_bar.search_icon.show()
                    self.title_bar.lock_icon.hide()
                    return
                elif isinstance(current_browser, HistoryPage):
                    self.title_bar.url_bar.setText("tron://history")
                    self.title_bar.search_icon.show()
                    self.title_bar.lock_icon.hide()
                    return
                elif isinstance(current_browser, SettingsPage):
                    self.title_bar.url_bar.setText("tron://settings")
                    self.title_bar.search_icon.show()
                    self.title_bar.lock_icon.hide()
                    return
                elif isinstance(current_browser, AboutPage):
                    self.title_bar.url_bar.setText("tron://about")
                    self.title_bar.search_icon.show()
                    self.title_bar.lock_icon.hide()
                    return
                elif isinstance(current_browser, NewTabPage):
                    self.title_bar.url_bar.clear()
                    self.title_bar.url_bar.setPlaceholderText("Search Google or type a URL")
                    self.title_bar.search_icon.show()
                    self.title_bar.lock_icon.hide()
                    return

                if hasattr(current_browser, "url"):
                    url = current_browser.url().toString()
                    if 'tronexplorer.netlify.app' in url or 'novaaisearch.netlify.app' in url or not url or url == 'about:blank':
                        self.title_bar.url_bar.clear()
                        self.title_bar.search_icon.show()
                        self.title_bar.lock_icon.hide()
                    else:
                        self.title_bar.url_bar.setText(url)
                        self.title_bar.search_icon.hide()
                        self.title_bar.lock_icon.show()
                self.update_bookmark_star_state()

    def go_back(self):
        current_browser = self.browser_stack.currentWidget()
        if hasattr(current_browser, "back"):
            current_browser.back()

    def go_forward(self):
        current_browser = self.browser_stack.currentWidget()
        if hasattr(current_browser, "forward"):
            current_browser.forward()

    def reload_page(self):
        current_browser = self.browser_stack.currentWidget()
        if hasattr(current_browser, "reload"):
            icon_path = self.title_bar.reload_btn.property("icon_path")
            if icon_path == "assets/stop.svg":
                current_browser.stop()
            else:
                current_browser.reload()

    def go_home(self):
        index = self.browser_stack.currentIndex()
        current_browser = self.browser_stack.currentWidget()
        
        behavior = SettingsManager.instance().get("startup_behavior", "home")
        if behavior == "blank":
            home_url = "about:blank"
        elif behavior == "custom":
            home_url = SettingsManager.instance().get("custom_startup_url", "tron://newtab")
            if not home_url.startswith("http") and not home_url.startswith("tron://") and not home_url.startswith("about:"):
                home_url = "https://" + home_url
        else:
            home_url = "tron://newtab"

        if home_url in ("tron://newtab", "tron://home"):
            if isinstance(current_browser, NewTabPage):
                return
            new_page = NewTabPage(self)
            if current_browser in self.browsers:
                idx = self.browsers.index(current_browser)
                self.browsers[idx] = new_page
            else:
                self.browsers.append(new_page)
            self.browser_stack.insertWidget(index, new_page)
            self.browser_stack.setCurrentWidget(new_page)
            self.browser_stack.removeWidget(current_browser)
            current_browser.hide()
            current_browser.deleteLater()
            self.tab_container.set_tab_title(index, "New Tab")
            self.tab_container.set_tab_icon(index, QIcon(resolve_resource("assets/app_icon.png")))
            self.title_bar.url_bar.clear()
            self.title_bar.url_bar.setPlaceholderText("Search Google or type a URL")
            self.title_bar.search_icon.show()
            self.title_bar.lock_icon.hide()
            return

        if isinstance(current_browser, QWebEngineView):
            current_browser.setUrl(QUrl(home_url))
        elif current_browser:
            browser = QWebEngineView()
            page = TronPage(self.profile, browser)
            c = ThemeManager.instance().colors()
            page.setBackgroundColor(parse_color(c["page_bg"]))
            browser.setPage(page)
            page.permissionRequested.connect(self.handle_permission_requested)
            
            overlay = ZoomOverlay(browser)
            browser._zoom_overlay = overlay
            
            browser.urlChanged.connect(lambda qurl, b=browser: self._on_url_changed(qurl, b))
            browser.titleChanged.connect(lambda title, b=browser: self._on_title_changed(title, b))
            browser.loadProgress.connect(lambda progress, b=browser: self._on_load_progress(progress, b))
            browser.loadStarted.connect(lambda b=browser: self._on_load_started(b))
            browser.loadFinished.connect(lambda ok, b=browser: self._on_load_finished(ok, b))
            browser.iconChanged.connect(lambda icon, b=browser: self._on_icon_changed(icon, b))

            if current_browser in self.browsers:
                idx = self.browsers.index(current_browser)
                self.browsers[idx] = browser
            else:
                self.browsers.append(browser)

            self.browser_stack.insertWidget(index, browser)
            self.browser_stack.setCurrentWidget(browser)
            self.browser_stack.removeWidget(current_browser)
            current_browser.hide()
            current_browser.deleteLater()
            browser.setUrl(QUrl(home_url))

    def navigate_to_url(self):
        if hasattr(self.title_bar, "suggestion_popup") and self.title_bar.suggestion_popup:
            self.title_bar.suggestion_popup.hide()

        url_text = self.title_bar.url_bar.text().strip()
        if not url_text:
            return
            
        if url_text.startswith("tron://"):
            self.navigate_internal_url(url_text)
            return

        if url_text.startswith('http://') or url_text.startswith('https://'):
            url = QUrl(url_text)
        elif '.' in url_text and ' ' not in url_text:
            url = QUrl('https://' + url_text)
        else:
            search_url = SettingsManager.instance().get_search_url(url_text)
            url = QUrl(search_url)
            
        current_browser = self.browser_stack.currentWidget()
        if isinstance(current_browser, QWebEngineView):
            current_browser.setUrl(url)
        elif current_browser in self.browsers:
            self.navigate_from_newtab(current_browser, url.toString())
        else:
            self.add_new_tab(url.toString())

    def sleep_tab(self, index):
        if 0 <= index < len(self.browsers):
            browser = self.browsers[index]
            if isinstance(browser, QWebEngineView) and not getattr(browser, "_is_sleeping", False):
                browser._saved_url = browser.url().toString()
                browser._saved_title = browser.title() or "Page"
                browser._is_sleeping = True
                
                c = ThemeManager.instance().colors()
                bg = c['page_bg']
                card_bg = c['card_bg']
                border = c['card_border']
                text_pri = c['text_primary']
                text_sec = c['text_secondary']
                accent = c['accent_blue']
                
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="utf-8">
                <style>
                  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: {bg}; color: {text_pri}; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
                  .card {{ background: {card_bg}; border: 1px solid {border}; border-radius: 20px; padding: 44px; text-align: center; max-width: 440px; box-shadow: 0 12px 40px rgba(0,0,0,0.2); }}
                  .icon {{ font-size: 56px; margin-bottom: 12px; display: inline-block; }}
                  h2 {{ margin: 0 0 8px 0; color: {accent}; font-size: 24px; font-weight: 800; }}
                  p {{ color: {text_sec}; font-size: 14px; margin-bottom: 20px; line-height: 1.5; }}
                  .url-badge {{ background: rgba(128,128,128,0.12); padding: 8px 16px; border-radius: 10px; font-family: monospace; font-size: 13px; word-break: break-all; margin-bottom: 24px; color: {text_pri}; border: 1px solid {border}; }}
                  button {{ background: {accent}; color: #ffffff; border: none; padding: 12px 28px; border-radius: 10px; font-weight: 700; cursor: pointer; font-size: 14px; }}
                  button:hover {{ opacity: 0.9; }}
                </style>
                </head>
                <body>
                <div class="card">
                  <div class="icon">🌙</div>
                  <h2>Tab Sleeping (RAM Saved)</h2>
                  <p>This tab was put to sleep after inactivity to optimize memory usage.</p>
                  <div class="url-badge">{browser._saved_title}</div>
                  <button onclick="location.reload()">Click to Wake Up Tab</button>
                </div>
                </body>
                </html>
                """
                browser.setHtml(html, QUrl(browser._saved_url))
                self.tab_container.set_tab_sleeping(index, True)
                self.show_browser_toast(f"Tab '{browser._saved_title[:20]}' put to sleep to save RAM")

    def wake_tab(self, index):
        if 0 <= index < len(self.browsers):
            browser = self.browsers[index]
            if isinstance(browser, QWebEngineView) and getattr(browser, "_is_sleeping", False):
                url_str = getattr(browser, "_saved_url", "")
                browser._is_sleeping = False
                browser._last_active_time = time.time()
                self.tab_container.set_tab_sleeping(index, False)
                if url_str:
                    browser.setUrl(QUrl(url_str))
                self.show_browser_toast("Tab woken up!")

    def _check_tab_sleeping(self):
        sm = SettingsManager.instance()
        if not sm.get("tab_suspension", True):
            return
            
        timeout_mins = sm.get("tab_sleep_timeout_minutes", 15)
        timeout_secs = timeout_mins * 60
        current_time = time.time()
        active_index = self.browser_stack.currentIndex()
        
        for i, browser in enumerate(self.browsers):
            if i != active_index and isinstance(browser, QWebEngineView):
                if not getattr(browser, "_is_sleeping", False):
                    last_active = getattr(browser, "_last_active_time", current_time)
                    if current_time - last_active >= timeout_secs:
                        self.sleep_tab(i)

    def show_tab_context_menu(self, index, global_pos):
        if 0 <= index < len(self.browsers):
            browser = self.browsers[index]
            menu = QMenu(self)
            c = ThemeManager.instance().colors()
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {c['menu_bg']};
                    border: 1px solid {c['menu_border']};
                    border-radius: 8px;
                    padding: 4px;
                }}
                QMenu::item {{
                    color: {c['menu_text']};
                    padding: 6px 20px;
                    border-radius: 4px;
                    font-size: 13px;
                }}
                QMenu::item:selected {{
                    background-color: {c['menu_hover']};
                }}
            """)
            
            is_sleeping = getattr(browser, "_is_sleeping", False)
            if is_sleeping:
                wake_act = menu.addAction("☀️ Wake Tab")
                wake_act.triggered.connect(lambda: self.wake_tab(index))
            else:
                sleep_act = menu.addAction("🌙 Sleep Tab (Save RAM)")
                sleep_act.triggered.connect(lambda: self.sleep_tab(index))
                
            dup_act = menu.addAction("📋 Duplicate Tab")
            if isinstance(browser, QWebEngineView):
                dup_act.triggered.connect(lambda: self.add_new_tab(browser.url().toString()))
            else:
                dup_act.setEnabled(False)
                
            reload_act = menu.addAction("🔄 Reload Tab")
            reload_act.triggered.connect(lambda: self.reload_tab(index))
            
            menu.addSeparator()
            
            close_act = menu.addAction("❌ Close Tab")
            close_act.triggered.connect(lambda: self.close_tab(index))
            
            close_others_act = menu.addAction("🚫 Close Other Tabs")
            close_others_act.triggered.connect(lambda: self.close_other_tabs(index))
            
            menu.exec(global_pos)

    def reload_tab(self, index):
        if 0 <= index < len(self.browsers):
            b = self.browsers[index]
            if getattr(b, "_is_sleeping", False):
                self.wake_tab(index)
            elif hasattr(b, "reload"):
                b.reload()

    def close_other_tabs(self, keep_index):
        for i in reversed(range(len(self.browsers))):
            if i != keep_index:
                self.close_tab(i)

    def _on_url_changed(self, qurl, browser):
        url_str = qurl.toString()
        browser._last_active_time = time.time()
        if not getattr(browser, "_is_sleeping", False):
            browser._saved_url = url_str
        if browser == self.browser_stack.currentWidget():
            if 'tronexplorer.netlify.app' in url_str or 'novaaisearch.netlify.app' in url_str or not url_str or url_str == 'about:blank':
                self.title_bar.url_bar.clear()
                self.title_bar.search_icon.show()
                self.title_bar.lock_icon.hide()
            else:
                self.title_bar.url_bar.setText(url_str)
                self.title_bar.search_icon.hide()
                self.title_bar.lock_icon.show()
            self.update_bookmark_star_state()

        if hasattr(browser, "title") and not self.is_incognito:
            title = browser.title()
            if url_str and not url_str.startswith("about:") and not "tronexplorer" in url_str and not "novaaisearch" in url_str:
                HistoryManager.instance().add_history(title or url_str, url_str)

    def _on_load_progress(self, progress, browser):
        if browser == self.browser_stack.currentWidget():
            if hasattr(self.title_bar, "set_load_progress"):
                self.title_bar.set_load_progress(progress)

    def _on_load_started(self, browser):
        if browser == self.browser_stack.currentWidget():
            self.title_bar.set_reload_state(True)
            if hasattr(self.title_bar, "set_load_progress"):
                self.title_bar.set_load_progress(15)
            self.set_pwa_installable(False)
            
        if browser in self.browsers:
            i = self.browsers.index(browser)
            self.tab_container.set_tab_loading(i, True)

    def _on_load_finished(self, ok, browser):
        if browser == self.browser_stack.currentWidget():
            self.title_bar.set_reload_state(False)
            if hasattr(self.title_bar, "set_load_progress"):
                self.title_bar.set_load_progress(100)
            self.update_bookmark_star_state()
            
        if browser in self.browsers:
            i = self.browsers.index(browser)
            self.tab_container.set_tab_loading(i, False)
            url_str = browser.url().toString()
            if "tronexplorer.netlify.app" in url_str or "novaaisearch.netlify.app" in url_str:
                self.tab_container.set_tab_icon(i, QIcon(resolve_resource("assets/app_icon.png")))
                self.tab_container.set_tab_title(i, "New Tab")
            else:
                icon = browser.icon()
                if icon.isNull():
                    c = ThemeManager.instance().colors()
                    icon = get_tinted_icon("assets/lock.svg", c["icon_stroke"], QSize(16, 16))
                self.tab_container.set_tab_icon(i, icon)

    def _on_icon_changed(self, icon, browser):
        if browser in self.browsers:
            i = self.browsers.index(browser)
            url_str = browser.url().toString()
            if "tronexplorer.netlify.app" in url_str or "novaaisearch.netlify.app" in url_str:
                self.tab_container.set_tab_icon(i, QIcon(resolve_resource("assets/app_icon.png")))
            else:
                self.tab_container.set_tab_icon(i, icon)

    def _on_title_changed(self, title, browser):
        if browser == self.browser_stack.currentWidget():
            self.setWindowTitle(f"Tron - {title}")
            if self.is_pwa_mode:
                if hasattr(self.title_bar, "title_label"):
                    self.title_bar.title_label.setText(title)
                if hasattr(self.tab_container, "pwa_title_label"):
                    self.tab_container.pwa_title_label.setText(title)
            
        if browser in self.browsers:
            i = self.browsers.index(browser)
            url_str = browser.url().toString()
            if "tronexplorer.netlify.app" in url_str or "novaaisearch.netlify.app" in url_str:
                self.tab_container.set_tab_title(i, "New Tab")
            else:
                short_title = (title[:30] + '...') if len(title) > 30 else title
                self.tab_container.set_tab_title(i, short_title)
                if url_str and not url_str.startswith("about:") and not self.is_incognito:
                    HistoryManager.instance().add_history(title or url_str, url_str)

    def toggle_tab_mute(self, index):
        if 0 <= index < len(self.browsers):
            b = self.browsers[index]
            if hasattr(b, "page") and hasattr(b.page(), "setAudioMuted"):
                page = b.page()
                is_muted = not page.isAudioMuted()
                page.setAudioMuted(is_muted)
                if hasattr(self.tab_container, "set_tab_muted"):
                    self.tab_container.set_tab_muted(index, is_muted)
                self.show_browser_toast("Tab muted" if is_muted else "Tab unmuted")

    def _on_recently_audible_changed(self, audible, browser):
        if browser in self.browsers:
            i = self.browsers.index(browser)
            is_muted = False
            if hasattr(browser, "page") and hasattr(browser.page(), "isAudioMuted"):
                is_muted = browser.page().isAudioMuted()
            if hasattr(self.tab_container, "set_tab_audible"):
                self.tab_container.set_tab_audible(i, audible, is_muted=is_muted)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resizing = self._check_resize_area(event.position().toPoint())
            self.drag_pos = event.globalPosition().toPoint()
            self._orig_rect = self.geometry()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            self._perform_resize(event.globalPosition().toPoint())
        else:
            self._update_cursor(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        self._update_cursor(self.mapFromGlobal(QCursor.pos()))
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def _reset_cursor_to_arrow(self):
        if not self.resizing:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _check_resize_area(self, pos):
        if self.isMaximized():
            return False

        px, py = pos.x(), pos.y()
        margin = self.MARGIN
        self.resize_dir = None

        if px < margin and py < margin:
            self.resize_dir = 'topleft'
        elif px > self.width()-margin and py < margin:
            self.resize_dir = 'topright'
        elif px < margin and py > self.height()-margin:
            self.resize_dir = 'bottomleft'
        elif px > self.width()-margin and py > self.height()-margin:
            self.resize_dir = 'bottomright'
        elif px < margin:
            self.resize_dir = 'left'
        elif px > self.width()-margin:
            self.resize_dir = 'right'
        elif py < margin:
            self.resize_dir = 'top'
        elif py > self.height()-margin:
            self.resize_dir = 'bottom'

        return self.resize_dir is not None

    def _update_cursor(self, pos):
        if self.isMaximized():
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        margin = self.MARGIN
        px, py = pos.x(), pos.y()
        cursor_set = False

        if px < margin and py < margin:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            cursor_set = True
        elif px > self.width()-margin and py < margin:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            cursor_set = True
        elif px < margin and py > self.height()-margin:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            cursor_set = True
        elif px > self.width()-margin and py > self.height()-margin:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            cursor_set = True
        elif px < margin:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            cursor_set = True
        elif px > self.width()-margin:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            cursor_set = True
        elif py < margin:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            cursor_set = True
        elif py > self.height()-margin:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            cursor_set = True

        if cursor_set:
            self.cursor_reset_timer.start(1500)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.cursor_reset_timer.stop()

    def _perform_resize(self, global_pos):
        diff = global_pos - self.drag_pos
        rect = QRect(self._orig_rect)

        if 'left' in self.resize_dir:
            rect.setLeft(rect.left() + diff.x())
        if 'right' in self.resize_dir:
            rect.setRight(rect.right() + diff.x())
        if 'top' in self.resize_dir:
            rect.setTop(rect.top() + diff.y())
        if 'bottom' in self.resize_dir:
            rect.setBottom(rect.bottom() + diff.y())

        if rect.width() >= self.MIN_WIDTH and rect.height() >= self.MIN_HEIGHT:
            self.setGeometry(rect)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if not self.isMinimized():
                self.setWindowOpacity(1.0)
                if hasattr(self, 'title_bar'):
                    self.title_bar.update_max_icon(self.isMaximized())
        super().changeEvent(event)

    def nativeEvent(self, eventType, message):
        try:
            if eventType == b"windows_generic_MSG" and sys.platform == "win32":
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x0084:
                    x = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    pos = self.mapFromGlobal(QPoint(x, y))
                    lx, ly = pos.x(), pos.y()
                    
                    margin = 8
                    w, h = self.width(), self.height()
                    
                    if lx < margin and ly < margin:
                        return True, 13
                    if lx > w - margin and ly < margin:
                        return True, 14
                    if lx < margin and ly > h - margin:
                        return True, 16
                    if lx > w - margin and ly > h - margin:
                        return True, 17
                    
                    if lx < margin:
                        return True, 10
                    if lx > w - margin:
                        return True, 11
                    if ly < margin:
                        return True, 12
                    if ly > h - margin:
                        return True, 15
                    
                    if hasattr(self, "tab_container") and hasattr(self, "title_bar"):
                        tab_h = self.tab_container.height() if self.tab_container.isVisible() else 0
                        title_h = self.title_bar.height() if self.title_bar.isVisible() else 0
                        if ly < tab_h:
                            child = self.tab_container.childAt(lx, ly)
                            if child is None or child == self.tab_container or child.objectName() in ["tabBarContainer", "emptyDragArea", "tabsStrip"]:
                                return True, 2
                        elif ly < tab_h + title_h:
                            child = self.title_bar.childAt(lx, ly - tab_h)
                            if child is None or child == self.title_bar:
                                return True, 2
        except Exception:
            pass
                             
        return False, 0

    def set_pwa_installable(self, installable):
        self.current_tab_installable = installable
        if hasattr(self, "title_bar") and hasattr(self.title_bar, "pwa_btn"):
            if installable:
                self.title_bar.pwa_btn.show()
            else:
                self.title_bar.pwa_btn.hide()

    def trigger_pwa_install(self):
        active_view = self.browser_stack.currentWidget()
        if isinstance(active_view, QWebEngineView):
            js = """
                (function() {
                    if (window._tronDeferredPrompt) {
                        return "NATIVE";
                    }
                    return "FALLBACK";
                })()
            """
            def on_check_result(res):
                if res == "NATIVE":
                    native_js = """
                        window._tronDeferredPrompt.prompt();
                        window._tronDeferredPrompt.userChoice.then((choiceResult) => {
                            window._tronDeferredPrompt = null;
                            console.log("TRON_PWA_INSTALLABLE:false");
                        });
                    """
                    active_view.page().runJavaScript(native_js)
                else:
                    title = active_view.title() or "Web App"
                    url = active_view.url().toString()
                    self.create_pwa_shortcut(title, url)
                    self.show_browser_toast(f"Installed '{title}' to your Desktop!")
                    
            active_view.page().runJavaScript(js, on_check_result)

    def create_pwa_shortcut(self, name, url):
        import subprocess
        main_py = os.path.abspath(sys.argv[0])
        desktop = os.path.expanduser("~/Desktop")
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        lnk_path = os.path.join(desktop, f"{safe_name}.lnk")
        
        ps_cmd = f"""
        $s = (New-Object -ComObject WScript.Shell).CreateShortcut('{lnk_path}');
        $s.TargetPath = 'python.exe';
        $s.Arguments = '"{main_py}" --pwa "{url}"';
        $s.Save();
        """
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)

    def closeEvent(self, event):
        sm = SettingsManager.instance()
        sm.set("window_maximized", self.isMaximized())
        if not self.isMaximized():
            geo = self.geometry()
            sm.set("window_geometry", [geo.x(), geo.y(), geo.width(), geo.height()])
        else:
            if hasattr(self, "_last_normal_geometry") and self._last_normal_geometry:
                g = self._last_normal_geometry
                sm.set("window_geometry", [g.x(), g.y(), g.width(), g.height()])
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_should_maximize", False):
            self._should_maximize = False
            self.showMaximized()
            if hasattr(self, "title_bar") and hasattr(self.title_bar, "update_max_icon"):
                self.title_bar.update_max_icon(True)

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            if hasattr(self, "title_bar") and hasattr(self.title_bar, "update_max_icon"):
                self.title_bar.update_max_icon(self.isMaximized())
        super().changeEvent(event)
