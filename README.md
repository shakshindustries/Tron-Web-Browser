# 🚀 Tron Web Browser

<p align="center">
  <img src="assets/app_icon.png" width="128" height="128" alt="Tron Browser Logo" />
</p>

<p align="center">
  <strong>A modern, high-performance, Chromium-powered web browser with native customization, smooth animations, and clean Chrome-inspired aesthetics built with Python & PyQt6.</strong>
</p>

---

## ✨ Features

- 🌐 **Chromium Web Engine**: Powered by `PyQt6-WebEngine` with GPU acceleration, zero-copy rasterization, and modern web standards.
- 🎨 **Adaptive Design System**:
  - Chrome-style rounded tab bar with dynamic accent tinting and smooth tab closing.
  - Transparent-idle navigation buttons with subtle hover feedback.
  - Comprehensive Light and Dark theme modes with real-time switching.
- 🖼️ **Customizable New Tab Page**:
  - Live wallpaper engine with curated stock wallpapers or custom wallpaper uploads.
  - Search suggestion dropdown with instant history shortcuts and edge-to-edge highlights.
  - Full `Ctrl + Wheel` smooth zooming with percentage toast indicators.
- 📥 **Built-in Download Manager**: Real-time progress bar, pause/resume/cancel controls, and category filtering (Documents, Images, Media, etc.).
- 🛡️ **Shield & Privacy Protection**: Built-in tracking/ad-blocking controls and private Incognito browsing mode.
- 🔖 **Bookmarks & History Suite**: Full bookmark management and search-indexed history viewer.
- 📦 **PWA / Desktop App Installability**: Install web apps directly to your desktop.

---

## 🛠️ Prerequisites

Before getting started, make sure you have:

- **Windows 10 / 11** (64-bit recommended)
- **Python 3.10+** (Python 3.11, 3.12, 3.13, or 3.14)
- **Git** (for cloning the repository)
- *(Optional, for building the Windows Setup installer)*: [Inno Setup 6.x](https://jrsoftware.org/isdl.php)

---

## 🚀 Getting Started (Run from Source)

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/Tron-Web-Browser.git
cd Tron-Web-Browser
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note**: For live microphone voice search, optionally install `pip install PyAudio`.

### 4. Launch Tron Browser
```bash
python main.py
```

---

## 📦 How to Build the Standalone Executable & Installer

You can distribute Tron Browser either as a portable `.exe` folder or as a professional Windows Setup Installer (`.exe`).


### Option 1: Manual Build (Step-by-Step)

#### Step 1: Build the Standalone Executable with PyInstaller
Run the following command in Command Prompt or PowerShell:
```cmd
python -m PyInstaller --noconfirm --onedir --windowed --name TronBrowser --icon assets\app_icon.ico --collect-all PyQt6.QtSvg --add-data "assets;assets" main.py
```

Ensure assets are available directly beside the executable:
```cmd
if not exist "dist\TronBrowser\assets" mkdir "dist\TronBrowser\assets"
xcopy /E /I /Y "assets\*" "dist\TronBrowser\assets\"
```

You can now test and run the standalone browser directly from:
```
dist\TronBrowser\TronBrowser.exe
```

#### Step 2: Create the Windows Setup Installer (.exe) with Inno Setup
1. Download and install [Inno Setup 6](https://jrsoftware.org/isdl.php) (e.g. version 6.3+ or 6.7+).
2. Right-click [`TronBrowserInstaller.iss`](TronBrowserInstaller.iss) $\rightarrow$ **Compile**, **OR** run from the terminal:
   ```cmd
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" TronBrowserInstaller.iss
   ```
3. Your installer will be ready in:
   ```
   Output\TronBrowserSetup_v2.5.exe
   ```

---

## ⌨️ Useful Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + T` | Open a new tab |
| `Ctrl + W` | Close the active tab |
| `Ctrl + N` | Open a new browser window |
| `Ctrl + Shift + N` | Open an Incognito window |
| `Ctrl + L` / `Alt + D` | Focus URL address bar |
| `Ctrl + H` | Open Browsing History |
| `Ctrl + J` | Open Downloads page |
| `Ctrl + D` | Bookmark active page |
| `Ctrl + +` / `Ctrl + -` | Zoom in / Zoom out |
| `Ctrl + 0` | Reset Zoom to 100% |
| `Ctrl + MouseWheel` | Dynamic Zoom with percentage toast |
| `F5` / `Ctrl + R` | Reload active page |
| `F11` | Toggle Fullscreen |

---

## 📁 Project Structure

```
Tron-Web-Browser/
├── assets/                    # SVG icons, app icons, and default wallpapers
├── about_page.py              # tron://about architecture & features page
├── bookmarks_manager.py       # JSON bookmark storage and controller
├── bookmarks_page.py          # tron://bookmarks manager page
├── browser_menu.py            # Modern Chrome-style 3-dots dropdown menu
├── browser_window.py          # Main application window & Chromium tab orchestration
├── download_manager.py        # Concurrent download tracker & downloads page
├── history_manager.py         # Persistent SQLite/JSON history database
├── history_page.py            # tron://history search viewer
├── new_tab_page.py            # Customizable dashboard, wallpaper engine & search bar
├── settings_manager.py        # User settings & preference persistence
├── settings_page.py           # tron://settings configuration page
├── tab_bar.py                 # Chrome-style tab strip with animations & close buttons
├── theme_manager.py           # Dynamic accent palette and theme manager
├── title_bar.py               # Frameless title bar with navigation controls
├── toast_overlay.py           # Floating toast indicators (zoom %, notifications)
├── main.py                    # Application entry point & crash protection
├── build_installer.bat        # Automated one-click PyInstaller + Inno Setup build script
├── TronBrowserInstaller.iss   # Inno Setup compiler configuration
└── requirements.txt           # Python dependencies
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
