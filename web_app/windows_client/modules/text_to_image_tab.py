import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QRadioButton, QButtonGroup, QGroupBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QThread, Signal
import time

class StarryAIWorker(QThread):
    finished = Signal(QImage)
    error = Signal(str)

    def __init__(self, prompt, api_key):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key

    def run(self):
        url = "https://api.starryai.com/creations/"
        headers = {
            "X-API-Key": self.api_key,
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "prompt": self.prompt
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=60)
            if resp.status_code in (200, 201):
                result = resp.json()
                creation_id = result.get("id")
                if not creation_id:
                    self.error.emit("No creation ID returned by StarryAI.")
                    return
                # Poll for image completion
                image_url = self.poll_starryai_image(creation_id, self.api_key)
                if image_url:
                    img_resp = requests.get(image_url, timeout=60)
                    if img_resp.status_code == 200:
                        image = QImage()
                        image.loadFromData(img_resp.content)
                        if image.isNull():
                            self.error.emit("Failed to load image from StarryAI response.")
                            return
                        self.finished.emit(image)
                    else:
                        self.error.emit("Failed to download image from StarryAI.")
                else:
                    self.error.emit("Image not available after polling StarryAI.")
            else:
                self.error.emit(f"StarryAI API error: {resp.status_code} {resp.text}")
        except Exception as e:
            self.error.emit(f"An error occurred: {e}")

    def poll_starryai_image(self, creation_id, api_key, max_attempts=24, delay=5):
        url = f"https://api.starryai.com/creations/{creation_id}/"
        headers = {
            "X-API-Key": api_key,
            "accept": "application/json"
        }
        last_result = None
        for attempt in range(max_attempts):
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                last_result = result
                # Try all possible fields for the image URL
                image_url = result.get("image_url") or result.get("output_url")
                if not image_url and "images" in result and isinstance(result["images"], list):
                    for img in result["images"]:
                        if isinstance(img, dict) and img.get("url"):
                            image_url = img["url"]
                            break
                status = result.get("status")
                if image_url and status in ("completed", "succeeded", "success"):
                    return image_url
                elif status == "failed":
                    break
            time.sleep(delay)
        # If we get here, show the last response for debugging
        if last_result:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "StarryAI Polling Debug", f"Last response: {last_result}")
        return None

class TextToImageTab(QWidget):
    def __init__(self):
        super().__init__()
        self.starryai_worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Provider selection
        provider_group = QGroupBox("Image Generation Provider")
        provider_layout = QHBoxLayout()
        self.radio_pollinations = QRadioButton("Pollinations (Free)")
        self.radio_starryai = QRadioButton("StarryAI")
        self.radio_pollinations.setChecked(True)
        provider_layout.addWidget(self.radio_pollinations)
        provider_layout.addWidget(self.radio_starryai)
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        self.button_group = QButtonGroup()
        self.button_group.addButton(self.radio_pollinations)
        self.button_group.addButton(self.radio_starryai)
        self.button_group.buttonClicked.connect(self.on_provider_changed)

        # API key input for StarryAI
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("StarryAI API Key (required for StarryAI)")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setVisible(False)
        self.api_key_input.setText(self.get_starryai_api_key())
        layout.addWidget(self.api_key_input)

        # Prompt input
        prompt_layout = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter your image prompt here...")
        self.generate_btn = QPushButton("Generate Image")
        self.generate_btn.clicked.connect(self.generate_image)
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addWidget(self.generate_btn)
        layout.addLayout(prompt_layout)

        self.image_label = QLabel("Image will appear here")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(300)
        layout.addWidget(self.image_label)

        self.setLayout(layout)

    def on_provider_changed(self):
        # Show/hide API key input based on provider
        self.api_key_input.setVisible(self.radio_starryai.isChecked())

    def generate_image(self):
        prompt = self.prompt_input.text().strip()
        if not prompt:
            QMessageBox.warning(self, "Input Error", "Please enter a prompt.")
            return
        if self.radio_pollinations.isChecked():
            self.generate_pollinations(prompt)
        elif self.radio_starryai.isChecked():
            api_key = self.get_starryai_api_key()
            self.api_key_input.setText(api_key)
            self.image_label.setText("Generating...")
            self.generate_btn.setEnabled(False)
            self.starryai_worker = StarryAIWorker(prompt, api_key)
            self.starryai_worker.finished.connect(self.on_starryai_image_ready)
            self.starryai_worker.error.connect(self.on_starryai_error)
            self.starryai_worker.start()

    def generate_pollinations(self, prompt):
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
        try:
            self.image_label.setText("Generating...")
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                image = QImage()
                image.loadFromData(resp.content)
                if image.isNull():
                    raise Exception("Failed to load image from response.")
                pixmap = QPixmap.fromImage(image)
                self.image_label.setPixmap(pixmap.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                QMessageBox.critical(self, "API Error", f"Failed to generate image. Status: {resp.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
        finally:
            self.generate_btn.setEnabled(True)

    def on_starryai_image_ready(self, image):
        pixmap = QPixmap.fromImage(image)
        self.image_label.setPixmap(pixmap.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.generate_btn.setEnabled(True)

    def on_starryai_error(self, message):
        QMessageBox.critical(self, "Error", message)
        self.image_label.setText("Image will appear here")
        self.generate_btn.setEnabled(True)

    def get_starryai_api_key(self):
        # Hardcoded StarryAI API key
        return "uZEq84ZOupA9jAtWQdzxPVfWe6vCtQ" 