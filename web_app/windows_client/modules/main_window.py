import os
import sys
import requests
import datetime
import subprocess
import mimetypes
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTextEdit, QFileDialog, QMessageBox, QDialog, QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon, QPainter, QImage
from PySide6.QtWidgets import QApplication
import ctypes

# Import other modules
from converter_tab import ConverterTab
from player_tab import PlayerTab
from search_tab import SearchTab
from upload_tab import UploadYTGTab
from daily_logs_tab import DailyLogsTab
from llm_tab import LLMTab
from text_to_image_tab import TextToImageTab
from command_tab import CommandTab

# Constants
MOBILE_UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "../mobile_uploads")
FLASK_URL = "http://localhost:5000/upload"


def get_wifi_ip_address():
    """
    Automatically detect the WiFi IP address of the current machine.
    Returns the IP address as a string, or None if not found.
    """
    try:
        # Method 1: Use socket to get local IP
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Check if it's a private IP (likely WiFi)
        if local_ip.startswith(('192.168.', '10.', '172.')):
            return local_ip
            
    except Exception:
        pass
    
    try:
        # Method 2: Use ipconfig command (Windows)
        import subprocess
        import re
        result = subprocess.run(['ipconfig'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            # Look for WiFi adapter IP
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if 'Wireless LAN adapter Wi-Fi' in line or 'Ethernet adapter' in line:
                    # Look for IPv4 address in the next few lines
                    for j in range(i, min(i + 10, len(lines))):
                        if 'IPv4 Address' in lines[j]:
                            # Extract IP address using regex
                            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', lines[j])
                            if ip_match:
                                return ip_match.group(1)
    except Exception:
        pass
    
    return None

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        print("=== MainWindow Initialization Started ===")
        print("🚀 App started - AI models will load when Command tab is opened")
        
        try:
            # Use default window frame (no frameless)
            self.setStyleSheet('''
                QWidget {
                    background: #ffffff;
                    color: #222222;
                    font-size: 15px;
                }
                QGroupBox {
                    border: 1px solid #cccccc;
                    border-radius: 6px;
                    margin-top: 10px;
                    background: #fafafa;
                }
                QGroupBox:title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                    color: #444444;
                    font-weight: bold;
                }
                QPushButton {
                    background: #f5f5f5;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                }
                QPushButton:pressed {
                    background: #d0d0d0;
                }
                QTextEdit {
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 8px;
                    background: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                    background: #ffffff;
                }
                QTabBar::tab {
                    background: #f0f0f0;
                    border: 1px solid #cccccc;
                    padding: 8px 16px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: #ffffff;
                    border-bottom: 1px solid #ffffff;
                }
            ''')
            print("✓ Style sheet applied")
            
            # Initialize command tab first
            self.command_tab = CommandTab()
            print("✓ Command tab initialized")
            
            self.init_ui()
            print("✓ UI initialized")
            
            print("=== MainWindow Initialization Completed ===")
            
        except Exception as e:
            print(f"✗ Error during MainWindow initialization: {e}")
            import traceback
            traceback.print_exc()
            raise

    def init_ui(self):
        tabs = QTabWidget()
        main_tab = QWidget()
        main_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.setWindowState(Qt.WindowMaximized)
        # self.showFullScreen()

        # Show detected IP address
        detected_ip = get_wifi_ip_address()
        if detected_ip:
            ip_info = QLabel(f"Detected IP: {detected_ip}")
            ip_info.setStyleSheet("color: green; font-weight: bold;")
            main_layout.addWidget(ip_info)
        else:
            ip_info = QLabel("IP detection failed. Please check network connection.")
            ip_info.setStyleSheet("color: red; font-weight: bold;")
            main_layout.addWidget(ip_info)

        # Camera section
        camera_layout = QHBoxLayout()
        camera_layout.addWidget(QLabel("Camera:"))
        self.img_label = QLabel()
        self.img_label.setFixedSize(800, 600)
        self.img_label.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        camera_layout.addWidget(self.img_label)
        main_layout.addLayout(camera_layout)

        # Buttons
        self.select_btn = QPushButton("Select Image")
        self.select_btn.clicked.connect(self.select_image)
        btn_layout.addWidget(self.select_btn)

        self.upload_btn = QPushButton("Upload")
        self.upload_btn.clicked.connect(self.upload_image)
        self.upload_btn.setEnabled(False)
        btn_layout.addWidget(self.upload_btn)

        self.mobile_btn = QPushButton("Check Mobile Uploads")
        self.mobile_btn.clicked.connect(self.check_mobile_uploads)
        btn_layout.addWidget(self.mobile_btn)

        self.view_files_btn = QPushButton("View Files")
        self.view_files_btn.clicked.connect(lambda: self.view_uploads_files())
        btn_layout.addWidget(self.view_files_btn)

        # Stop Camera button
        self.stop_camera_btn = QPushButton("Stop Camera")
        self.stop_camera_btn.clicked.connect(self.stop_camera)
        self.stop_camera_btn.setEnabled(False)  # Initially disabled
        btn_layout.addWidget(self.stop_camera_btn)

        # Theme toggle button
        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setFixedSize(40, 40)
        self.theme_btn.clicked.connect(self.toggle_theme)
        btn_layout.addWidget(self.theme_btn)

        main_layout.addLayout(btn_layout)

        # Result area
        self.result_text = QTextEdit()
        self.result_text.setPlaceholderText("ML result will appear here")
        self.result_text.setMaximumHeight(200)
        main_layout.addWidget(self.result_text)

        main_tab.setLayout(main_layout)

        # Create tabs
        converter_tab = ConverterTab()
        search_tab = SearchTab()
        upload_tab = UploadYTGTab()
        player_tab = PlayerTab()
        daily_logs_tab = DailyLogsTab()
        llm_tab = LLMTab()
        text_to_image_tab = TextToImageTab()
        command_tab = CommandTab()

        # Add tabs to tab widget
        tabs.addTab(main_tab, "Main")
        tabs.addTab(converter_tab, "Converter")
        tabs.addTab(search_tab, "Search")
        tabs.addTab(upload_tab, "Uploading YT/G")
        tabs.addTab(player_tab, "Player")
        tabs.addTab(daily_logs_tab, "Daily Logs")
        tabs.addTab(llm_tab, "LLM")
        tabs.addTab(text_to_image_tab, "Text to Image")
        tabs.addTab(self.command_tab, "Command")
        # Add refresh tab (icon only)
        refresh_tab = QWidget()
        tabs.addTab(refresh_tab, '⟳')
        self._last_tab_index = 0
        def on_tab_changed(idx):
            if idx == tabs.count() - 1:  # Refresh tab
                self.restart_app()
                # Switch back to previous tab after restart_app (if app doesn't close)
                tabs.setCurrentIndex(self._last_tab_index)
            else:
                self._last_tab_index = idx
        tabs.currentChanged.connect(on_tab_changed)

        # --- Main Layout ---
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(tabs)
        self.setLayout(layout)

    def toggle_theme(self):
        WHITE_STYLE = '''
            QWidget {
                background: #ffffff;
                color: #222222;
                font-size: 15px;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 10px;
                background: #fafafa;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #444444;
                font-weight: bold;
            }
            QPushButton {
                background: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                color: #222222;
            }
            QPushButton:checked, QPushButton:pressed {
                background: #e0e0e0;
                border: 1px solid #aaaaaa;
            }
            QPushButton:hover {
                background: #f0f0f0;
            }
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #eee;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #cccccc;
                border: 1px solid #888;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QListWidget {
                background: #ffffff;
                border: 1px solid #cccccc;
            }
            QLabel {
                color: #222222;
            }
            QProgressBar {
                background: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                color: #222222;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: #ffffff;
            }
            QTabBar::tab {
                background: #f5f5f5;
                color: #222222;
                padding: 8px 16px;
                border: 1px solid #cccccc;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-bottom: 2px solid #0078d7;
            }
            QTextEdit {
                background: #fafafa;
                color: #222222;
                border: 1px solid #cccccc;
            }
            QComboBox {
                background: #f5f5f5;
                color: #222222;
                border: 1px solid #cccccc;
                padding: 4px;
            }
            QLineEdit {
                background: #fafafa;
                color: #222222;
                border: 1px solid #cccccc;
                padding: 4px;
            }
        '''
        DARK_STYLE = '''
QWidget {
    background-color: #232629;
    color: #f0f0f0;
}
QLineEdit, QTextEdit, QComboBox, QTabWidget, QProgressBar {
    background-color: #31363b;
    color: #f0f0f0;
    border: 1px solid #555;
}
QTextEdit, QPlainTextEdit {
    background-color: #232629;
    color: #f0f0f0;
    border: 1px solid #555;
}
QLabel {
    color: #f0f0f0;
}
QPushButton {
    background-color: #444;
    color: #f0f0f0;
    border: 1px solid #666;
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton:hover {
    background-color: #555;
}
QTreeWidget, QTreeWidgetItem {
    background-color: #31363b;
    color: #f0f0f0;
}
QCheckBox {
    color: #f0f0f0;
}
QTabBar::tab:selected {
    background: #31363b;
    color: #f0f0f0;
}
QTabBar::tab:!selected {
    background: #232629;
    color: #aaa;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #232629;
}
'''
        if not self.is_dark_mode:
            QApplication.instance().setStyleSheet(DARK_STYLE)
            self.theme_btn.setText("☀️")
            self.is_dark_mode = True
            self.img_label.setStyleSheet("background: #181a1b; border: 1px solid #333;")
        else:
            QApplication.instance().setStyleSheet(WHITE_STYLE)
            self.theme_btn.setText("🌙")
            self.is_dark_mode = False
            self.img_label.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc;")

    def show_camera_icon(self):
        from PySide6.QtGui import QPixmap, QIcon, QPainter
        import os
        icons_dir = os.path.join(os.path.dirname(__file__), "../icons")
        camera_icon_path = os.path.join(icons_dir, "camera.png")
        # Use the current size of img_label for the pixmap
        w = self.img_label.width() if self.img_label.width() > 0 else 800
        h = self.img_label.height() if self.img_label.height() > 0 else 600
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        if os.path.exists(camera_icon_path):
            icon = QIcon(camera_icon_path)
            icon_pix = icon.pixmap(120, 120)
            painter.drawPixmap((w-120)//2, (h-120)//2, icon_pix)
        else:
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "[Camera]")
        painter.end()
        self.img_label.setPixmap(pixmap)
        self.img_label.mousePressEvent = self.camera_icon_clicked
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
            self.timer = None
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
            self.cap = None
        if hasattr(self, 'capture_overlay_btn'):
            self.capture_overlay_btn.hide()

    def camera_icon_clicked(self, event):
        self.start_camera_preview()

    def start_camera_preview(self):
        import cv2
        from PySide6.QtCore import QTimer
        # Try multiple backends for Windows webcam compatibility
        backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
        cap = None
        for backend in backends:
            try:
                cap = cv2.VideoCapture(0, backend)
                if cap.isOpened():
                    print(f"[Camera] Opened webcam with backend {backend}")
                    break
                else:
                    cap.release()
            except Exception as e:
                print(f"[Camera] Exception with backend {backend}: {e}")
        if not cap or not cap.isOpened():
            self.result_text.setText("Webcam not found.\nTried MSMF, DSHOW, and ANY backends.\nIf you have a webcam, make sure no other app is using it and try again.")
            print("[Camera] Webcam not found with any backend.")
            return
        self.cap = cap
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_camera_frame)
        self.timer.start(30)
        self.upload_btn.setEnabled(False)
        self.stop_camera_btn.setEnabled(True)
        
        # Ensure main tab stays enabled while other tabs are disabled
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            for i in range(tab_widget.count()):
                tab_widget.setTabEnabled(i, False)
            tab_widget.setTabEnabled(0, True)  # Keep main tab enabled
        
        # Add a capture button overlay
        if not hasattr(self, 'capture_overlay_btn'):
            from PySide6.QtWidgets import QPushButton
            self.capture_overlay_btn = QPushButton("Capture", self.img_label)
            self.capture_overlay_btn.setStyleSheet("background: rgba(255,255,255,0.8); font-size: 20px; border: 2px solid #333; border-radius: 8px;")
            self.capture_overlay_btn.setFixedSize(120, 48)
            self.capture_overlay_btn.move((self.img_label.width()-120)//2, self.img_label.height()-60)
            self.capture_overlay_btn.raise_()
            self.capture_overlay_btn.clicked.connect(self.capture_from_camera)
        self.capture_overlay_btn.show()
        self.img_label.mousePressEvent = None

    def update_camera_frame(self):
        import cv2
        if not hasattr(self, 'cap') or self.cap is None:
            # Defensive: stop timer if running
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
                self.timer = None
            self.stop_camera_btn.setEnabled(False)
            return
        ret, frame = self.cap.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            label_w = self.img_label.width()
            label_h = self.img_label.height()
            qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img).scaled(label_w, label_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.img_label.setPixmap(pixmap)
            self._last_camera_frame = frame
        else:
            self.result_text.setText("Camera error. Stopping preview.")
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
                self.timer = None
            if hasattr(self, 'cap') and self.cap:
                self.cap.release()
                self.cap = None
            self.stop_camera_btn.setEnabled(False)
            self.show_camera_icon()

    def capture_from_camera(self):
        # Called when the overlay 'Capture' button is pressed
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
            self.timer = None
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
            self.cap = None
        if hasattr(self, 'capture_overlay_btn'):
            self.capture_overlay_btn.hide()
        self.stop_camera_btn.setEnabled(False)
        
        # Re-enable all tabs when camera is stopped
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            for i in range(tab_widget.count()):
                tab_widget.setTabEnabled(i, True)
        
        if hasattr(self, '_last_camera_frame'):
            import cv2
            rgb = cv2.cvtColor(self._last_camera_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            label_w = self.img_label.width()
            label_h = self.img_label.height()
            qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img).scaled(label_w, label_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.img_label.setPixmap(pixmap)
            # Save the captured image as bytes for upload
            import numpy as np
            import io
            import PIL.Image
            pil_img = PIL.Image.fromarray(cv2.cvtColor(self._last_camera_frame, cv2.COLOR_BGR2RGB))
            buf = io.BytesIO()
            pil_img.save(buf, format='JPEG')
            self.image_data = buf.getvalue()
            self.image_path = None
            self.upload_btn.setEnabled(True)
            # Clicking the image will reopen the camera
            def reopen_camera(event):
                self.show_camera_icon()
                self.start_camera_preview()
            self.img_label.mousePressEvent = reopen_camera

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            self.image_data = None
            pixmap = QPixmap(file_path).scaled(self.img_label.width(), self.img_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.img_label.setPixmap(pixmap)
            self.upload_btn.setEnabled(True)
            self.img_label.mousePressEvent = None
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
                self.timer = None
            if hasattr(self, 'cap') and self.cap:
                self.cap.release()
                self.cap = None
            if hasattr(self, 'capture_overlay_btn'):
                self.capture_overlay_btn.hide()
            self.stop_camera_btn.setEnabled(False)
            
            # Re-enable all tabs when camera is stopped
            tab_widget = self.findChild(QTabWidget)
            if tab_widget:
                for i in range(tab_widget.count()):
                    tab_widget.setTabEnabled(i, True)
        else:
            self.show_camera_icon()

    def upload_image(self):
        self.result_text.setText("Uploading...")
        files = None
        import datetime
        if self.image_path:
            files = {'file': open(self.image_path, 'rb')}
            img_bytes = open(self.image_path, 'rb').read()
        elif self.image_data:
            dt_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = f"capture_{dt_str}.jpg"
            files = {'file': (fname, self.image_data, 'image/jpeg')}
            img_bytes = self.image_data
        else:
            self.result_text.setText("No image to upload.")
            return
        try:
            resp = requests.post(FLASK_URL, files=files)
            if resp.ok:
                self.result_text.setText(f"Result: {resp.json().get('result', resp.text)}")
            else:
                self.result_text.setText(f"Upload failed: {resp.status_code}\n{resp.text}")
        except Exception as e:
            self.result_text.setText(f"Error: {e}")
        if self.image_path:
            files['file'].close()

    def check_mobile_uploads(self):
        # Show all files in web_app/mobile_uploads in a dialog with thumbnails for images
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget, QHBoxLayout, QCheckBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem
        import mimetypes, shutil
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        uploads_dir = os.path.join(project_root, 'web_app', 'uploads')
        send_to_mobile_dir = os.path.join(project_root, 'web_app', 'send_to_mobile')
        if not os.path.exists(uploads_dir):
            QMessageBox.information(self, "Notification", "No files found in uploads.")
            return
        files = os.listdir(uploads_dir)
        if not files:
            QMessageBox.information(self, "Notification", "No files found in uploads.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Uploads (web_app/web_app/uploads)")
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout()
        checkboxes = []
        for fname in files:
            row = QHBoxLayout()
            cb = QCheckBox(fname)
            checkboxes.append(cb)
            row.addWidget(cb)
            # Show thumbnail for images
            file_path = os.path.join(uploads_dir, fname)
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('image/'):
                try:
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        thumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumb_label = QLabel()
                        thumb_label.setPixmap(thumbnail)
                        thumb_label.setFixedSize(100, 100)
                        row.addWidget(thumb_label)
                except Exception:
                    pass
            content_layout.addLayout(row)
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        button_layout = QHBoxLayout()
        def send_to_mobile():
            selected_files = [fname for cb, fname in zip(checkboxes, files) if cb.isChecked()]
            if not selected_files:
                QMessageBox.warning(dialog, "No Selection", "Please select files to send to mobile.")
                return
            os.makedirs(send_to_mobile_dir, exist_ok=True)
            for fname in selected_files:
                src = os.path.join(uploads_dir, fname)
                dst = os.path.join(send_to_mobile_dir, fname)
                shutil.copy2(src, dst)
            QMessageBox.information(dialog, "Success", f"Sent {len(selected_files)} files to mobile.")
            dialog.accept()
        def delete_files():
            selected_files = [fname for cb, fname in zip(checkboxes, files) if cb.isChecked()]
            if not selected_files:
                QMessageBox.warning(dialog, "No Selection", "Please select files to delete.")
                return
            reply = QMessageBox.question(dialog, "Confirm Delete", f"Delete {len(selected_files)} files?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                for fname in selected_files:
                    os.remove(os.path.join(uploads_dir, fname))
                QMessageBox.information(dialog, "Success", f"Deleted {len(selected_files)} files.")
                dialog.accept()
        send_btn = QPushButton("Send to Mobile")
        send_btn.clicked.connect(send_to_mobile)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(delete_files)
        button_layout.addWidget(send_btn)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def view_uploads_files(self, start_dir=None):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QWidget, QSizePolicy
        import mimetypes, shutil, os
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QPixmap
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        uploads_root = os.path.join(project_root, 'web_app', 'uploads')
        if start_dir is None:
            current_dir = uploads_root
        else:
            current_dir = start_dir
        if not os.path.exists(current_dir):
            QMessageBox.information(self, "Notification", f"No files found in {current_dir}.")
            return
        files = os.listdir(current_dir)
        if not files:
            QMessageBox.information(self, "Notification", f"No files found in {current_dir}.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Uploads ({os.path.relpath(current_dir, uploads_root) or '.'})")
        main_layout = QHBoxLayout()
        # --- Tree Widget ---
        tree = QTreeWidget()
        tree.setColumnCount(3)
        tree.setHeaderLabels(["Name", "Type", "Size"])
        tree.setSelectionMode(QAbstractItemView.SingleSelection)
        tree.setStyleSheet('''
            QTreeView::indicator:unchecked {
                width: 24px;
                height: 24px;
                background: #fff;
                border: 1px solid #bbb;
            }
            QTreeView::indicator:checked {
                width: 24px;
                height: 24px;
                background: #0078d7;
                border: 1px solid #0078d7;
            }
            QTreeWidget::item {
                padding: 8px 0px 8px 0px;
                font-size: 15px;
            }
            QTreeWidget::item:selected {
                background: #e0e0e0;
                color: #222222;
            }
        ''')
        self._tree_checkboxes = []
        def add_items(parent, dir_path):
            entries = sorted(os.listdir(dir_path))
            for fname in entries:
                fpath = os.path.join(dir_path, fname)
                if os.path.isdir(fpath):
                    item = QTreeWidgetItem(parent, [fname, "Folder", ""])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Unchecked)
                    self._tree_checkboxes.append((item, fpath))
                    add_items(item, fpath)
                else:
                    ext = os.path.splitext(fname)[1]
                    size = os.path.getsize(fpath)
                    size_str = f"{size // 1024} KB" if size >= 1024 else f"{size} B"
                    item = QTreeWidgetItem(parent, [fname, ext, size_str])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Unchecked)
                    self._tree_checkboxes.append((item, fpath))
        add_items(tree.invisibleRootItem(), current_dir)
        tree.expandAll()
        main_layout.addWidget(tree)
        # --- Preview Pane ---
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_label = QLabel("<i>Select a file to preview</i>")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setWordWrap(True)
        preview_label.setMinimumSize(300, 200)
        preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_layout.addWidget(preview_label)
        main_layout.addWidget(preview_widget)
        def show_preview(item, col):
            fpath = None
            for chk_item, path in self._tree_checkboxes:
                if chk_item is item:
                    fpath = path
                    break
            if not fpath or os.path.isdir(fpath):
                preview_label.setText("<i>Select a file to preview</i>")
                preview_label.setPixmap(QPixmap())
                return
            mimetype, _ = mimetypes.guess_type(fpath)
            if mimetype and mimetype.startswith('image'):
                pixmap = QPixmap(fpath)
                if not pixmap.isNull():
                    preview_label.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    preview_label.setText("[Image]")
            elif mimetype and mimetype.startswith('video'):
                try:
                    import cv2
                    cap = cv2.VideoCapture(fpath)
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        import numpy as np
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb.shape
                        bytes_per_line = ch * w
                        from PySide6.QtGui import QImage
                        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(qt_img)
                        preview_label.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    else:
                        preview_label.setText("[Video]")
                except Exception:
                    preview_label.setText("[Video]")
            else:
                info = f"<b>{os.path.basename(fpath)}</b><br>Type: {mimetype or 'Unknown'}<br>Size: {os.path.getsize(fpath)} bytes"
                preview_label.setText(info)
                preview_label.setPixmap(QPixmap())
        # Remove preview on single-click
        # tree.itemClicked.connect(show_preview)
        # Add preview on double-click
        tree.itemDoubleClicked.connect(show_preview)
        # --- Bulk Action Buttons ---
        btn_row = QVBoxLayout()
        send_btn = QPushButton("Send to Mobile")
        delete_btn = QPushButton("Delete")
        btn_row.addWidget(send_btn)
        btn_row.addWidget(delete_btn)
        def collect_checked_files():
            files = []
            for item, fpath in self._tree_checkboxes:
                if item.checkState(0) == Qt.Checked and os.path.isfile(fpath):
                    files.append(fpath)
            return files
        def send_to_mobile():
            selected_files = collect_checked_files()
            if not selected_files:
                QMessageBox.warning(dialog, "No Selection", "Please select files to send to mobile.")
                return
            send_to_mobile_dir = os.path.join(project_root, 'web_app', 'send_to_mobile')
            os.makedirs(send_to_mobile_dir, exist_ok=True)
            for file_path in selected_files:
                fname = os.path.basename(file_path)
                dst = os.path.join(send_to_mobile_dir, fname)
                shutil.copy2(file_path, dst)
            QMessageBox.information(dialog, "Success", f"Sent {len(selected_files)} files to mobile.")
        def delete_files():
            selected_files = collect_checked_files()
            if not selected_files:
                QMessageBox.warning(dialog, "No Selection", "Please select files to delete.")
                return
            reply = QMessageBox.question(dialog, "Confirm Delete", f"Delete {len(selected_files)} files?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                for file_path in selected_files:
                    os.remove(file_path)
                QMessageBox.information(dialog, "Success", f"Deleted {len(selected_files)} files.")
                dialog.accept()
        send_btn.clicked.connect(send_to_mobile)
        delete_btn.clicked.connect(delete_files)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)
        dialog.setLayout(main_layout)
        dialog.resize(900, 600)
        dialog.exec()

    def stop_camera(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
            self.timer = None
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
            self.cap = None
        if hasattr(self, 'capture_overlay_btn'):
            self.capture_overlay_btn.hide()
        self.stop_camera_btn.setEnabled(False)
        
        # Re-enable all tabs when camera is stopped
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            for i in range(tab_widget.count()):
                tab_widget.setTabEnabled(i, True)
        
        self.show_camera_icon()
        self.img_label.mousePressEvent = self.camera_icon_clicked

    def closeEvent(self, event):
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        # Clean up player tab if it exists
        try:
            for i in range(self.layout().count()):
                item = self.layout().itemAt(i)
                if hasattr(item, 'widget') and item.widget():
                    if hasattr(item.widget(), 'cleanup_media'):
                        item.widget().cleanup_media()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        event.accept() 

    def restart_app(self):
        import sys, os, subprocess
        python = sys.executable
        script = sys.argv[0]
        args = sys.argv[1:]
        subprocess.Popen([python, script] + args)
        self.close()

    def header_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def header_mouse_move(self, event):
        if self._drag_active and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def header_mouse_release(self, event):
        self._drag_active = False
        event.accept() 