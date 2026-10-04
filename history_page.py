import os
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QFrame, QSizePolicy
)
from theme_manager import ThemeManager, get_tinted_icon
from history_manager import HistoryManager

class ElidedLabel(QLabel):
    """QLabel subclass that dynamically elides long text with ellipsis (...) on resize."""
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text or ""
        self.update_elided_text()

    def setText(self, text):
        self._full_text = text or ""
        self.update_elided_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_elided_text()

    def update_elided_text(self):
        if not self._full_text:
            super().setText("")
            return
        fm = self.fontMetrics()
        elided = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, max(20, self.width()))
        super().setText(elided)


class HistoryCard(QFrame):
    def __init__(self, item, parent_page):
        super().__init__(parent_page)
        self.item = item
        self.parent_page = parent_page
        self.setObjectName("historyCard")
        self.setFixedHeight(52)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(18, 18)
        layout.addWidget(self.icon_lbl)

        self.time_lbl = QLabel(item.get("time", ""))
        self.time_lbl.setObjectName("timeLabel")
        self.time_lbl.setFixedWidth(60)
        layout.addWidget(self.time_lbl)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.title_lbl = ElidedLabel(item.get("title", "") or item.get("url", ""))
        self.title_lbl.setObjectName("cardTitle")
        
        self.url_lbl = ElidedLabel(item.get("url", ""))
        self.url_lbl.setObjectName("cardUrl")
        self.url_lbl.setToolTip(item.get("url", ""))
        
        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.url_lbl)
        layout.addLayout(text_layout, 1)
        
        self.open_btn = QPushButton("Visit")
        self.open_btn.setFixedHeight(28)
        self.open_btn.setFixedWidth(64)
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(self.open_history_item)
        
        self.delete_btn = QPushButton()
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setToolTip("Remove from history")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self.delete_history_item)
        
        layout.addWidget(self.open_btn)
        layout.addWidget(self.delete_btn)
        
        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        ic = c["icon_stroke"]
        
        self.icon_lbl.setPixmap(get_tinted_icon("assets/history.svg", c["accent_blue"], QSize(18, 18)).pixmap(QSize(18, 18)))
        self.open_btn.setIcon(get_tinted_icon("assets/open.svg", ic, QSize(12, 12)))
        self.delete_btn.setIcon(get_tinted_icon("assets/cancel.svg", ic, QSize(12, 12)))

        self.setStyleSheet(f"""
            #historyCard {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 10px;
            }}
            #historyCard:hover {{
                border: 1px solid {c['accent_blue']};
            }}
            QLabel#timeLabel {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 500;
            }}
            QLabel#cardTitle {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#cardUrl {{
                color: {c['accent_blue']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }}
            QPushButton {{
                background-color: {c['btn_bg']};
                color: {c['text_primary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                border-radius: 6px;
                padding: 4px 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {c['btn_hover']};
            }}
        """)

    def open_history_item(self):
        main_win = self.window()
        if hasattr(main_win, "navigate_to_url"):
            main_win.title_bar.url_bar.setText(self.item["url"])
            main_win.navigate_to_url()

    def delete_history_item(self):
        HistoryManager.instance().remove_item(self.item["url"])


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyPage")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        self.title_lbl = QLabel("Browsing History")
        self.title_lbl.setObjectName("pageTitle")
        
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("searchBar")
        self.search_bar.setPlaceholderText("Search history...")
        self.search_bar.textChanged.connect(self.load_history)
        self.search_bar.setFixedWidth(240)
        self.search_bar.setFixedHeight(32)
        
        self.clear_btn = QPushButton("Clear Browsing Data")
        self.clear_btn.setObjectName("clearBtn")
        self.clear_btn.clicked.connect(self.clear_all)
        
        header.addWidget(self.title_lbl)
        header.addStretch(1)
        header.addWidget(self.search_bar)
        header.addWidget(self.clear_btn)
        layout.addLayout(header)
        
        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setContentsMargins(0, 0, 16, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll, 1)

        # Empty state
        self.empty_frame = QFrame()
        self.empty_frame.setObjectName("emptyState")
        empty_l = QVBoxLayout(self.empty_frame)
        empty_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_l.setSpacing(10)
        
        self.empty_icon = QLabel()
        self.empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_l.addWidget(self.empty_icon)
        
        empty_txt = QLabel("Your browsing history is clean")
        empty_txt.setObjectName("emptyText")
        empty_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_l.addWidget(empty_txt)
        
        layout.addWidget(self.empty_frame, 1)
        self.empty_frame.hide()

        HistoryManager.instance().history_changed.connect(self.load_history)
        ThemeManager.instance().theme_changed.connect(self.update_styles)
        self.update_styles()
        self.load_history()

    def update_styles(self):
        c = ThemeManager.instance().colors()
        self.empty_icon.setPixmap(get_tinted_icon("assets/history.svg", c["text_secondary"], QSize(48, 48)).pixmap(QSize(48, 48)))

        self.setStyleSheet(f"""
            #historyPage {{
                background-color: {c['page_bg']};
            }}
            QLabel#pageTitle {{
                color: {c['text_primary']};
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                font-size: 20px;
                font-weight: 600;
            }}
            QLineEdit#searchBar {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 16px;
                padding: 4px 14px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {c['text_primary']};
            }}
            QLineEdit#searchBar:focus {{
                border: 1px solid {c['accent_blue']};
            }}
            QPushButton#clearBtn {{
                background-color: {c['btn_bg']};
                color: {c['text_primary']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 500;
                border-radius: 6px;
                padding: 6px 14px;
                border: none;
            }}
            QPushButton#clearBtn:hover {{
                background-color: {c['btn_hover']};
            }}
            #emptyState {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
                padding: 40px;
            }}
            #emptyText {{
                color: {c['text_secondary']};
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: 500;
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
        """)

    def load_history(self):
        for i in reversed(range(self.list_layout.count())):
            item = self.list_layout.itemAt(i)
            w = item.widget()
            if w:
                w.deleteLater()
                
        filter_txt = self.search_bar.text().strip().lower()
        history = HistoryManager.instance().history
        
        count = 0
        for h in history:
            if filter_txt and (filter_txt not in h["title"].lower() and filter_txt not in h["url"].lower()):
                continue
            count += 1
            card = HistoryCard(h, self)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        if count == 0:
            self.scroll.hide()
            self.empty_frame.show()
        else:
            self.scroll.show()
            self.empty_frame.hide()

    def clear_all(self):
        HistoryManager.instance().clear_history()
