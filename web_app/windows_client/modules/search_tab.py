import os
import threading
import webbrowser
import subprocess
import time
import pyautogui
import pyperclip
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, 
    QLineEdit, QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt, QMetaObject, Q_ARG, QTimer, QSize
from PySide6.QtGui import QIcon, QTextCursor

class SearchTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type your search query...")
        self.input_box.setMinimumHeight(40)
        self.input_box.setStyleSheet("font-size: 20px;")
        self.input_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Add custom cross (X) button at the end
        from PySide6.QtWidgets import QToolButton
        from PySide6.QtWidgets import QStyle
        from PySide6.QtCore import QSize
        self.clear_btn = QToolButton(self.input_box)
        self.clear_btn.setText('✕')  # Unicode cross
        self.clear_btn.setCursor(Qt.ArrowCursor)
        self.clear_btn.setStyleSheet('border: none; font-size: 18px; color: #888; background: transparent;')
        self.clear_btn.setFixedSize(24, 24)
        self.clear_btn.setToolTip('Clear input')
        self.clear_btn.clicked.connect(self.clear_and_refocus_input)
        self.clear_btn.hide()
        self.input_box.textChanged.connect(lambda text: self.clear_btn.setVisible(bool(text)))
        # Adjust margins to make space for the button
        right_margin = self.clear_btn.width() + 4
        self.input_box.setTextMargins(0, 0, right_margin, 0)
        layout.addWidget(self.input_box)
        # Position the button inside the QLineEdit
        def position_clear_btn():
            frame_width = self.input_box.style().pixelMetric(QStyle.PixelMetric.PM_DefaultFrameWidth)
            x = self.input_box.rect().right() - self.clear_btn.width() - frame_width - 2
            y = (self.input_box.height() - self.clear_btn.height()) // 2
            self.clear_btn.move(x, y)
        self.input_box.resizeEvent = lambda event: (position_clear_btn(), QLineEdit.resizeEvent(self.input_box, event))
        position_clear_btn()

        # Log box for STT
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(80)
        self.log_box.setMaximumHeight(160)
        self.log_box.setStyleSheet("font-size: 14px; background: #f8f8f8;")
        layout.addWidget(self.log_box)

        # Ensure icons directory exists
        icons_dir = os.path.join(os.path.dirname(__file__), "../icons")
        if not os.path.exists(icons_dir):
            os.makedirs(icons_dir)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(20)
        self.icons = [
            ("google", "google.png", lambda q: webbrowser.open(f"https://www.google.com/search?q={q}")),
            ("youtube", "youtube.png", lambda q: webbrowser.open(f"https://www.youtube.com/results?search_query={q}")),
            ("chatgpt", "chatgpt.png", lambda q: webbrowser.open(f"https://chat.openai.com/?q={q}")),
            ("bing", "bing.png", lambda q: webbrowser.open(f"https://www.bing.com/search?q={q}")),
            ("gemini", "gemini.png", self.search_gemini),
            ("file_explorer", "file_explorer.png", self.search_file_explorer),
            ("windows_search", "windows_search.png", self.search_windows),
        ]
        self.icon_buttons = []
        for name, icon_file, handler in self.icons:
            btn = QPushButton()
            icon_path = os.path.join(icons_dir, icon_file)
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
            else:
                btn.setText(name.capitalize())
            btn.setIconSize(QSize(40, 40))
            btn.setFixedSize(48, 48)
            btn.setStyleSheet("border: none;")
            btn.clicked.connect(self._make_search_handler(handler))
            icon_row.addWidget(btn)
            self.icon_buttons.append(btn)
        # Add microphone button for Windows dictation
        self.mic_btn = QPushButton()
        self.mic_icon_path = os.path.join(icons_dir, 'mic.png')
        if os.path.exists(self.mic_icon_path):
            self.mic_btn.setIcon(QIcon(self.mic_icon_path))
        else:
            self.mic_btn.setText("Mic")
        self.mic_btn.setIconSize(QSize(40, 40))
        self.mic_btn.setFixedSize(48, 48)
        self.mic_btn.setStyleSheet("border: none;")
        self.mic_btn.setToolTip("Start Windows dictation (WIN+H)")
        self.mic_btn.setEnabled(True)  # Always enabled
        self.mic_btn.setCheckable(False)  # Not a toggle
        self.mic_btn.clicked.connect(self.trigger_windows_dictation)
        icon_row.addWidget(self.mic_btn)
        self.icon_buttons.append(self.mic_btn)
        layout.addLayout(icon_row)
        layout.addStretch()
        self.setLayout(layout)
        self.input_box.returnPressed.connect(lambda: self.icons[0][2](self.input_box.text()))

    def _make_search_handler(self, handler):
        return lambda *args, h=handler: h(self.input_box.text())

    def log(self, msg):
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        def append():
            self.log_box.append(msg)
            self.log_box.moveCursor(QTextCursor.End)
        if threading.current_thread() is threading.main_thread():
            append()
        else:
            QMetaObject.invokeMethod(self.log_box, "append", Qt.QueuedConnection, Q_ARG(str, msg))
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.log_box.moveCursor(QTextCursor.End))

    def trigger_windows_dictation(self):
        self.input_box.setFocus()
        try:
            import pyautogui
            import time
            time.sleep(0.2)
            pyautogui.hotkey('win', 'h')
            self.log("🎤 Windows dictation started (WIN+H). Speak now...")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self.input_box.setFocus)
        except Exception as e:
            self.log(f"❌ Could not trigger Windows dictation: {e}")
        finally:
            self.mic_btn.setEnabled(True)  # Always re-enable after click

    def search_gemini(self, query):
        import webbrowser
        if query:
            import pyperclip
            pyperclip.copy(query)
            webbrowser.open("https://gemini.google.com/app")
        else:
            webbrowser.open("https://gemini.google.com/app")

    def search_file_explorer(self, query):
        import subprocess
        import urllib.parse
        import time
        import pyautogui
        import pyperclip
        if query:
            subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            time.sleep(1.5)
            pyautogui.hotkey('ctrl', 'e')
            time.sleep(0.2)
            pyperclip.copy(query)
            pyautogui.hotkey('ctrl', 'v')
            pyautogui.press('enter')

    def search_windows(self, query):
        import pyautogui
        import pyperclip
        import time
        if query:
            pyautogui.hotkey('win', 's')
            time.sleep(0.5)
            pyperclip.copy(query)
            pyautogui.hotkey('ctrl', 'v')
            pyautogui.press('enter')

    def focus_input(self):
        self.input_box.setFocus()

    def clear_and_refocus_input(self):
        self.input_box.clear()
        self.input_box.setFocus()

    def closeEvent(self, event):
        event.accept() 