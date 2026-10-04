import sys
import os
import shutil
import threading
import ctypes

# Ensure correct working directory so relative paths like "assets/..." always resolve
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

# Fix taskbar icon on Windows by explicitly setting AppUserModelID
if sys.platform == 'win32':
    try:
        myappid = 'Tron.Browser.App.v2'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# Chromium flags: GPU acceleration, speech recognition, microphone/camera streams, zero-copy rasterization
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--enable-gpu-rasterization --enable-zero-copy --ignore-gpu-blocklist --enable-speech-input --enable-media-stream --enable-usermedia-screen-capturing --log-level=3'

from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from PyQt6.QtSvg import QSvgRenderer

# Ensure Qt plugins (qsvg.dll, imageformats, iconengines) are located in frozen bundles
if getattr(sys, 'frozen', False):
    for candidate_plugin_dir in [
        os.path.join(BASE_DIR, "PyQt6", "Qt6", "plugins"),
        os.path.join(BASE_DIR, "_internal", "PyQt6", "Qt6", "plugins"),
        os.path.join(BASE_DIR, "plugins"),
        os.path.join(BASE_DIR, "_internal", "plugins"),
    ]:
        if os.path.exists(candidate_plugin_dir):
            QCoreApplication.addLibraryPath(candidate_plugin_dir)
            os.environ["QT_PLUGIN_PATH"] = candidate_plugin_dir

from browser_window import TronWindow

def excepthook(type, value, traceback):
    import traceback as tb
    try:
        with open("error.log", "a", encoding="utf-8") as f:
            tb.print_exception(type, value, traceback, file=f)
    except Exception:
        pass
    print(f"[Tron Crash Protection] Suppressed unhandled exception: {value}")

sys.excepthook = excepthook

def clear_gpu_cache_async():
    """Non-blocking background cleanup of stale/leftover GPU caches without disrupting active sessions."""
    def _cleanup():
        cache_base = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'python', 'QtWebEngine')
        if os.path.exists(cache_base):
            for profile in ['Default', 'TronProfile']:
                profile_path = os.path.join(cache_base, profile)
                if os.path.exists(profile_path):
                    try:
                        for item in os.listdir(profile_path):
                            if 'old_GPUCache' in item:
                                shutil.rmtree(os.path.join(profile_path, item), ignore_errors=True)
                    except Exception:
                        pass
    t = threading.Thread(target=_cleanup, daemon=True)
    t.start()

from theme_manager import resolve_resource

def main():
    clear_gpu_cache_async()

    app = QApplication(sys.argv)
    icon_path = resolve_resource("assets/app_icon.ico")
    if not os.path.exists(icon_path):
        icon_path = resolve_resource("assets/app_icon.png")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    else:
        app_icon = None

    is_pwa = False
    pwa_url = None
    if "--pwa" in sys.argv:
        idx = sys.argv.index("--pwa")
        if idx + 1 < len(sys.argv):
            is_pwa = True
            pwa_url = sys.argv[idx + 1]

    win = TronWindow(is_pwa_mode=is_pwa, pwa_url=pwa_url)
    if app_icon:
        win.setWindowIcon(app_icon)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

