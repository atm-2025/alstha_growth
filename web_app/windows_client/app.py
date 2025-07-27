import os

import sys
import requests
import cv2
import socket
import subprocess
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QTextEdit, QHBoxLayout, QMessageBox, QTabWidget, QComboBox, QLineEdit, QProgressBar, QInputDialog, QSizePolicy, QCheckBox, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QListWidget, QGroupBox, QSlider, QStyle, QFrame
)
from PySide6.QtGui import QPixmap, QImage, QIcon, QTextCursor
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QEventLoop, QObject, QSize, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import numpy as np
import os
import glob
import time
import threading
import signal
import webbrowser
import functools
import tempfile
import datetime

FLASK_URL = "http://127.0.0.1:5000/upload"  # Change to your Flask server IP if needed

MOBILE_UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'mobile_uploads')

# Ensure yt_downloader from the converter folder is importable
CONVERTER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web_app/converter'))
if CONVERTER_PATH not in sys.path:
    sys.path.insert(0, CONVERTER_PATH)

UPLOAD_JSON_DIR = os.path.join(os.path.dirname(__file__), 'upload-json')
os.makedirs(UPLOAD_JSON_DIR, exist_ok=True)

def get_wifi_ip_address():
    """
    Automatically detect the WiFi IP address of the current machine.
    Returns the IP address as a string, or None if not found.
    """
    try:
        # Method 1: Use socket to get local IP
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

class FileWithProgress:
    def __init__(self, file_path, progress_callback, cancel_flag):
        self.file = open(file_path, 'rb')
        self.size = self._get_size()
        self.progress_callback = progress_callback
        self.bytes_read = 0
        self.cancel_flag = cancel_flag
    def _get_size(self):
        return os.path.getsize(self.file.name)
    def read(self, chunk_size=-1):
        if self.cancel_flag() and chunk_size != 0:
            raise Exception('Upload cancelled by user.')
        chunk = self.file.read(chunk_size)
        self.bytes_read += len(chunk)
        if self.size > 0:
            self.progress_callback(self.bytes_read, self.size)
        return chunk
    def __getattr__(self, attr):
        return getattr(self.file, attr)
    def close(self):
        self.file.close()

class ConverterWorker(QThread):
    progress_update = Signal(int, int, str, float, float)  # current, total, message, elapsed, est_remaining
    file_result = Signal(str, str)
    finished = Signal(int, int)
    file_progress = Signal(int, str)  # percent, phase ('upload' or 'convert')

    def __init__(self, file_paths, conversion, server, data, save_ext):
        super().__init__()
        self.file_paths = file_paths
        self.conversion = conversion
        self.server = server
        self.data = data
        self.save_ext = save_ext
        self._is_running = True
        self._cancel_requested = False
        self.start_time = None
        self.last_update_time = None
        self.files_done = 0
        self.current_subprocess = None

    def run(self):
        import requests
        import subprocess
        success = 0
        fail = 0
        total = len(self.file_paths)
        self.start_time = time.time()
        for idx, file_path in enumerate(self.file_paths, 1):
            if not self._is_running or self._cancel_requested:
                break
            elapsed = time.time() - self.start_time
            est_remaining = (elapsed / idx) * (total - idx) if idx > 0 else 0
            self.progress_update.emit(idx, total, f"Uploading: {file_path}", elapsed, est_remaining)
            def progress_callback(bytes_read, total_size):
                percent = int((bytes_read / total_size) * 100)
                self.file_progress.emit(percent, 'upload')
            file_obj = FileWithProgress(file_path, progress_callback, lambda: self._cancel_requested)
            files = {'file': (file_path, file_obj)}
            try:
                resp = requests.post(self.server, files=files, data=self.data, timeout=3600)
                file_obj.close()
                self.file_progress.emit(100, 'upload')
                # Now show converting phase (indeterminate)
                self.progress_update.emit(idx, total, f"Converting: {file_path}", elapsed, est_remaining)
                self.file_progress.emit(-1, 'convert')  # -1 means indeterminate
                # Wait for server response (already done above)
                if resp.ok:
                    out_path = file_path + "_converted" + self.save_ext
                    with open(out_path, 'wb') as f:
                        f.write(resp.content)
                    self.file_result.emit(file_path, f"Success: {file_path} → {out_path}")
                    success += 1
                else:
                    self.file_result.emit(file_path, f"Failed: {file_path} ({resp.status_code})\n{resp.text}")
                    fail += 1
            except Exception as e:
                self.file_result.emit(file_path, f"Error: {file_path} ({e})")
                fail += 1
            if self._cancel_requested:
                break
        self.finished.emit(success, fail)

    def stop(self):
        self._is_running = False
        self._cancel_requested = True
        # Kill any running subprocess
        if self.current_subprocess:
            try:
                self.current_subprocess.terminate()
            except Exception:
                pass

class ConverterTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.file_paths = []
        self.selected_type = None
        self.worker = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_labels)
        self.elapsed_time = 0
        self.est_remaining = 0
        self.current_phase = 'upload'

        self.setAcceptDrops(True)  # Enable drag-and-drop

        # Server IP input with auto-detection
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("Server IP:"))
        
        # Auto-detect IP address
        detected_ip = get_wifi_ip_address()
        if detected_ip:
            # Split IP into parts for easier editing
            ip_parts = detected_ip.split('.')
            if len(ip_parts) == 4:
                self.ip_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}."
                self.ip_last = QLineEdit()
                self.ip_last.setText(ip_parts[3])
                self.ip_last.setFixedWidth(40)
                ip_layout.addWidget(QLabel(self.ip_prefix))
                ip_layout.addWidget(self.ip_last)
            else:
                # Fallback to full IP input
                self.ip_prefix = ""
                self.ip_last = QLineEdit()
                self.ip_last.setText(detected_ip)
                self.ip_last.setFixedWidth(120)
                ip_layout.addWidget(self.ip_last)
        else:
            # Fallback to manual input
            self.ip_prefix = "192.168.1."
            self.ip_last = QLineEdit()
            self.ip_last.setPlaceholderText("5")
            self.ip_last.setFixedWidth(40)
            ip_layout.addWidget(QLabel(self.ip_prefix))
            ip_layout.addWidget(self.ip_last)
        
        # Add refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh IP Address\nClick to auto-detect current WiFi IP")
        refresh_btn.setFixedWidth(30)
        refresh_btn.clicked.connect(self.refresh_ip_address)
        ip_layout.addWidget(refresh_btn)
        
        layout.addLayout(ip_layout)

        self.select_btn = QPushButton("Select Files")
        self.select_btn.clicked.connect(self.select_files)
        layout.addWidget(self.select_btn)

        self.combo = QComboBox()
        self.combo.addItems([
            "MP4 to MP3",
            "JPG to PNG",
            "PNG to JPG",
            "Word to PDF",
            "Archive to ZIP",
            "Extract ZIP",
            "MP3 to WAV",
            "WAV to MP3",
            "GIF to MP4",
            "MP4 to GIF",
            "PNG/JPG to ICO",
            "JPG/PNG to SVG",
            "SVG to PNG",
            "SVG to JPG",
            "M4A to MP3",
            "MP3 to M4A",
            "Text to QR",
            "QR to Text",
            "Image to Text (OCR)",
            "PDF to Text (OCR)",
            "Text to MP3",
            "Text to WAV",
            "YouTube Video to MP3 (native)",
            "YouTube Video to MP4 (native)",
            "YouTube Playlist to MP3 (native)",
            "YouTube Playlist to MP4 (native)",
            "YouTube Video to Transcript (TXT)"  # NEW OPTION
        ])
        self.combo.currentIndexChanged.connect(self.update_input_mode)
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("")
        self.input_box.setVisible(False)
        self.input_box.textChanged.connect(self.on_input_box_changed)
        layout.addWidget(self.input_box)
        layout.addWidget(self.combo)

        self.convert_btn = QPushButton("Convert")
        self.convert_btn.clicked.connect(self.convert_files)
        self.convert_btn.setEnabled(False)
        layout.addWidget(self.convert_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        layout.addWidget(self.cancel_btn)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.file_progress = QProgressBar()
        self.file_progress.setValue(0)
        self.file_progress.setVisible(False)
        layout.addWidget(self.file_progress)
        self.file_progress.setFormat('')

        self.phase_label = QLabel('')
        self.phase_label.setVisible(False)
        layout.addWidget(self.phase_label)

        time_layout = QHBoxLayout()
        self.elapsed_label = QLabel("Elapsed: 00:00")
        self.est_label = QLabel("Est. Remaining: 00:00")
        time_layout.addWidget(self.elapsed_label)
        time_layout.addWidget(self.est_label)
        layout.addLayout(time_layout)

        self.status = QTextEdit()
        self.status.setReadOnly(True)
        layout.addWidget(self.status)
        
        # Show current IP status
        detected_ip = get_wifi_ip_address()
        if detected_ip:
            self.status.append(f"✅ Auto-detected IP: {detected_ip}")
        else:
            self.status.append("⚠️ Could not auto-detect IP. Please check network connection.")

        self.setLayout(layout)

        # Ensure worker is stopped on close
        self._app = QApplication.instance()
        self._app.aboutToQuit.connect(self.handle_app_close)
        self.update_input_mode()  # Set initial state

    def handle_app_close(self):
        if self.worker:
            self.worker.stop()
            if self.worker.isRunning():
                self.worker.wait()
        # Force exit after a short delay to ensure all threads/subprocesses are killed
        QTimer.singleShot(500, lambda: os._exit(0))

    def get_server_url(self):
        last = self.ip_last.text().strip()
        if self.ip_prefix:
            # Split IP format (e.g., "192.168.1.")
            if not last.isdigit():
                return None
            return f"{self.ip_prefix}{last}"
        else:
            # Full IP format
            if not last:
                return None
            return last

    def refresh_ip_address(self):
        """Refresh the IP address by auto-detecting it again"""
        detected_ip = get_wifi_ip_address()
        if detected_ip:
            ip_parts = detected_ip.split('.')
            if len(ip_parts) == 4:
                self.ip_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}."
                self.ip_last.setText(ip_parts[3])
                # Update the label
                for i in range(self.layout().count()):
                    item = self.layout().itemAt(i)
                    if isinstance(item, QHBoxLayout) and item.count() > 1:
                        label_item = item.itemAt(1)
                        if isinstance(label_item.widget(), QLabel):
                            label_item.widget().setText(self.ip_prefix)
                            break
            else:
                self.ip_prefix = ""
                self.ip_last.setText(detected_ip)
            self.status.append(f"🔄 IP refreshed to: {detected_ip}")
            QMessageBox.information(self, "IP Refresh", f"IP address updated to: {detected_ip}")
        else:
            self.status.append("❌ Failed to detect IP address")
            QMessageBox.warning(self, "IP Refresh", "Could not detect IP address. Please enter manually.")

    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "Text Files (*.txt);;All Files (*)")
        if file_paths:
            self.file_paths = file_paths
            self.status.setText(f"Selected: {len(file_paths)} files\n" + '\n'.join(file_paths))
            # For text_types, enable convert if .txt file is selected or input_box has text
            conversion = self.combo.currentText()
            text_types = ["Text to MP3", "Text to WAV", "Text to QR"]
            if conversion in text_types:
                has_txt_file = bool(self.file_paths) and self.file_paths[0].lower().endswith('.txt')
                has_text = bool(self.input_box.text().strip())
                self.convert_btn.setEnabled(has_txt_file or has_text)
            else:
                self.convert_btn.setEnabled(True)

    def update_input_mode(self):
        conversion = self.combo.currentText()
        yt_types = [
            "YouTube Video to MP3 (native)",
            "YouTube Video to MP4 (native)",
            "YouTube Playlist to MP3 (native)",
            "YouTube Playlist to MP4 (native)"
        ]
        yt_transcript_type = "YouTube Video to Transcript (TXT)"
        text_types = [
            "Text to MP3",
            "Text to WAV",
            "Text to QR"
        ]
        if conversion in yt_types or conversion == yt_transcript_type:
            self.select_btn.setVisible(False)
            self.input_box.setVisible(True)
            self.input_box.setPlaceholderText("Paste YouTube link or playlist here")
            self.file_paths = []
            self.convert_btn.setEnabled(bool(self.input_box.text().strip()))
        elif conversion in text_types:
            self.select_btn.setVisible(True)  # Show file select for .txt
            self.input_box.setVisible(True)
            self.input_box.setPlaceholderText("Enter text to convert or select a .txt file")
            # Enable convert if either input_box has text or a .txt file is selected
            has_txt_file = bool(self.file_paths) and self.file_paths[0].lower().endswith('.txt')
            has_text = bool(self.input_box.text().strip())
            self.convert_btn.setEnabled(has_txt_file or has_text)
        else:
            self.select_btn.setVisible(True)
            self.input_box.setVisible(False)
            self.input_box.setPlaceholderText("")
            self.convert_btn.setEnabled(bool(self.file_paths))

    def on_input_box_changed(self, text):
        conversion = self.combo.currentText()
        yt_types = [
            "YouTube Video to MP3 (native)",
            "YouTube Video to MP4 (native)",
            "YouTube Playlist to MP3 (native)",
            "YouTube Playlist to MP4 (native)"
        ]
        yt_transcript_type = "YouTube Video to Transcript (TXT)"
        text_types = [
            "Text to MP3",
            "Text to WAV",
            "Text to QR"
        ]
        if conversion in yt_types or conversion == yt_transcript_type:
            self.convert_btn.setEnabled(bool(text.strip()))
        elif conversion in text_types:
            has_txt_file = bool(self.file_paths) and self.file_paths[0].lower().endswith('.txt')
            has_text = bool(text.strip())
            self.convert_btn.setEnabled(has_txt_file or has_text)

    def convert_files(self):
        if not self.convert_btn.isEnabled():
            print("Convert button is disabled, skipping duplicate call.")
            return
        self.convert_btn.setEnabled(False)
        try:
            conversion = self.combo.currentText()
            yt_types = [
                "YouTube Video to MP3 (native)",
                "YouTube Video to MP4 (native)",
                "YouTube Playlist to MP3 (native)",
                "YouTube Playlist to MP4 (native)"
            ]
            text_types = [
                "Text to MP3",
                "Text to WAV",
                "Text to QR"
            ]
            print(f"convert_files called. Conversion: {conversion}, input_box visible: {self.input_box.isVisible()}")
            if conversion in yt_types:
                if not self.input_box.isVisible():
                    print("Input box not visible, skipping conversion.")
                    return
                yt_url = self.input_box.text() or ""
                yt_url = yt_url.strip()
                # Sanitize input: remove leading/trailing non-URL characters
                import re
                yt_url = re.sub(r'^[^h]*', '', yt_url)
                yt_url = yt_url.strip()
                print(f"YT playlist URL: {repr(yt_url)} (type: {type(yt_url)}), length: {len(yt_url)})")
                print("Char codes:", [ord(c) for c in yt_url])
                if not yt_url or not yt_url.startswith('http'):
                    self.status.setText("Please enter a valid YouTube playlist link (string).")
                    return
            elif conversion == "YouTube Video to Transcript (TXT)":
                yt_url = self.input_box.text() or ""
                yt_url = yt_url.strip()
                import re
                yt_url = re.sub(r'^[^h]*', '', yt_url)
                yt_url = yt_url.strip()
                if not yt_url or not yt_url.startswith('http'):
                    self.status.setText("Please enter a valid YouTube video link.")
                    return
                self.status.setText("Starting transcript extraction...")
                self.progress.setVisible(True)
                self.progress.setMaximum(0)  # Indeterminate
                self.progress.setMinimum(0)
                self.progress.setValue(0)
                self.convert_btn.setEnabled(False)
                self.cancel_btn.setEnabled(False)
                self.worker = YTTranscriptWorker(yt_url)
                self.worker.progress.connect(self.status.append)
                def on_finished(status, out_path):
                    self.progress.setVisible(False)
                    self.convert_btn.setEnabled(True)
                    if status == "success":
                        self.status.append(f"✅ Transcript saved to: {out_path}")
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.information(self, "Transcript", f"Transcript saved to: {out_path}")
                    else:
                        self.status.append(f"❌ {out_path}")
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "Transcript", f"Failed: {out_path}")
                self.worker.finished.connect(on_finished)
                self.worker.start()
                return
            if conversion in text_types:
                # Priority: .txt file if selected, else input box
                text_input = None
                if self.file_paths and self.file_paths[0].lower().endswith('.txt'):
                    try:
                        with open(self.file_paths[0], 'r', encoding='utf-8') as f:
                            text_input = f.read().strip()
                    except Exception as e:
                        self.status.setText(f"Error reading .txt file: {e}")
                        return
                else:
                    text_input = self.input_box.text() or ""
                    text_input = text_input.strip()
                if not text_input:
                    self.status.setText("Please enter text or select a .txt file to convert.")
                    return
            server = self.get_server_url()
            if not server:
                self.status.setText("Invalid server IP.")
                return
            conversion = self.combo.currentText()
            url = None
            data = {}
            save_ext = None
            if conversion == "MP4 to MP3":
                url = f"http://{server}:5000/convert/video"
                save_ext = ".mp3"
            elif conversion == "JPG to PNG":
                url = f"http://{server}:5000/convert/image"
                data = {'format': 'png'}
                save_ext = ".png"
            elif conversion == "PNG to JPG":
                url = f"http://{server}:5000/convert/image"
                data = {'format': 'jpg'}
                save_ext = ".jpg"
            elif conversion == "Word to PDF":
                url = f"http://{server}:5000/convert/document"
                save_ext = ".pdf"
            elif conversion == "Archive to ZIP":
                url = f"http://{server}:5000/convert/archive"
                save_ext = ".zip"
            elif conversion == "Extract ZIP":
                if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith('.zip'):
                    self.status.setText("Please select a single ZIP file to extract.")
                    return
                url = f"http://{server}:5000/convert/unzip"
                try:
                    import requests
                    with open(self.file_paths[0], 'rb') as f:
                        files = {'file': (os.path.basename(self.file_paths[0]), f)}
                        resp = requests.post(url, files=files)
                    if resp.ok:
                        out_path = os.path.join(os.path.dirname(self.file_paths[0]), "unzipped_contents.zip")
                        with open(out_path, 'wb') as outf:
                            outf.write(resp.content)
                        self.status.append(f"Success: {out_path}")
                        success = 1
                        fail = 0
                    else:
                        self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                        success = 0
                        fail = 1
                except Exception as e:
                    self.status.append(f"Error: {e}")
                    success = 0
                    fail = 1
                self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
                QMessageBox.information(self, "Converter", f"Extract ZIP done! {success} succeeded, {fail} failed.")
                self.progress.setVisible(False)
                self.file_progress.setVisible(False)
                self.phase_label.setVisible(False)
                self.convert_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
                self.timer.stop()
                return
            elif conversion == "MP3 to WAV":
                self.convert_audio('mp3_to_wav', server)
                return
            elif conversion == "WAV to MP3":
                self.convert_audio('wav_to_mp3', server)
                return
            elif conversion == "GIF to MP4":
                self.convert_gifmp4('gif_to_mp4', server)
                return
            elif conversion == "MP4 to GIF":
                self.convert_gifmp4('mp4_to_gif', server)
                return
            elif conversion == "PNG/JPG to ICO":
                self.convert_to_ico(server)
                return
            elif conversion == "JPG/PNG to SVG":
                self.convert_svg('raster_to_svg', server)
                return
            elif conversion == "SVG to PNG":
                self.convert_svg('svg_to_raster', server, 'png')
                return
            elif conversion == "SVG to JPG":
                self.convert_svg('svg_to_raster', server, 'jpg')
                return
            elif conversion == "M4A to MP3":
                self.convert_m4amp3('m4a_to_mp3', server)
                return
            elif conversion == "MP3 to M4A":
                self.convert_m4amp3('mp3_to_m4a', server)
                return
            elif conversion == "Text to QR":
                self.convert_text_to_qr(server)
                return
            elif conversion == "QR to Text":
                self.convert_qr_to_text(server)
                return
            elif conversion == "Image to Text (OCR)":
                self.convert_ocr('image_to_text', server)
                return
            elif conversion == "PDF to Text (OCR)":
                self.convert_ocr('pdf_to_text', server)
                return
            # For YouTube conversions, use url from input_box
            if conversion == "YouTube Video to MP3 (native)":
                try:
                    import sys
                    import os
                    CONVERTER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web_app/converter'))
                    if CONVERTER_PATH not in sys.path:
                        sys.path.insert(0, CONVERTER_PATH)
                    from yt_downloader import download_yt_mp3  # type: ignore
                    download_yt_mp3(yt_url)
                    self.status.append("✅ Downloaded video as MP3 to yt_converted.")
                except Exception as e:
                    self.status.append(f"❌ Error: {e}")
                return
            elif conversion == "YouTube Video to MP4 (native)":
                try:
                    import sys
                    import os
                    CONVERTER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web_app/converter'))
                    if CONVERTER_PATH not in sys.path:
                        sys.path.insert(0, CONVERTER_PATH)
                    from yt_downloader import download_yt_mp4  # type: ignore
                    download_yt_mp4(yt_url)
                    self.status.append("✅ Downloaded video as MP4 to yt_converted.")
                except Exception as e:
                    self.status.append(f"❌ Error: {e}")
                return
            elif conversion == "YouTube Playlist to MP3 (native)":
                try:
                    import sys
                    import os
                    CONVERTER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web_app/converter'))
                    if CONVERTER_PATH not in sys.path:
                        sys.path.insert(0, CONVERTER_PATH)
                    from yt_downloader import download_yt_playlist_mp3  # type: ignore
                    download_yt_playlist_mp3(yt_url)
                    self.status.append("✅ Downloaded playlist as MP3 to yt_converted.")
                except Exception as e:
                    self.status.append(f"❌ Error: {e}")
                return
            elif conversion == "YouTube Playlist to MP4 (native)":
                # Debug and type check
                print(f"YT playlist URL: {repr(yt_url)} (type: {type(yt_url)})")
                if not yt_url or not yt_url.startswith('http'):
                    self.status.setText("Please enter a valid YouTube playlist link (string).")
                    return
                try:
                    import sys
                    import os
                    CONVERTER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web_app/converter'))
                    if CONVERTER_PATH not in sys.path:
                        sys.path.insert(0, CONVERTER_PATH)
                    from yt_downloader import download_yt_playlist_mp4  # type: ignore
                    download_yt_playlist_mp4(yt_url)
                    self.status.append("✅ Downloaded playlist as MP4 to yt_converted.")
                except Exception as e:
                    self.status.append(f"❌ Error: {e}")
                return
            # For text conversions, use text from input_box
            if conversion == "Text to MP3":
                self.convert_tts('mp3', self.get_server_url(), text=text_input)
                return
            elif conversion == "Text to WAV":
                self.convert_tts('wav', self.get_server_url(), text=text_input)
                return
            else:
                self.status.setText("Unknown conversion type.")
                return

            if conversion == "Archive to ZIP":
                # Send all files as 'files' in a single request
                files_payload = [("files", (os.path.basename(fp), open(fp, "rb"))) for fp in self.file_paths]
                try:
                    import requests
                    resp = requests.post(url, files=files_payload)
                    for _, f in files_payload:
                        f[1].close()
                    if resp.ok:
                        out_path = os.path.join(os.path.dirname(self.file_paths[0]), "archive_converted.zip")
                        with open(out_path, 'wb') as f:
                            f.write(resp.content)
                        self.status.append(f"Success: {out_path}")
                        success = 1
                        fail = 0
                    else:
                        self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                        success = 0
                        fail = 1
                except Exception as e:
                    self.status.append(f"Error: {e}")
                    success = 0
                    fail = 1
                self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
                QMessageBox.information(self, "Converter", f"Archive to ZIP done! {success} succeeded, {fail} failed.")
                self.progress.setVisible(False)
                self.file_progress.setVisible(False)
                self.phase_label.setVisible(False)
                self.convert_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
                self.timer.stop()
                return
            self.status.setText(f"Converting {len(self.file_paths)} files...")
            self.progress.setVisible(True)
            self.progress.setMaximum(len(self.file_paths))
            self.progress.setValue(0)
            self.file_progress.setVisible(True)
            self.file_progress.setValue(0)
            self.file_progress.setMaximum(100)
            self.file_progress.setMinimum(0)
            self.file_progress.setFormat('')
            self.phase_label.setVisible(True)
            self.phase_label.setText('Uploading...')
            self.convert_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
            self.elapsed_label.setText("Elapsed: 00:00")
            self.est_label.setText("Est. Remaining: 00:00")
            self.elapsed_time = 0
            self.est_remaining = 0
            self.timer.start(1000)
            self.worker = ConverterWorker(self.file_paths, conversion, url, data, save_ext)
            self.worker.progress_update.connect(self.on_progress_update)
            self.worker.file_result.connect(self.on_file_result)
            self.worker.finished.connect(self.on_conversion_finished)
            self.worker.file_progress.connect(self.on_file_progress)
            self.worker.start()
        finally:
            self.convert_btn.setEnabled(True)

    def cancel_conversion(self):
        if self.worker:
            self.worker.stop()
            self.status.append("\nConversion cancelled by user.")
            self.cancel_btn.setEnabled(False)
            self.timer.stop()
            self.file_progress.setVisible(False)
            self.phase_label.setVisible(False)

    def on_progress_update(self, current, total, message, elapsed, est_remaining):
        self.progress.setMaximum(total)
        self.progress.setValue(current-1)
        self.status.append(message)
        self.elapsed_time = elapsed
        self.est_remaining = est_remaining
        self.update_time_labels()
        # Don't reset file_progress here, let phase change handle it

    def on_file_progress(self, percent, phase):
        if phase == 'upload':
            self.file_progress.setMaximum(100)
            self.file_progress.setMinimum(0)
            self.file_progress.setFormat('%p%')
            self.file_progress.setValue(percent)
            self.phase_label.setText('Uploading...')
        elif phase == 'convert':
            self.file_progress.setMaximum(0)  # Indeterminate
            self.file_progress.setMinimum(0)
            self.file_progress.setFormat('')
            self.phase_label.setText('Converting...')

    def on_file_result(self, file_path, result):
        self.status.append(result)

    def on_conversion_finished(self, success, fail):
        self.progress.setValue(self.progress.maximum())
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()
        self.update_time_labels()
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"Batch conversion done! {success} succeeded, {fail} failed.")

    def update_time_labels(self):
        elapsed_str = self.format_time(self.elapsed_time)
        est_str = self.format_time(self.est_remaining)
        self.elapsed_label.setText(f"Elapsed: {elapsed_str}")
        self.est_label.setText(f"Est. Remaining: {est_str}")

    @staticmethod
    def format_time(seconds):
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        return f"{mins:02d}:{secs:02d}"

    def convert_audio(self, direction, server):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('mp3', 'wav')):
            self.status.setText("Please select a single MP3 or WAV file.")
            return
        url = f"http://{server}:5000/convert/audio"
        ext = '.wav' if direction == 'mp3_to_wav' else '.mp3'
        try:
            import requests
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'direction': direction}
                resp = requests.post(url, files=files, data=data)
            if resp.ok:
                out_path = os.path.splitext(self.file_paths[0])[0] + "_converted" + ext
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                self.status.append(f"Success: {out_path}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"Audio conversion done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def convert_gifmp4(self, direction, server):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('gif', 'mp4')):
            self.status.setText("Please select a single GIF or MP4 file.")
            return
        url = f"http://{server}:5000/convert/gifmp4"
        ext = '.mp4' if direction == 'gif_to_mp4' else '.gif'
        try:
            import requests
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'direction': direction}
                resp = requests.post(url, files=files, data=data)
            if resp.ok:
                out_path = os.path.splitext(self.file_paths[0])[0] + "_converted" + ext
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                self.status.append(f"Success: {out_path}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"GIF/MP4 conversion done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def convert_to_ico(self, server):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('png', 'jpg', 'jpeg')):
            self.status.setText("Please select a single PNG or JPG file.")
            return
        url = f"http://{server}:5000/convert/ico"
        try:
            import requests
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                resp = requests.post(url, files=files)
            if resp.ok:
                out_path = os.path.splitext(self.file_paths[0])[0] + "_converted.ico"
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                self.status.append(f"Success: {out_path}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"ICO conversion done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def convert_svg(self, direction, server, fmt=None):
        if direction == 'raster_to_svg':
            if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('png', 'jpg', 'jpeg')):
                self.status.setText("Please select a single PNG or JPG file.")
                return
        elif direction == 'svg_to_raster':
            if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith('svg'):
                self.status.setText("Please select a single SVG file.")
                return
        url = f"http://{server}:5000/convert/svg"
        try:
            import requests
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'direction': direction}
                if fmt:
                    data['format'] = fmt
                resp = requests.post(url, files=files, data=data)
            if resp.ok:
                ext = '.svg' if direction == 'raster_to_svg' else f'.{fmt}'
                out_path = os.path.splitext(self.file_paths[0])[0] + "_converted" + ext
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                self.status.append(f"Success: {out_path}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"SVG conversion done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def convert_m4amp3(self, direction, server):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('m4a', 'mp3')):
            self.status.setText("Please select a single M4A or MP3 file.")
            return
        url = f"http://{server}:5000/convert/m4amp3"
        ext = '.mp3' if direction == 'm4a_to_mp3' else '.m4a'
        try:
            import requests
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'direction': direction}
                resp = requests.post(url, files=files, data=data)
            if resp.ok:
                out_path = os.path.splitext(self.file_paths[0])[0] + "_converted" + ext
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                self.status.append(f"Success: {out_path}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"M4A/MP3 conversion done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def convert_text_to_qr(self, server):
        text, ok = QInputDialog.getText(self, "Text to QR", "Enter text to encode:")
        if not ok or not text:
            self.status.setText("No text entered.")
            return
        url = f"http://{server}:5000/convert/qr"
        try:
            import requests
            data = {'mode': 'text_to_qr', 'text': text}
            resp = requests.post(url, data=data)
            if resp.ok:
                out_path = os.path.join(os.getcwd(), "qr_converted.png")
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                self.status.append(f"Success: {out_path}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"Text to QR done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def convert_qr_to_text(self, server):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('png', 'jpg', 'jpeg')):
            self.status.setText("Please select a single QR code image file.")
            return
        url = f"http://{server}:5000/convert/qr"
        try:
            import requests
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'mode': 'qr_to_text'}
                resp = requests.post(url, files=files, data=data)
            if resp.ok:
                decoded = resp.json().get('text', '')
                self.status.append(f"Decoded text: {decoded}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"QR to Text done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def convert_ocr(self, mode, server):
        if mode == 'image_to_text':
            if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('png', 'jpg', 'jpeg')):
                self.status.setText("Please select a single PNG or JPG file.")
                return
        elif mode == 'pdf_to_text':
            if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith('pdf'):
                self.status.setText("Please select a single PDF file.")
                return
        url = f"http://{server}:5000/convert/ocr"
        try:
            import requests
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'mode': mode}
                resp = requests.post(url, files=files, data=data)
            if resp.ok:
                text = resp.text
                self.status.append(f"Extracted text:\n{text}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"OCR done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def convert_tts(self, fmt, server, text=None):
        from PySide6.QtWidgets import QInputDialog
        if text is None:
            text, ok = QInputDialog.getText(self, f"Text to {fmt.upper()}", "Enter text to synthesize:")
            if not ok or not text:
                self.status.setText("No text entered.")
                return
        url = f"http://{server}:5000/convert/tts"
        try:
            import requests
            data = {'text': text, 'format': fmt}
            resp = requests.post(url, data=data)
            if resp.ok:
                out_path = os.path.join(os.getcwd(), f"tts_converted.{fmt}")
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                self.status.append(f"Success: {out_path}")
                success = 1
                fail = 0
            else:
                self.status.append(f"Failed: ({resp.status_code})\n{resp.text}")
                success = 0
                fail = 1
        except Exception as e:
            self.status.append(f"Error: {e}")
            success = 0
            fail = 1
        self.status.append(f"\nDone! {success} succeeded, {fail} failed.")
        QMessageBox.information(self, "Converter", f"TTS done! {success} succeeded, {fail} failed.")
        self.progress.setVisible(False)
        self.file_progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.timer.stop()

    def on_yt_progress(self, filename, downloaded, total):
        percent = int((downloaded / total) * 100) if total else 0
        self.progress.setValue(percent)
        self.phase_label.setVisible(True)
        self.phase_label.setText(f"Downloading: {os.path.basename(filename)} ({percent}%)")

    def on_yt_status(self, msg):
        self.status.append(msg)

    def on_yt_finished(self, msg):
        self.progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.status.append(msg)
        self.convert_btn.setEnabled(True)

    # Drag-and-drop support
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if file_paths:
            self.file_paths = file_paths
            self.status.setText(f"Selected (dragged): {len(file_paths)} files\n" + '\n'.join(file_paths))
            # For text_types, enable convert if .txt file is selected or input_box has text
            conversion = self.combo.currentText()
            text_types = ["Text to MP3", "Text to WAV", "Text to QR"]
            if conversion in text_types:
                has_txt_file = bool(self.file_paths) and self.file_paths[0].lower().endswith('.txt')
                has_text = bool(self.input_box.text().strip())
                self.convert_btn.setEnabled(has_txt_file or has_text)
            else:
                self.convert_btn.setEnabled(True)

class YTTranscriptWorker(QThread):
    progress = Signal(str)
    finished = Signal(str, str)  # (status, out_path or error)
    def __init__(self, yt_url, out_dir=None):
        super().__init__()
        self.yt_url = yt_url
        self.out_dir = out_dir or os.getcwd()
    def run(self):
        try:
            self.progress.emit("Fetching transcript...")
            # Try youtube_transcript_api first
            try:
                from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
                import re
                video_id = None
                # Extract video ID from URL
                match = re.search(r"(?:v=|youtu.be/)([\w-]{11})", self.yt_url)
                if match:
                    video_id = match.group(1)
                if not video_id:
                    self.finished.emit("error", "Could not extract video ID from URL.")
                    return
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = transcript_list.find_transcript(["en"]).fetch()
                text = "\n".join([entry.text for entry in transcript])
            except Exception as e:
                self.finished.emit("error", f"Transcript fetch failed: {e}")
                return
            # Save to txt file in converter/yt_transcripted
            import datetime
            import os
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web_app/converter/yt_transcripted'))
            os.makedirs(base_dir, exist_ok=True)
            fname = f"yt_transcript_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            out_path = os.path.join(base_dir, fname)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(text)
            self.finished.emit("success", out_path)
        except Exception as e:
            self.finished.emit("error", str(e))

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
        icons_dir = os.path.join(os.path.dirname(__file__), "icons")
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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("alstha_growth - ML Client")
        self.image_path = None
        self.image_data = None
        self.result = None
        self.last_mobile_image = None
        if not os.path.exists(MOBILE_UPLOADS_DIR):
            os.makedirs(MOBILE_UPLOADS_DIR)
        self.is_dark_mode = False
        self.init_ui()

    def init_ui(self):
        tabs = QTabWidget()
        main_tab = QWidget()
        main_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.setWindowState(Qt.WindowMaximized)

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

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.img_label.setMaximumSize(1280, 720)
        self.img_label.setMinimumSize(320, 240)
        self.img_label.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc;")
        self.show_camera_icon()
        main_layout.addWidget(self.img_label)

        self.select_btn = QPushButton("Select Image")
        self.select_btn.clicked.connect(self.select_image)
        btn_layout.addWidget(self.select_btn)

        self.check_mobile_btn = QPushButton("Check Mobile Uploads")
        self.check_mobile_btn.clicked.connect(self.check_mobile_uploads)
        btn_layout.addWidget(self.check_mobile_btn)

        self.view_files_btn = QPushButton("View Files")
        self.view_files_btn.clicked.connect(lambda: self.view_uploads_files())
        btn_layout.addWidget(self.view_files_btn)

        main_layout.addLayout(btn_layout)

        self.upload_btn = QPushButton("Upload to Flask")
        self.upload_btn.clicked.connect(self.upload_image)
        self.upload_btn.setEnabled(False)
        main_layout.addWidget(self.upload_btn)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("ML result will appear here.")
        main_layout.addWidget(self.result_text)

        main_tab.setLayout(main_layout)
        converter_tab = ConverterTab()
        tabs.addTab(main_tab, "Main")
        tabs.addTab(converter_tab, "Converter")
        search_tab = SearchTab()
        tabs.addTab(search_tab, "Search")
        upload_ytg_tab = UploadYTGTab()
        tabs.addTab(upload_ytg_tab, "Uploading YT/G")
        player_tab = PlayerTab()
        tabs.addTab(player_tab, "Player")
        tabs.setCurrentIndex(0)
        self.search_tab = search_tab

        # Freeze/unfreeze tabs logic
        def set_tab_enabled(tab_widget, enabled):
            for i in range(tab_widget.layout().count()):
                item = tab_widget.layout().itemAt(i)
                widget = item.widget() if item else None
                if widget:
                    widget.setEnabled(enabled)
                elif item and hasattr(item, 'layout') and item.layout():
                    # Recursively disable/enable nested layouts
                    for j in range(item.layout().count()):
                        subitem = item.layout().itemAt(j)
                        subwidget = subitem.widget() if subitem else None
                        if subwidget:
                            subwidget.setEnabled(enabled)
        def on_tab_changed(idx):
            for i in range(tabs.count()):
                tab = tabs.widget(i)
                if hasattr(tab, 'setEnabled'):
                    tab.setEnabled(i == idx)
                # For QWidget with layouts, recursively enable/disable children
                if hasattr(tab, 'layout') and tab.layout():
                    set_tab_enabled(tab, i == idx)
            # Special: focus input for Search tab
            if tabs.tabText(idx) == "Search":
                search_tab.focus_input()
        tabs.currentChanged.connect(on_tab_changed)
        # Initial freeze
        on_tab_changed(tabs.currentIndex())

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)

        # Light/Dark mode toggle button
        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setToolTip("Toggle Light/Dark Mode")
        self.theme_btn.setFixedWidth(40)
        self.theme_btn.clicked.connect(self.toggle_theme)
        btn_layout.addWidget(self.theme_btn)

    def toggle_theme(self):
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
            # Set camera section background to black
            self.img_label.setStyleSheet("background: #181a1b; border: 1px solid #333;")
        else:
            QApplication.instance().setStyleSheet("")
            self.theme_btn.setText("🌙")
            self.is_dark_mode = False
            # Set camera section background to light
            self.img_label.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc;")

    def show_camera_icon(self):
        from PySide6.QtGui import QPixmap, QIcon, QPainter
        import os
        icons_dir = os.path.join(os.path.dirname(__file__), "icons")
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
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget, QHBoxLayout, QCheckBox, QPushButton, QMessageBox
        import mimetypes, shutil
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        uploads_dir = os.path.join(project_root, 'web_app', 'web_app', 'uploads')
        send_to_mobile_dir = os.path.join(project_root, 'web_app', 'web_app', 'send_to_mobile')
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
        self.uploads_checkboxes = []
        for fname in sorted(files):
            fpath = os.path.join(uploads_dir, fname)
            row = QHBoxLayout()
            cb = QCheckBox()
            row.addWidget(cb)
            mimetype, _ = mimetypes.guess_type(fpath)
            if os.path.isdir(fpath):
                icon_label = QLabel("[Folder]")
                row.addWidget(icon_label)
            elif mimetype and mimetype.startswith('image'):
                pixmap = QPixmap(fpath).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label = QLabel()
                img_label.setPixmap(pixmap)
                row.addWidget(img_label)
            else:
                icon_label = QLabel("[File]")
                row.addWidget(icon_label)
            name_label = QLabel(fname)
            row.addWidget(name_label)
            content_layout.addLayout(row)
            self.uploads_checkboxes.append((cb, fpath))
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        # Bulk action buttons
        btn_row = QHBoxLayout()
        send_btn = QPushButton("Send to Mobile")
        delete_btn = QPushButton("Delete")
        btn_row.addWidget(send_btn)
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)
        def send_to_mobile():
            selected = [f for cb, f in self.uploads_checkboxes if cb.isChecked() and os.path.isfile(f)]
            if not selected:
                QMessageBox.information(dialog, "No Selection", "No files selected.")
                return
            if not os.path.exists(send_to_mobile_dir):
                os.makedirs(send_to_mobile_dir)
            for f in selected:
                shutil.copy2(f, send_to_mobile_dir)
            QMessageBox.information(dialog, "Done", f"Sent {len(selected)} files to send_to_mobile.")
        def delete_files():
            selected = [f for cb, f in self.uploads_checkboxes if cb.isChecked() and os.path.isfile(f)]
            if not selected:
                QMessageBox.information(dialog, "No Selection", "No files selected.")
                return
            for f in selected:
                os.remove(f)
            QMessageBox.information(dialog, "Done", f"Deleted {len(selected)} files from uploads.")
            dialog.close()
        send_btn.clicked.connect(send_to_mobile)
        delete_btn.clicked.connect(delete_files)
        dialog.setLayout(layout)
        dialog.resize(500, 400)
        dialog.exec()

    def view_uploads_files(self, start_dir=None):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem, QAbstractItemView
        import mimetypes, shutil, os
        from PySide6.QtCore import Qt
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        uploads_root = os.path.join(project_root, 'web_app', 'web_app', 'uploads')
        if start_dir is None:
            current_dir = uploads_root
        else:
            current_dir = start_dir
        send_to_mobile_dir = os.path.join(project_root, 'web_app', 'web_app', 'send_to_mobile')
        if not os.path.exists(current_dir):
            QMessageBox.information(self, "Notification", f"No files found in {current_dir}.")
            return
        files = os.listdir(current_dir)
        if not files:
            QMessageBox.information(self, "Notification", f"No files found in {current_dir}.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Uploads ({os.path.relpath(current_dir, uploads_root) or '.'})")
        layout = QVBoxLayout()
        # Back button if not at root
        if os.path.normpath(current_dir) != os.path.normpath(uploads_root):
            back_btn = QPushButton("Back")
            def go_back():
                parent_dir = os.path.dirname(current_dir)
                # Only go back if still within uploads_root
                if os.path.commonpath([uploads_root, parent_dir]) == uploads_root:
                    dialog.close()
                    self.view_uploads_files(parent_dir)
            back_btn.clicked.connect(go_back)
            layout.addWidget(back_btn)
        # QTreeWidget for file explorer
        tree = QTreeWidget()
        tree.setColumnCount(3)
        tree.setHeaderLabels(["Name", "Type", "Size"])
        tree.setSelectionMode(QAbstractItemView.NoSelection)
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
        layout.addWidget(tree)
        # Bulk action buttons
        btn_row = QVBoxLayout()
        send_btn = QPushButton("Send to Mobile")
        delete_btn = QPushButton("Delete")
        btn_row.addWidget(send_btn)
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)
        def collect_checked_files():
            checked = []
            for item, fpath in self._tree_checkboxes:
                if item.checkState(0) == Qt.Checked and os.path.isfile(fpath):
                    checked.append(fpath)
            return checked
        def send_to_mobile():
            selected = collect_checked_files()
            if not selected:
                QMessageBox.information(dialog, "No Selection", "No files selected.")
                return
            if not os.path.exists(send_to_mobile_dir):
                os.makedirs(send_to_mobile_dir)
            for f in selected:
                shutil.copy2(f, send_to_mobile_dir)
            QMessageBox.information(dialog, "Done", f"Sent {len(selected)} files to send_to_mobile.")
        def delete_files():
            selected = collect_checked_files()
            if not selected:
                QMessageBox.information(dialog, "No Selection", "No files selected.")
                return
            for f in selected:
                os.remove(f)
            QMessageBox.information(dialog, "Done", f"Deleted {len(selected)} files from uploads.")
            dialog.close()
        send_btn.clicked.connect(send_to_mobile)
        delete_btn.clicked.connect(delete_files)
        dialog.setLayout(layout)
        dialog.resize(600, 500)
        dialog.exec()

    def closeEvent(self, event):
        event.accept()

class UploadYTGTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.yt_dir, self.g_dir = self.ensure_dirs()
        self.status = QTextEdit()
        self.status.setReadOnly(True)
        # YouTube account selection
        from PySide6.QtWidgets import QComboBox
        self.yt_account_box = QComboBox()
        self.yt_account_box.setToolTip("Select YouTube account")
        self.yt_account_box.addItem("(Choose or add account)")
        self.yt_account_map = self.load_yt_accounts()  # {email: client_secret_filename}
        self.yt_account_emails = list(self.yt_account_map.keys())
        for email in self.yt_account_emails:
            self.yt_account_box.addItem(email)
        layout.addWidget(QLabel("YouTube Account:"))
        layout.addWidget(self.yt_account_box)
        # Google Drive account selection
        self.account_box = QComboBox()
        self.account_box.setToolTip("Select Google Drive account")
        self.account_box.addItem("(Choose or add account)")
        self.account_map = self.load_known_accounts()  # {email: client_secret_filename}
        self.account_emails = list(self.account_map.keys())
        for email in self.account_emails:
            self.account_box.addItem(email)
        layout.addWidget(QLabel("Google Drive Account:"))
        layout.addWidget(self.account_box)
        # YouTube files with checkboxes
        self.yt_files = self.get_files(self.yt_dir)
        from PySide6.QtWidgets import QCheckBox, QHBoxLayout
        layout.addWidget(QLabel("YouTube Files:"))
        self.yt_checkboxes = []
        for fname in self.yt_files:
            row = QHBoxLayout()
            cb = QCheckBox(fname)
            row.addWidget(cb)
            layout.addLayout(row)
            self.yt_checkboxes.append((cb, fname))
        self.yt_upload_btn = QPushButton("Upload to YouTube")
        self.yt_upload_btn.clicked.connect(self.upload_yt)
        layout.addWidget(self.yt_upload_btn)
        # Google Drive files with checkboxes
        self.g_files = self.get_files(self.g_dir)
        layout.addWidget(QLabel("Google Drive Files:"))
        self.g_checkboxes = []
        for fname in self.g_files:
            row = QHBoxLayout()
            cb = QCheckBox(fname)
            row.addWidget(cb)
            layout.addLayout(row)
            self.g_checkboxes.append((cb, fname))
        self.g_upload_btn = QPushButton("Upload to Google Drive")
        self.g_upload_btn.clicked.connect(self.upload_g)
        layout.addWidget(self.g_upload_btn)
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status)
        self.setLayout(layout)
    def load_yt_accounts(self):
        import json
        acc_path = os.path.join(UPLOAD_JSON_DIR, 'yt_accounts.json')
        if os.path.exists(acc_path):
            with open(acc_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {email: '' for email in data}
                return data
        return {}
    def save_yt_accounts(self, accounts):
        import json
        acc_path = os.path.join(UPLOAD_JSON_DIR, 'yt_accounts.json')
        with open(acc_path, 'w') as f:
            json.dump(accounts, f)
    def ensure_dirs(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        base = os.path.join(project_root, 'web_app', 'web_app', 'files', 'uploading_yt_G')
        yt = os.path.join(base, 'yt')
        g = os.path.join(base, 'google')
        os.makedirs(yt, exist_ok=True)
        os.makedirs(g, exist_ok=True)
        return yt, g
    def get_files(self, folder):
        return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    def load_known_accounts(self):
        import json
        acc_path = os.path.join(UPLOAD_JSON_DIR, 'gdrive_accounts.json')
        if os.path.exists(acc_path):
            with open(acc_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {email: '' for email in data}
                return data
        return {}
    def save_known_accounts(self, accounts):
        import json
        acc_path = os.path.join(UPLOAD_JSON_DIR, 'gdrive_accounts.json')
        with open(acc_path, 'w') as f:
            json.dump(accounts, f)
    def upload_yt(self):
        selected_files = [fname for cb, fname in self.yt_checkboxes if cb.isChecked()]
        if not selected_files:
            self.status.append("No files selected for YouTube upload.")
            return
        idx = self.yt_account_box.currentIndex()
        if idx <= 0 or idx > len(self.yt_account_emails):
            from PySide6.QtWidgets import QFileDialog
            self.status.append("No YouTube account selected, please choose your client_secret JSON file...")
            secrets_path, _ = QFileDialog.getOpenFileName(self, "Select YouTube client_secret JSON", UPLOAD_JSON_DIR, "JSON Files (*.json)")
            if not secrets_path:
                self.status.append("No client_secret file selected. Aborting.")
                return
            try:
                import pickle
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build as build2
                from google.auth.transport.requests import Request
                import json
                SCOPES = [
                    'openid',
                    'https://www.googleapis.com/auth/youtube.upload',
                    'https://www.googleapis.com/auth/userinfo.email'
                ]
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
                service2 = build2('oauth2', 'v2', credentials=creds)
                user_info = service2.userinfo().get().execute()
                actual_email = user_info['email']
                cred_path2 = os.path.join(UPLOAD_JSON_DIR, f'token_yt_{actual_email}.pickle')
                with open(cred_path2, 'wb') as token:
                    pickle.dump(creds, token)
                # Save mapping
                self.yt_account_map[actual_email] = os.path.basename(secrets_path)
                self.save_yt_accounts(self.yt_account_map)
                if actual_email not in self.yt_account_emails:
                    self.yt_account_emails.append(actual_email)
                    self.yt_account_box.addItem(actual_email)
                self.yt_account_box.setCurrentIndex(self.yt_account_emails.index(actual_email)+1)
                email = actual_email
                secrets_path = os.path.join(UPLOAD_JSON_DIR, self.yt_account_map[email])
            except Exception as e:
                self.status.append(f"❌ YouTube login failed: {e}")
                self.status.append("Please select a YouTube account.")
                return
        else:
            email = self.yt_account_emails[idx-1]
            secrets_path = os.path.join(UPLOAD_JSON_DIR, self.yt_account_map[email])
        self.status.append(f"Uploading {len(selected_files)} files to YouTube as {email}...")
        try:
            import pickle
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.auth.transport.requests import Request
            import json
            SCOPES = [
                'openid',
                'https://www.googleapis.com/auth/youtube.upload',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
            creds = None
            cred_path = os.path.join(UPLOAD_JSON_DIR, f'token_yt_{email}.pickle')
            if os.path.exists(cred_path):
                with open(cred_path, 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    from googleapiclient.discovery import build as build2
                    service2 = build2('oauth2', 'v2', credentials=creds)
                    user_info = service2.userinfo().get().execute()
                    actual_email = user_info['email']
                    cred_path2 = os.path.join(UPLOAD_JSON_DIR, f'token_yt_{actual_email}.pickle')
                    with open(cred_path2, 'wb') as token:
                        pickle.dump(creds, token)
                    if actual_email not in self.yt_account_emails:
                        self.yt_account_emails.append(actual_email)
                        self.yt_account_map[actual_email] = os.path.basename(secrets_path)
                        self.save_yt_accounts(self.yt_account_map)
                        self.yt_account_box.addItem(actual_email)
                    email = actual_email
            service = build('youtube', 'v3', credentials=creds)
            for fname in selected_files:
                fpath = os.path.join(self.yt_dir, fname)
                body = {
                    'snippet': {
                        'title': fname,
                        'description': 'Uploaded by alstha_growth app',
                        'tags': ['alstha_growth'],
                        'categoryId': '22'  # People & Blogs
                    },
                    'status': {
                        'privacyStatus': 'private'
                    }
                }
                media = MediaFileUpload(fpath, resumable=True)
                request = service.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
                response = request.execute()
                self.status.append(f"[YouTube] Uploaded: {fname} (id: {response.get('id')})")
            self.status.append(f"YouTube upload complete for {email}.")
        except Exception as e:
            self.status.append(f"❌ YouTube upload failed: {e}")
    def upload_g(self):
        selected_files = [fname for cb, fname in self.g_checkboxes if cb.isChecked()]
        if not selected_files:
            self.status.append("No files selected for Google Drive upload.")
            return
        idx = self.account_box.currentIndex()
        if idx <= 0 or idx > len(self.account_emails):
            from PySide6.QtWidgets import QFileDialog
            self.status.append("No account selected, please choose your client_secret JSON file...")
            secrets_path, _ = QFileDialog.getOpenFileName(self, "Select Google client_secret JSON", UPLOAD_JSON_DIR, "JSON Files (*.json)")
            if not secrets_path:
                self.status.append("No client_secret file selected. Aborting.")
                return
            try:
                import pickle
                from google_auth_oauthlib.flow import InstalledAppFlow
                from googleapiclient.discovery import build as build2
                from google.auth.transport.requests import Request
                import json
                SCOPES = [
                    'openid',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/userinfo.email'
                ]
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
                service2 = build2('oauth2', 'v2', credentials=creds)
                user_info = service2.userinfo().get().execute()
                actual_email = user_info['email']
                cred_path2 = os.path.join(UPLOAD_JSON_DIR, f'token_gdrive_{actual_email}.pickle')
                with open(cred_path2, 'wb') as token:
                    pickle.dump(creds, token)
                # Save mapping
                self.account_map[actual_email] = os.path.basename(secrets_path)
                self.save_known_accounts(self.account_map)
                if actual_email not in self.account_emails:
                    self.account_emails.append(actual_email)
                    self.account_box.addItem(actual_email)
                self.account_box.setCurrentIndex(self.account_emails.index(actual_email)+1)
                email = actual_email
                secrets_path = os.path.join(UPLOAD_JSON_DIR, self.account_map[email])
            except Exception as e:
                self.status.append(f"❌ Google login failed: {e}")
                self.status.append("Please select a Google Drive account.")
                return
        else:
            email = self.account_emails[idx-1]
            secrets_path = os.path.join(UPLOAD_JSON_DIR, self.account_map[email])
        self.status.append(f"Uploading {len(selected_files)} files to Google Drive as {email}...")
        try:
            import pickle
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.auth.transport.requests import Request
            import json
            SCOPES = [
                'openid',
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
            creds = None
            cred_path = os.path.join(UPLOAD_JSON_DIR, f'token_gdrive_{email}.pickle')
            if os.path.exists(cred_path):
                with open(cred_path, 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    from googleapiclient.discovery import build as build2
                    service2 = build2('oauth2', 'v2', credentials=creds)
                    user_info = service2.userinfo().get().execute()
                    actual_email = user_info['email']
                    cred_path2 = os.path.join(UPLOAD_JSON_DIR, f'token_gdrive_{actual_email}.pickle')
                    with open(cred_path2, 'wb') as token:
                        pickle.dump(creds, token)
                    if actual_email not in self.account_emails:
                        self.account_emails.append(actual_email)
                        self.account_map[actual_email] = os.path.basename(secrets_path)
                        self.save_known_accounts(self.account_map)
                        self.account_box.addItem(actual_email)
                    email = actual_email
            service = build('drive', 'v3', credentials=creds)
            for fname in selected_files:
                fpath = os.path.join(self.g_dir, fname)
                file_metadata = {'name': fname}
                media = MediaFileUpload(fpath, resumable=True)
                uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                self.status.append(f"[GDrive] Uploaded: {fname} (id: {uploaded.get('id')})")
            self.status.append(f"Google Drive upload complete for {email}.")
        except Exception as e:
            self.status.append(f"❌ Google Drive upload failed: {e}")

class StreamingWorker(QThread):
    """Worker thread for streaming media files"""
    buffer_progress = Signal(int)
    streaming_complete = Signal(str)  # temp_file_path
    
    def __init__(self, file_path, buffer_size=1024*1024):
        super().__init__()
        self.file_path = file_path
        self.buffer_size = buffer_size
        self.is_running = True
        
    def run(self):
        temp_path = None
        try:
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(self.file_path)[1])
            temp_path = temp_file.name
            temp_file.close()
            
            file_size = os.path.getsize(self.file_path)
            bytes_received = 0
            
            with open(self.file_path, 'rb') as source_file:
                while self.is_running:
                    chunk = source_file.read(self.buffer_size)
                    if not chunk:
                        break
                    
                    with open(temp_path, 'ab') as temp_file:
                        temp_file.write(chunk)
                    
                    bytes_received += len(chunk)
                    buffer_percent = min(100, int((bytes_received / file_size) * 100))
                    self.buffer_progress.emit(buffer_percent)
                    
                    # Small delay to simulate network streaming
                    self.msleep(50)
            
            if self.is_running:
                self.streaming_complete.emit(temp_path)
            else:
                # Clean up if cancelled
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            print(f"Streaming error: {e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def stop(self):
        self.is_running = False

class StreamingMediaPlayer(QWidget):
    """Advanced streaming media player with chunked loading and buffering"""
    
    def __init__(self, media_type="audio"):
        super().__init__()
        self.media_type = media_type
        self.streaming_worker = None
        self.temp_file_path = None
        
        layout = QVBoxLayout()
        
        # Media player
        self.player = QMediaPlayer()
        if media_type == "video":
            self.video_widget = QVideoWidget()
            self.player.setVideoOutput(self.video_widget)
            layout.addWidget(self.video_widget)
        
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Play/Pause/Stop buttons
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        
        # Progress and time
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.time_label = QLabel("00:00 / 00:00")
        
        controls_layout.addWidget(self.progress_slider, 2)
        controls_layout.addWidget(self.time_label)
        
        # Volume
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        controls_layout.addWidget(QLabel("Vol"))
        controls_layout.addWidget(self.volume_slider)
        
        layout.addLayout(controls_layout)
        
        # Buffer progress
        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(QLabel("Buffer:"))
        self.buffer_progress = QProgressBar()
        self.buffer_progress.setRange(0, 100)
        self.buffer_progress.setVisible(False)
        buffer_layout.addWidget(self.buffer_progress)
        buffer_layout.addStretch()
        layout.addLayout(buffer_layout)
        
        # Connect signals
        self.play_btn.clicked.connect(self.player.play)
        self.pause_btn.clicked.connect(self.player.pause)
        self.stop_btn.clicked.connect(self.stop_streaming)
        self.progress_slider.sliderMoved.connect(self.seek)
        self.player.positionChanged.connect(self.update_progress)
        self.player.durationChanged.connect(self.update_duration)
        self.volume_slider.valueChanged.connect(lambda v: self.audio_output.setVolume(v/100))
        self.audio_output.setVolume(self.volume_slider.value()/100)
        
        self.setLayout(layout)
    
    def stream_file(self, file_path):
        """Start streaming a file in chunks"""
        try:
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", f"File not found: {file_path}")
                return
            
            # Stop any current streaming and wait for cleanup
            self.stop_streaming()
            
            # Small delay to ensure proper cleanup
            QTimer.singleShot(200, lambda: self._start_streaming(file_path))
                
        except Exception as e:
            QMessageBox.critical(self, "Streaming Error", f"Failed to stream file: {str(e)}")
            self.stop_streaming()
    
    def _start_streaming(self, file_path):
        """Internal method to start streaming after cleanup delay"""
        try:
            # Start streaming worker
            self.streaming_worker = StreamingWorker(file_path)
            self.streaming_worker.buffer_progress.connect(self.update_buffer_progress)
            self.streaming_worker.streaming_complete.connect(self.on_streaming_complete)
            self.streaming_worker.finished.connect(self._on_worker_finished)
            self.streaming_worker.start()
            
            # Show buffer progress
            self.buffer_progress.setVisible(True)
            self.buffer_progress.setValue(0)
            
        except Exception as e:
            QMessageBox.critical(self, "Streaming Error", f"Failed to start streaming: {str(e)}")
            self.stop_streaming()
    
    def _on_worker_finished(self):
        """Called when streaming worker finishes"""
        try:
            if self.streaming_worker:
                # Disconnect signals to prevent memory leaks
                self.streaming_worker.buffer_progress.disconnect()
                self.streaming_worker.streaming_complete.disconnect()
                self.streaming_worker.finished.disconnect()
        except Exception as e:
            print(f"Worker finished cleanup error: {e}")
    
    def update_buffer_progress(self, percent):
        """Update buffer progress bar"""
        try:
            self.buffer_progress.setValue(percent)
            
            # Start playing when we have enough buffer (10% or 1MB)
            if percent >= 10 and not self.player.mediaStatus() == QMediaPlayer.PlayingState:
                if hasattr(self, 'temp_file_path') and self.temp_file_path:
                    self.player.setSource(QUrl.fromLocalFile(self.temp_file_path))
                    self.player.play()
        except Exception as e:
            print(f"Buffer progress update error: {e}")
    
    def on_streaming_complete(self, temp_file_path):
        """Called when streaming is complete"""
        try:
            self.temp_file_path = temp_file_path
            self.buffer_progress.setValue(100)
            
            # Start playing if not already playing
            if not self.player.mediaStatus() == QMediaPlayer.PlayingState:
                self.player.setSource(QUrl.fromLocalFile(temp_file_path))
                self.player.play()
        except Exception as e:
            print(f"Streaming complete error: {e}")
    
    def stop_streaming(self):
        """Stop streaming and cleanup"""
        try:
            # Stop the player first
            self.player.stop()
            self.player.setSource(QUrl())
            
            # Stop streaming worker
            if self.streaming_worker:
                self.streaming_worker.stop()
                # Don't wait here - let it clean up in background
                self.streaming_worker.finished.connect(lambda: self._cleanup_worker())
                self.streaming_worker = None
            
            # Hide buffer progress
            self.buffer_progress.setVisible(False)
            self.buffer_progress.setValue(0)
            
            # Clean up temp file
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.unlink(self.temp_file_path)
                except:
                    pass
                self.temp_file_path = None
                
        except Exception as e:
            print(f"Error stopping streaming: {e}")
    
    def _cleanup_worker(self):
        """Clean up worker after it finishes"""
        try:
            if hasattr(self, 'temp_file_path') and self.temp_file_path and os.path.exists(self.temp_file_path):
                os.unlink(self.temp_file_path)
                self.temp_file_path = None
        except Exception as e:
            print(f"Error cleaning up worker: {e}")
    
    def seek(self, pos):
        """Seek to position"""
        if self.player.duration() > 0:
            self.player.setPosition(int(pos/100 * self.player.duration()))
    
    def update_progress(self, position):
        """Update progress slider"""
        duration = self.player.duration()
        if duration > 0:
            percent = int(position / duration * 100)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(percent)
            self.progress_slider.blockSignals(False)
            self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
    
    def update_duration(self, duration):
        """Update duration display"""
        position = self.player.position()
        if duration > 0:
            percent = int(position / duration * 100)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(percent)
            self.progress_slider.blockSignals(False)
            self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
    
    @staticmethod
    def format_time(ms):
        s = int(ms // 1000)
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"
    
    def closeEvent(self, event):
        """Clean up when widget is closed"""
        self.stop_streaming()
        super().closeEvent(event)

class PlayerTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        # Player mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Player Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Standard Player", "Streaming Player"])
        self.mode_combo.currentTextChanged.connect(self.switch_player_mode)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # --- Audio Section ---
        audio_group = QGroupBox("Audio Player")
        audio_layout = QVBoxLayout()
        audio_row = QHBoxLayout()
        self.audio_list = QListWidget()
        self.audio_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web_app/files/Audio'))
        os.makedirs(self.audio_dir, exist_ok=True)
        self.audio_files = [f for f in os.listdir(self.audio_dir) if os.path.isfile(os.path.join(self.audio_dir, f))]
        self.audio_list.addItems(self.audio_files)
        audio_row.addWidget(self.audio_list, 2)
        audio_controls = QHBoxLayout()
        self.audio_play_btn = QPushButton()
        self.audio_play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.audio_pause_btn = QPushButton()
        self.audio_pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.audio_stop_btn = QPushButton()
        self.audio_stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        audio_controls.addWidget(self.audio_play_btn)
        audio_controls.addWidget(self.audio_pause_btn)
        audio_controls.addWidget(self.audio_stop_btn)
        # Progress bar and time
        self.audio_slider = QSlider(Qt.Horizontal)
        self.audio_slider.setRange(0, 100)
        self.audio_time_label = QLabel("00:00 / 00:00")
        audio_controls.addWidget(self.audio_slider, 2)
        audio_controls.addWidget(self.audio_time_label)
        # Volume
        self.audio_volume = QSlider(Qt.Horizontal)
        self.audio_volume.setRange(0, 100)
        self.audio_volume.setValue(80)
        audio_controls.addWidget(QLabel("Vol"))
        audio_controls.addWidget(self.audio_volume)
        # Create standard audio container
        self.audio_standard_container = QWidget()
        audio_standard_layout = QHBoxLayout()
        
        # Add play/pause/stop buttons
        audio_standard_layout.addWidget(self.audio_play_btn)
        audio_standard_layout.addWidget(self.audio_pause_btn)
        audio_standard_layout.addWidget(self.audio_stop_btn)
        
        # Add progress bar and time
        audio_standard_layout.addWidget(self.audio_slider, 2)
        audio_standard_layout.addWidget(self.audio_time_label)
        
        # Add volume controls
        audio_standard_layout.addWidget(QLabel("Vol"))
        audio_standard_layout.addWidget(self.audio_volume)
        
        self.audio_standard_container.setLayout(audio_standard_layout)
        
        # Create streaming audio player
        self.audio_streaming_player = StreamingMediaPlayer("audio")
        self.audio_streaming_player.setVisible(False)
        
        # Add both to layout
        audio_layout.addWidget(self.audio_standard_container)
        audio_layout.addWidget(self.audio_streaming_player)
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        # --- Audio Player Logic ---
        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)
        self.audio_play_btn.clicked.connect(self.audio_player.play)
        self.audio_pause_btn.clicked.connect(self.audio_player.pause)
        self.audio_stop_btn.clicked.connect(self.audio_player.stop)
        self.audio_list.itemClicked.connect(self.play_selected_audio)
        self.audio_slider.sliderMoved.connect(self.seek_audio)
        self.audio_player.positionChanged.connect(self.update_audio_slider)
        self.audio_player.durationChanged.connect(self.update_audio_duration)
        self.audio_volume.valueChanged.connect(lambda v: self.audio_output.setVolume(v/100))
        self.audio_output.setVolume(self.audio_volume.value()/100)
        # --- Video Section ---
        video_group = QGroupBox("Video Player")
        video_layout = QVBoxLayout()
        video_row = QHBoxLayout()
        self.video_list = QListWidget()
        self.video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web_app/files/Video'))
        os.makedirs(self.video_dir, exist_ok=True)
        self.video_files = [f for f in os.listdir(self.video_dir) if os.path.isfile(os.path.join(self.video_dir, f))]
        self.video_list.addItems(self.video_files)
        video_row.addWidget(self.video_list, 2)
        video_controls = QHBoxLayout()
        self.video_play_btn = QPushButton()
        self.video_play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.video_pause_btn = QPushButton()
        self.video_pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.video_stop_btn = QPushButton()
        self.video_stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        video_controls.addWidget(self.video_play_btn)
        video_controls.addWidget(self.video_pause_btn)
        video_controls.addWidget(self.video_stop_btn)
        # Progress bar and time
        self.video_slider = QSlider(Qt.Horizontal)
        self.video_slider.setRange(0, 100)
        self.video_time_label = QLabel("00:00 / 00:00")
        video_controls.addWidget(self.video_slider, 2)
        video_controls.addWidget(self.video_time_label)
        # Volume
        self.video_volume = QSlider(Qt.Horizontal)
        self.video_volume.setRange(0, 100)
        self.video_volume.setValue(80)
        video_controls.addWidget(QLabel("Vol"))
        video_controls.addWidget(self.video_volume)
        
        # Create standard video container
        self.video_standard_container = QWidget()
        video_standard_layout = QHBoxLayout()
        
        # Add play/pause/stop buttons
        video_standard_layout.addWidget(self.video_play_btn)
        video_standard_layout.addWidget(self.video_pause_btn)
        video_standard_layout.addWidget(self.video_stop_btn)
        
        # Add progress bar and time
        video_standard_layout.addWidget(self.video_slider, 2)
        video_standard_layout.addWidget(self.video_time_label)
        
        # Add volume controls
        video_standard_layout.addWidget(QLabel("Vol"))
        video_standard_layout.addWidget(self.video_volume)
        
        self.video_standard_container.setLayout(video_standard_layout)
        
        # Add video list and standard container to video row
        video_row.addWidget(self.video_standard_container, 3)
        video_layout.addLayout(video_row)
        
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(240)
        video_layout.addWidget(self.video_widget)
        
        # Create streaming video player
        self.video_streaming_player = StreamingMediaPlayer("video")
        self.video_streaming_player.setVisible(False)
        video_layout.addWidget(self.video_streaming_player)
        
        video_group.setLayout(video_layout)
        layout.addWidget(video_group)
        # --- Video Player Logic ---
        self.video_player = QMediaPlayer()
        self.video_player.setVideoOutput(self.video_widget)
        self.video_play_btn.clicked.connect(self.video_player.play)
        self.video_pause_btn.clicked.connect(self.video_player.pause)
        self.video_stop_btn.clicked.connect(self.video_player.stop)
        self.video_list.itemClicked.connect(self.play_selected_video)
        self.video_slider.sliderMoved.connect(self.seek_video)
        self.video_player.positionChanged.connect(self.update_video_slider)
        self.video_player.durationChanged.connect(self.update_video_duration)
        self.video_volume.valueChanged.connect(lambda v: self.video_audio_output.setVolume(v/100))
        self.video_audio_output = QAudioOutput()
        self.video_player.setAudioOutput(self.video_audio_output)
        self.video_volume.valueChanged.connect(lambda v: self.video_audio_output.setVolume(v/100))
        self.video_audio_output.setVolume(self.video_volume.value()/100)
        
        # Connect error signals
        self.audio_player.errorOccurred.connect(self.on_audio_error)
        self.video_player.errorOccurred.connect(self.on_video_error)
        
        # Add refresh button
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh Files")
        refresh_btn.clicked.connect(self.refresh_file_lists)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        self.setLayout(layout)
        
        # Initialize player mode
        self.current_mode = "standard"
        self.switch_player_mode("Standard Player")
    
    def switch_player_mode(self, mode):
        """Switch between standard and streaming player modes"""
        if mode == "Standard Player":
            self.current_mode = "standard"
            # Show standard containers
            self.audio_standard_container.setVisible(True)
            self.video_standard_container.setVisible(True)
            self.video_widget.setVisible(True)
            # Hide streaming players
            self.audio_streaming_player.setVisible(False)
            self.video_streaming_player.setVisible(False)
        else:  # Streaming Player
            self.current_mode = "streaming"
            # Hide standard containers
            self.audio_standard_container.setVisible(False)
            self.video_standard_container.setVisible(False)
            self.video_widget.setVisible(False)
            # Show streaming players
            self.audio_streaming_player.setVisible(True)
            self.video_streaming_player.setVisible(True)
    
    def refresh_file_lists(self):
        """Refresh the audio and video file lists"""
        try:
            # Refresh audio files
            self.audio_files = [f for f in os.listdir(self.audio_dir) if os.path.isfile(os.path.join(self.audio_dir, f))]
            self.audio_list.clear()
            self.audio_list.addItems(self.audio_files)
            
            # Refresh video files
            self.video_files = [f for f in os.listdir(self.video_dir) if os.path.isfile(os.path.join(self.video_dir, f))]
            self.video_list.clear()
            self.video_list.addItems(self.video_files)
            
        except Exception as e:
            print(f"Error refreshing file lists: {e}")
    
    def on_audio_error(self, error, error_string):
        QMessageBox.critical(self, "Audio Error", f"Audio playback error: {error_string}")
        print(f"Audio error: {error} - {error_string}")
    
    def on_video_error(self, error, error_string):
        QMessageBox.critical(self, "Video Error", f"Video playback error: {error_string}")
        print(f"Video error: {error} - {error_string}")
    
    def cleanup_media(self):
        """Clean up media resources when tab is closed or app is shutting down"""
        try:
            # Clean up standard players
            self.audio_player.stop()
            self.audio_player.setSource(QUrl())
            self.video_player.stop()
            self.video_player.setSource(QUrl())
            
            # Clean up streaming players
            if hasattr(self, 'audio_streaming_player'):
                self.audio_streaming_player.stop_streaming()
            if hasattr(self, 'video_streaming_player'):
                self.video_streaming_player.stop_streaming()
                
        except Exception as e:
            print(f"Media cleanup error: {e}")
    
    def closeEvent(self, event):
        """Clean up when tab is closed"""
        self.cleanup_media()
        super().closeEvent(event)
    # --- Audio helpers ---
    def play_selected_audio(self, item):
        try:
            file_path = os.path.join(self.audio_dir, item.text())
            
            if self.current_mode == "streaming":
                # Use streaming player
                self.audio_streaming_player.stream_file(file_path)
            else:
                # Use standard player
                self.audio_player.stop()
                self.audio_player.setSource(QUrl())
                QTimer.singleShot(100, lambda: self._play_audio_file(item))
            
        except Exception as e:
            QMessageBox.critical(self, "Audio Playback Error", f"Failed to play audio: {str(e)}")
    
    def _play_audio_file(self, item):
        """Internal method to play audio file after cleanup delay"""
        try:
            file_path = os.path.join(self.audio_dir, item.text())
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", f"Audio file not found: {file_path}")
                return
                
            # Set new source and play
            self.audio_player.setSource(QUrl.fromLocalFile(file_path))
            self.audio_player.play()
            
            # Reset slider and time label
            self.audio_slider.setValue(0)
            self.audio_time_label.setText("00:00 / 00:00")
            
        except Exception as e:
            QMessageBox.critical(self, "Audio Playback Error", f"Failed to play audio: {str(e)}")
    
    def seek_audio(self, pos):
        try:
            if self.audio_player.duration() > 0:
                self.audio_player.setPosition(int(pos/100 * self.audio_player.duration()))
        except Exception as e:
            print(f"Audio seek error: {e}")
    
    def update_audio_slider(self, position):
        try:
            duration = self.audio_player.duration()
            if duration > 0:
                percent = int(position / duration * 100)
                self.audio_slider.blockSignals(True)
                self.audio_slider.setValue(percent)
                self.audio_slider.blockSignals(False)
                self.audio_time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
        except Exception as e:
            print(f"Audio slider update error: {e}")
    
    def update_audio_duration(self, duration):
        try:
            position = self.audio_player.position()
            if duration > 0:
                percent = int(position / duration * 100)
                self.audio_slider.blockSignals(True)
                self.audio_slider.setValue(percent)
                self.audio_slider.blockSignals(False)
                self.audio_time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
        except Exception as e:
            print(f"Audio duration update error: {e}")
    
    # --- Video helpers ---
    def play_selected_video(self, item):
        try:
            file_path = os.path.join(self.video_dir, item.text())
            
            if self.current_mode == "streaming":
                # Use streaming player
                self.video_streaming_player.stream_file(file_path)
            else:
                # Use standard player
                self.video_player.stop()
                self.video_player.setSource(QUrl())
                QTimer.singleShot(100, lambda: self._play_video_file(item))
            
        except Exception as e:
            QMessageBox.critical(self, "Video Playback Error", f"Failed to play video: {str(e)}")
    
    def _play_video_file(self, item):
        """Internal method to play video file after cleanup delay"""
        try:
            file_path = os.path.join(self.video_dir, item.text())
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", f"Video file not found: {file_path}")
                return
                
            # Set new source and play
            self.video_player.setSource(QUrl.fromLocalFile(file_path))
            self.video_player.play()
            
            # Reset slider and time label
            self.video_slider.setValue(0)
            self.video_time_label.setText("00:00 / 00:00")
            
        except Exception as e:
            QMessageBox.critical(self, "Video Playback Error", f"Failed to play video: {str(e)}")
    
    def seek_video(self, pos):
        try:
            if self.video_player.duration() > 0:
                self.video_player.setPosition(int(pos/100 * self.video_player.duration()))
        except Exception as e:
            print(f"Video seek error: {e}")
    
    def update_video_slider(self, position):
        try:
            duration = self.video_player.duration()
            if duration > 0:
                percent = int(position / duration * 100)
                self.video_slider.blockSignals(True)
                self.video_slider.setValue(percent)
                self.video_slider.blockSignals(False)
                self.video_time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
        except Exception as e:
            print(f"Video slider update error: {e}")
    
    def update_video_duration(self, duration):
        try:
            position = self.video_player.position()
            if duration > 0:
                percent = int(position / duration * 100)
                self.video_slider.blockSignals(True)
                self.video_slider.setValue(percent)
                self.video_slider.blockSignals(False)
                self.video_time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
        except Exception as e:
            print(f"Video duration update error: {e}")
    @staticmethod
    def format_time(ms):
        s = int(ms // 1000)
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 