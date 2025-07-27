import requests
import os
import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QCheckBox, QSizePolicy, QDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
import subprocess
import time
import ctypes

# --- Conversation DB Helper ---
def get_db_path():
    # Use the daily_logs.db in the new db/ folder at the project root
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_dir = os.path.join(base, "db")
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "daily_logs.db")
    return db_path

def ensure_convo_table():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS llm_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            provider TEXT,
            role TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_convo_message(provider, role, message):
    ensure_convo_table()
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute(
        "INSERT INTO llm_conversations (timestamp, provider, role, message) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(timespec='seconds'), provider, role, message)
    )
    conn.commit()
    conn.close()

# --- Worker Thread for API Calls ---
class LLMWorker(QThread):
    result = Signal(str)
    error = Signal(str)

    def __init__(self, prompt, provider, api_keys, model_map):
        super().__init__()
        self.prompt = prompt
        self.provider = provider
        self.api_keys = api_keys
        self.model_map = model_map

    def run(self):
        try:
            if self.provider == "Groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_keys['Groq']}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model_map['Groq'],
                    "messages": [
                        {"role": "user", "content": self.prompt}
                    ]
                }
                resp = requests.post(url, headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    self.result.emit(content)
                else:
                    self.error.emit(f"Groq API Error: {resp.status_code} {resp.text}")
            elif self.provider == "Cohere":
                url = "https://api.cohere.ai/v1/chat"
                headers = {
                    "Authorization": f"Bearer {self.api_keys['Cohere']}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model_map['Cohere'],
                    "message": self.prompt
                }
                resp = requests.post(url, headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    content = resp.json().get("text") or resp.json().get("response") or resp.json().get("reply")
                    if not content:
                        content = str(resp.json())
                    self.result.emit(content)
                else:
                    self.error.emit(f"Cohere API Error: {resp.status_code} {resp.text}")
            elif self.provider == "OpenRouter":
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_keys['OpenRouter']}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model_map['OpenRouter'],
                    "messages": [
                        {"role": "user", "content": self.prompt}
                    ]
                }
                resp = requests.post(url, headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    self.result.emit(content)
                else:
                    self.error.emit(f"OpenRouter API Error: {resp.status_code} {resp.text}")
            elif self.provider == "GoogleGemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_map['GoogleGemini']}:generateContent?key={self.api_keys['GoogleGemini']}"
                headers = {"Content-Type": "application/json"}
                data = {
                    "contents": [{"parts": [{"text": self.prompt}]}]
                }
                resp = requests.post(url, headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    candidates = resp.json().get("candidates", [])
                    if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                        content = candidates[0]["content"]["parts"][0].get("text", "")
                    else:
                        content = str(resp.json())
                    self.result.emit(content)
                else:
                    self.error.emit(f"Google Gemini API Error: {resp.status_code} {resp.text}")
            elif self.provider == "Cerebras":
                url = "https://api.cerebras.ai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_keys['Cerebras']}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "llama3.3-70b",
                    "messages": [
                        {"role": "user", "content": self.prompt}
                    ]
                }
                resp = requests.post(url, headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    self.result.emit(content)
                else:
                    self.error.emit(f"Cerebras API Error: {resp.status_code} {resp.text}")
            elif self.provider == "Mistral":
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_keys['Mistral']}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model_map['Mistral'],
                    "messages": [
                        {"role": "user", "content": self.prompt}
                    ]
                }
                resp = requests.post(url, headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    self.result.emit(content)
                else:
                    self.error.emit(f"Mistral API Error: {resp.status_code} {resp.text}")
            elif self.provider == "Mixtral":
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_keys['Mixtral']}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model_map['Mixtral'],
                    "messages": [
                        {"role": "user", "content": self.prompt}
                    ]
                }
                resp = requests.post(url, headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    self.result.emit(content)
                else:
                    self.error.emit(f"Mixtral API Error: {resp.status_code} {resp.text}")
            else:
                self.error.emit("Unknown provider selected.")
        except Exception as e:
            self.error.emit(str(e))

# --- Chat Bubble Widget ---
class ChatBubble(QLabel):
    def __init__(self, text, is_user):
        super().__init__(text)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setStyleSheet(f"""
            QLabel {{
                border-radius: 12px;
                padding: 10px 16px;
                margin: 6px;
                background: {'#d1eaff' if is_user else '#f0f0f0'};
                color: #222;
                font-size: 15px;
                max-width: 600px;
            }}
        """)
        self.setAlignment(Qt.AlignLeft if not is_user else Qt.AlignRight)

# --- Main LLMTab Widget ---
class LLMTab(QWidget):
    def __init__(self):
        super().__init__()
        # API keys (use environment variables or config file)
        self.api_keys = {
            "Groq": os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE"),
            "Cohere": os.getenv("COHERE_API_KEY", "YOUR_COHERE_API_KEY_HERE"),
            "OpenRouter": os.getenv("OPENROUTER_API_KEY", "YOUR_OPENROUTER_API_KEY_HERE"),
            "GoogleGemini": os.getenv("GOOGLE_GEMINI_API_KEY", "YOUR_GOOGLE_GEMINI_API_KEY_HERE"),
            "Cerebras": os.getenv("CEREBRAS_API_KEY", "YOUR_CEREBRAS_API_KEY_HERE"),
            "Mistral": os.getenv("MISTRAL_API_KEY", "YOUR_MISTRAL_API_KEY_HERE"),
            "Mixtral": os.getenv("MIXTRAL_API_KEY", "YOUR_MIXTRAL_API_KEY_HERE")
        }
        # Model names for each provider
        self.model_map = {
            "Groq": "llama3-70b-8192",
            "Cohere": "command-r-plus",
            "OpenRouter": "deepseek/deepseek-chat-v3-0324",
            "GoogleGemini": "gemini-2.5-flash",
            "Cerebras": "cerebras/cerebras-gpt-4-256k",
            "Mistral": "mistralai/mistral-7b-instruct",
            "Mixtral": "mistralai/mixtral-8x7b-instruct"
        }
        self.selected_provider = "Groq"
        self.init_ui()
        self.worker = None

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # History button
        history_btn = QPushButton("View History")
        history_btn.setStyleSheet("padding: 6px 16px; font-size: 15px; border-radius: 6px; background: #f5f5f5; border: 1px solid #bbb;")
        history_btn.clicked.connect(self.show_history_dialog)
        layout.addWidget(history_btn, alignment=Qt.AlignRight)

        # Provider selection checkboxes
        provider_layout = QHBoxLayout()
        provider_label = QLabel("Provider:")
        provider_layout.addWidget(provider_label)
        self.provider_checkboxes = {}
        for name, label in [
            ("Groq", "Groq"),
            ("Cohere", "Cohere"),
            ("OpenRouter", "DeepSeek"),
            ("GoogleGemini", "Gemini"),
            ("Cerebras", "Cerebras"),
            ("Mistral", "Mistral"),
            ("Mixtral", "Mixtral")
        ]:
            cb = QCheckBox(label)
            cb.setChecked(name == self.selected_provider)
            cb.toggled.connect(lambda checked, n=name: self.on_provider_checked(n, checked))
            cb.setStyleSheet('''
                QCheckBox {
                    border: 2px solid #222;
                    border-radius: 6px;
                    padding: 6px 16px;
                    background: #fff;
                    color: #222;
                    font-size: 15px;
                    margin-right: 8px;
                }
                QCheckBox::indicator { width: 0; height: 0; }
                QCheckBox:checked {
                    background: #2196f3;
                    color: #fff;
                    border: 2px solid #2196f3;
                }
            ''')
            self.provider_checkboxes[name] = cb
            provider_layout.addWidget(cb)
        provider_layout.addStretch(1)
        layout.addLayout(provider_layout)

        # Chat history area (scrollable)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.addStretch(1)
        self.scroll_area.setWidget(self.chat_widget)
        layout.addWidget(self.scroll_area, stretch=1)

        # Input area with mic button
        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type your message and press Enter...")
        self.input_box.returnPressed.connect(self.send_message)
        self.input_box.setFocusPolicy(Qt.StrongFocus)
        input_layout.addWidget(self.input_box, stretch=1)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        # Mic button
        self.mic_btn = QPushButton()
        self.mic_btn.setIcon(QIcon.fromTheme("microphone") or QIcon())
        self.mic_btn.setText("🎤")
        self.mic_btn.setFixedWidth(36)
        self.mic_btn.setToolTip("Start Windows Dictation (Win+H)")
        self.mic_btn.clicked.connect(self.start_windows_dictation)
        input_layout.addWidget(self.mic_btn)
        layout.addLayout(input_layout)

        # Loading indicator
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.loading_label)

        # API key warning
        warn_msgs = []
        if self.api_keys["Cohere"] == "YOUR_COHERE_API_KEY_HERE":
            warn_msgs.append("Set your Cohere API key in llm_tab.py")
        if self.api_keys["OpenRouter"] == "YOUR_OPENROUTER_API_KEY_HERE":
            warn_msgs.append("Set your OpenRouter API key in llm_tab.py")
        if self.api_keys["GoogleGemini"] == "YOUR_GOOGLE_GEMINI_API_KEY_HERE":
            warn_msgs.append("Set your Google Gemini API key in llm_tab.py")
        if self.api_keys["Cerebras"] == "YOUR_CEREBRAS_API_KEY_HERE":
            warn_msgs.append("Set your Cerebras API key in llm_tab.py")
        if self.api_keys["Mistral"] == "YOUR_MISTRAL_API_KEY_HERE":
            warn_msgs.append("Set your Mistral API key in llm_tab.py")
        if self.api_keys["Mixtral"] == "YOUR_MIXTRAL_API_KEY_HERE":
            warn_msgs.append("Set your Mixtral API key in llm_tab.py")
        if warn_msgs:
            warn = QLabel("<b>" + "<br>".join(warn_msgs) + "</b>")
            warn.setStyleSheet("color: #b00; margin-bottom: 8px;")
            layout.insertWidget(0, warn)

        # Focus input box when tab is shown
        self.setFocusPolicy(Qt.StrongFocus)
        self.input_box.setFocus()

    def on_provider_checked(self, name, checked):
        if checked:
            # Uncheck all others
            for n, cb in self.provider_checkboxes.items():
                if n != name:
                    cb.setChecked(False)
            self.selected_provider = name
        else:
            # Prevent all from being unchecked
            if not any(cb.isChecked() for cb in self.provider_checkboxes.values()):
                self.provider_checkboxes[name].setChecked(True)

    def focusInEvent(self, event):
        self.input_box.setFocus()
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            self.input_box.setFocus()
        super().keyPressEvent(event)

    def add_message(self, text, is_user):
        bubble = ChatBubble(text, is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        # Save to DB
        save_convo_message(self.selected_provider, "user" if is_user else "assistant", text)
        # Scroll to bottom
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def send_message(self):
        prompt = self.input_box.text().strip()
        provider = self.selected_provider
        if not prompt:
            return
        if provider == "Groq" and self.api_keys["Groq"] == "":
            return
        if provider == "Cohere" and self.api_keys["Cohere"] == "YOUR_COHERE_API_KEY_HERE":
            return
        if provider == "OpenRouter" and self.api_keys["OpenRouter"] == "YOUR_OPENROUTER_API_KEY_HERE":
            return
        if provider == "GoogleGemini" and self.api_keys["GoogleGemini"] == "YOUR_GOOGLE_GEMINI_API_KEY_HERE":
            return
        if provider == "Cerebras" and self.api_keys["Cerebras"] == "YOUR_CEREBRAS_API_KEY_HERE":
            return
        if provider == "Mistral" and self.api_keys["Mistral"] == "YOUR_MISTRAL_API_KEY_HERE":
            return
        if provider == "Mixtral" and self.api_keys["Mixtral"] == "YOUR_MIXTRAL_API_KEY_HERE":
            return
        self.add_message(prompt, is_user=True)
        self.input_box.clear()
        self.loading_label.setText(f"{provider} is thinking...")
        self.send_btn.setEnabled(False)
        self.input_box.setEnabled(False)
        self.worker = LLMWorker(prompt, provider, self.api_keys, self.model_map)
        self.worker.result.connect(self.on_result)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_result(self, text):
        self.add_message(text, is_user=False)
        self.loading_label.setText("")
        self.send_btn.setEnabled(True)
        self.input_box.setEnabled(True)
        self.input_box.setFocus()

    def on_error(self, err):
        self.add_message(f"<b>Error:</b> {err}", is_user=False)
        self.loading_label.setText("")
        self.send_btn.setEnabled(True)
        self.input_box.setEnabled(True)
        self.input_box.setFocus()

    def start_windows_dictation(self):
        # This will open the Windows dictation bar (Win+H)
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(0x5B, 0, 0, 0)  # Win (Left Windows key)
            user32.keybd_event(0x48, 0, 0, 0)  # H
            user32.keybd_event(0x48, 0, 2, 0)  # H up
            user32.keybd_event(0x5B, 0, 2, 0)  # Win up
            self.input_box.setFocus()
        except Exception as e:
            self.add_message(f"<b>Error starting dictation:</b> {e}", is_user=False)

    def show_history_dialog(self):
        # Paginated history dialog
        class HistoryDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("LLM Conversation History")
                self.setMinimumSize(700, 500)
                self.vbox = QVBoxLayout(self)
                self.vbox.setContentsMargins(16, 16, 16, 16)
                self.vbox.setSpacing(8)
                self.scroll = QScrollArea()
                self.scroll.setWidgetResizable(True)
                self.content = QWidget()
                self.content_layout = QVBoxLayout(self.content)
                self.content_layout.setSpacing(6)
                self.scroll.setWidget(self.content)
                self.vbox.addWidget(self.scroll)
                self.see_more_btn = QPushButton("See More")
                self.see_more_btn.setStyleSheet("padding: 6px 16px; font-size: 15px; border-radius: 6px; background: #f5f5f5; border: 1px solid #bbb;")
                self.see_more_btn.clicked.connect(self.load_more)
                self.vbox.addWidget(self.see_more_btn, alignment=Qt.AlignRight)
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(self.accept)
                self.vbox.addWidget(close_btn, alignment=Qt.AlignRight)
                self.offset = 0
                self.page_size = 10
                self.has_more = True
                self.load_more()

            def load_more(self):
                conn = sqlite3.connect(get_db_path())
                c = conn.cursor()
                c.execute("SELECT timestamp, provider, role, message FROM llm_conversations ORDER BY id DESC LIMIT ? OFFSET ?", (self.page_size, self.offset))
                rows = c.fetchall()
                conn.close()
                for ts, provider, role, msg in rows:
                    frame = QFrame()
                    frame.setFrameShape(QFrame.StyledPanel)
                    frame.setStyleSheet("background: #f8faff; border-radius: 8px; padding: 8px; border: 1px solid #e0e0e0;")
                    f_layout = QVBoxLayout(frame)
                    meta = QLabel(f"<b>{provider}</b> | <span style='color:#2196f3'>{role.capitalize()}</span> | <span style='color:#888'>{LLMTab.format_datetime(ts)}</span>")
                    meta.setStyleSheet("font-size: 13px; margin-bottom: 2px;")
                    msg_lbl = QLabel(msg)
                    msg_lbl.setWordWrap(True)
                    msg_lbl.setStyleSheet("font-size: 15px; color: #222;")
                    f_layout.addWidget(meta)
                    f_layout.addWidget(msg_lbl)
                    self.content_layout.addWidget(frame)
                self.offset += len(rows)
                if len(rows) < self.page_size:
                    self.see_more_btn.hide()
                else:
                    self.see_more_btn.show()

        dialog = HistoryDialog(self)
        dialog.exec()

    @staticmethod
    def format_datetime(ts):
        try:
            dt = datetime.fromisoformat(ts)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ts 