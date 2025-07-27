import os
import sys
import time
import socket
import subprocess
import re
import yt_dlp
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QLineEdit, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QInputDialog, QApplication, QSizePolicy
)
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from PIL import Image  # <-- Add PIL import for local image processing

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
                
                # Create converted_files directory structure
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(file_path))[0]
                
                # Determine conversion type folder
                conversion_folder = self._get_conversion_folder()
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files', conversion_folder))
                os.makedirs(converted_dir, exist_ok=True)
                
                # Create output filename with timestamp
                out_filename = f"{base_filename}_converted_{timestamp}{self.save_ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
                # Wait for server response (already done above)
                if resp.ok:
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

    def _get_conversion_folder(self):
        """Get the appropriate folder name for the conversion type"""
        conversion_map = {
            # Audio conversions
            "MP4 to MP3": "audio_conversions",
            "MP3 to WAV": "audio_conversions", 
            "WAV to MP3": "audio_conversions",
            "M4A to MP3": "audio_conversions",
            "MP3 to M4A": "audio_conversions",
            
            # Image conversions
            "JPG to PNG": "image_conversions",
            "PNG to JPG": "image_conversions",
            "PNG/JPG to ICO": "image_conversions",
            "JPG/PNG to SVG": "image_conversions",
            "SVG to PNG": "image_conversions",
            "SVG to JPG": "image_conversions",
            
            # Video conversions
            "GIF to MP4": "video_conversions",
            "MP4 to GIF": "video_conversions",
            
            # Document conversions
            "Word to PDF": "document_conversions",
            
            # Archive conversions
            "Archive to ZIP": "archive_conversions",
            "Extract ZIP": "archive_conversions",
            
            # QR conversions
            "Text to QR": "qr_conversions",
            "QR to Text": "qr_conversions",
            
            # OCR conversions
            "Image to Text (OCR)": "ocr_conversions",
            "PDF to Text (OCR)": "ocr_conversions",
            
            # TTS conversions
            "Text to MP3": "tts_conversions",
            "Text to WAV": "tts_conversions",
            
            # YouTube conversions
            "YouTube Video to MP3 (native)": "youtube_downloads",
            "YouTube Video to MP4 (native)": "youtube_downloads",
            "YouTube Playlist to MP3 (native)": "youtube_downloads",
            "YouTube Playlist to MP4 (native)": "youtube_downloads",
            "YouTube Video to Transcript (TXT)": "youtube_downloads"
        }
        return conversion_map.get(self.conversion, "other_conversions")

    def stop(self):
        self._is_running = False
        self._cancel_requested = True
        # Kill any running subprocess
        if self.current_subprocess:
            try:
                self.current_subprocess.terminate()
            except Exception:
                pass

# Background worker for individual conversions
class IndividualConversionWorker(QThread):
    progress_update = Signal(str, int)  # message, percent
    finished = Signal(bool, str)  # success, result_message

    def __init__(self, conversion_type, server, file_paths=None, text_input=None, direction=None, fmt=None, mode=None):
        super().__init__()
        self.conversion_type = conversion_type
        self.server = server
        self.file_paths = file_paths or []
        self.text_input = text_input
        self.direction = direction
        self.fmt = fmt
        self.mode = mode
        self._is_running = True
        self._cancel_requested = False

    def run(self):
        try:
            self.progress_update.emit("Starting conversion...", 10)
            
            if self.conversion_type == "audio":
                result = self._convert_audio()
            elif self.conversion_type == "gifmp4":
                result = self._convert_gifmp4()
            elif self.conversion_type == "ico":
                result = self._convert_to_ico()
            elif self.conversion_type == "svg":
                result = self._convert_svg()
            elif self.conversion_type == "m4amp3":
                result = self._convert_m4amp3()
            elif self.conversion_type == "text_to_qr":
                result = self._convert_text_to_qr()
            elif self.conversion_type == "qr_to_text":
                result = self._convert_qr_to_text()
            elif self.conversion_type == "ocr":
                result = self._convert_ocr()
            elif self.conversion_type == "tts":
                result = self._convert_tts()
            else:
                result = (False, "Unknown conversion type")
            
            self.finished.emit(*result)
            
        except Exception as e:
            self.finished.emit(False, f"Error: {e}")

    def _convert_audio(self):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('mp3', 'wav')):
            return False, "Please select a single MP3 or WAV file."
        
        self.progress_update.emit("Preparing audio conversion...", 20)
        url = f"http://{self.server}:5000/convert/audio"
        ext = '.wav' if self.direction == 'mp3_to_wav' else '.mp3'
        
        try:
            import requests
            self.progress_update.emit("Uploading file...", 40)
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'direction': self.direction}
                resp = requests.post(url, files=files, data=data)
            
            self.progress_update.emit("Processing conversion...", 70)
            if resp.ok:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/audio_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
                self.progress_update.emit("Saving file...", 90)
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                return True, f"Success: {out_path}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def _convert_gifmp4(self):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('gif', 'mp4')):
            return False, "Please select a single GIF or MP4 file."
        
        self.progress_update.emit("Preparing video conversion...", 20)
        url = f"http://{self.server}:5000/convert/gifmp4"
        ext = '.mp4' if self.direction == 'gif_to_mp4' else '.gif'
        
        try:
            import requests
            self.progress_update.emit("Uploading file...", 40)
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'direction': self.direction}
                resp = requests.post(url, files=files, data=data)
            
            self.progress_update.emit("Processing conversion...", 70)
            if resp.ok:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/video_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
                self.progress_update.emit("Saving file...", 90)
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                return True, f"Success: {out_path}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def _convert_to_ico(self):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('png', 'jpg', 'jpeg')):
            return False, "Please select a single PNG or JPG file."
        
        self.progress_update.emit("Preparing ICO conversion...", 20)
        url = f"http://{self.server}:5000/convert/ico"
        
        try:
            import requests
            self.progress_update.emit("Uploading file...", 40)
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                resp = requests.post(url, files=files)
            
            self.progress_update.emit("Processing conversion...", 70)
            if resp.ok:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/image_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}.ico"
                out_path = os.path.join(converted_dir, out_filename)
                
                self.progress_update.emit("Saving file...", 90)
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                return True, f"Success: {out_path}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def _convert_svg(self):
        if self.direction == 'raster_to_svg':
            if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('png', 'jpg', 'jpeg')):
                return False, "Please select a single PNG or JPG file."
        elif self.direction == 'svg_to_raster':
            if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith('svg'):
                return False, "Please select a single SVG file."
        
        self.progress_update.emit("Preparing SVG conversion...", 20)
        url = f"http://{self.server}:5000/convert/svg"
        
        try:
            import requests
            self.progress_update.emit("Uploading file...", 40)
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'direction': self.direction}
                if self.fmt:
                    data['format'] = self.fmt
                resp = requests.post(url, files=files, data=data)
            
            self.progress_update.emit("Processing conversion...", 70)
            if resp.ok:
                ext = '.svg' if self.direction == 'raster_to_svg' else f'.{self.fmt}'
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/image_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
                self.progress_update.emit("Saving file...", 90)
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                return True, f"Success: {out_path}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def _convert_m4amp3(self):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('m4a', 'mp3')):
            return False, "Please select a single M4A or MP3 file."
        
        self.progress_update.emit("Preparing audio conversion...", 20)
        url = f"http://{self.server}:5000/convert/m4amp3"
        ext = '.mp3' if self.direction == 'm4a_to_mp3' else '.m4a'
        
        try:
            import requests
            self.progress_update.emit("Uploading file...", 40)
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'direction': self.direction}
                resp = requests.post(url, files=files, data=data)
            
            self.progress_update.emit("Processing conversion...", 70)
            if resp.ok:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/audio_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
                self.progress_update.emit("Saving file...", 90)
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                return True, f"Success: {out_path}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def _convert_text_to_qr(self):
        if not self.text_input or not self.text_input.strip():
            return False, "No text entered."
        
        self.progress_update.emit("Preparing QR code generation...", 20)
        url = f"http://{self.server}:5000/convert/qr"
        
        try:
            import requests
            self.progress_update.emit("Generating QR code...", 50)
            data = {'mode': 'text_to_qr', 'text': self.text_input}
            resp = requests.post(url, data=data)
            
            self.progress_update.emit("Processing QR code...", 70)
            if resp.ok:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/qr_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"qr_converted_{timestamp}.png"
                out_path = os.path.join(converted_dir, out_filename)
                
                self.progress_update.emit("Saving QR code...", 90)
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                return True, f"Success: {out_path}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def _convert_qr_to_text(self):
        if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('png', 'jpg', 'jpeg')):
            return False, "Please select a single QR code image file."
        
        self.progress_update.emit("Preparing QR code decoding...", 20)
        url = f"http://{self.server}:5000/convert/qr"
        
        try:
            import requests
            self.progress_update.emit("Uploading QR code image...", 40)
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'mode': 'qr_to_text'}
                resp = requests.post(url, files=files, data=data)
            
            self.progress_update.emit("Decoding QR code...", 70)
            if resp.ok:
                decoded = resp.json().get('text', '')
                return True, f"Decoded text: {decoded}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def _convert_ocr(self):
        if self.mode == 'image_to_text':
            if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith(('png', 'jpg', 'jpeg')):
                return False, "Please select a single PNG or JPG file."
        elif self.mode == 'pdf_to_text':
            if len(self.file_paths) != 1 or not self.file_paths[0].lower().endswith('pdf'):
                return False, "Please select a single PDF file."
        
        self.progress_update.emit("Preparing OCR processing...", 20)
        url = f"http://{self.server}:5000/convert/ocr"
        
        try:
            import requests
            self.progress_update.emit("Uploading file...", 40)
            with open(self.file_paths[0], 'rb') as f:
                files = {'file': (os.path.basename(self.file_paths[0]), f)}
                data = {'mode': self.mode}
                resp = requests.post(url, files=files, data=data)
            
            self.progress_update.emit("Processing OCR...", 70)
            if resp.ok:
                text = resp.text
                return True, f"Extracted text:\n{text}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def _convert_tts(self):
        if not self.text_input or not self.text_input.strip():
            return False, "No text entered."
        
        self.progress_update.emit("Preparing text-to-speech conversion...", 20)
        url = f"http://{self.server}:5000/convert/tts"
        
        try:
            import requests
            self.progress_update.emit("Processing text-to-speech...", 50)
            data = {'text': self.text_input, 'format': self.fmt}
            resp = requests.post(url, data=data)
            
            self.progress_update.emit("Generating audio...", 70)
            if resp.ok:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/tts_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"tts_converted_{timestamp}.{self.fmt}"
                out_path = os.path.join(converted_dir, out_filename)
                
                self.progress_update.emit("Saving audio file...", 90)
                with open(out_path, 'wb') as outf:
                    outf.write(resp.content)
                return True, f"Success: {out_path}"
            else:
                return False, f"Failed: ({resp.status_code})\n{resp.text}"
        except Exception as e:
            return False, f"Error: {e}"

    def stop(self):
        self._is_running = False
        self._cancel_requested = True

# Background worker for YouTube downloads
class YouTubeDownloadWorker(QThread):
    progress_update = Signal(str, int)  # message, percent
    finished = Signal(bool, str)  # success, result_message

    def __init__(self, download_type, url, server=None):
        super().__init__()
        self.download_type = download_type
        self.url = url
        self.server = server
        self._is_running = True
        self._cancel_requested = False

    def run(self):
        try:
            # Reset progress tracking
            if hasattr(self, '_last_percent'):
                delattr(self, '_last_percent')
            
            self.progress_update.emit("Starting YouTube download...", 10)
            
            if self.download_type == "mp3":
                result = self._download_mp3()
            elif self.download_type == "mp4":
                result = self._download_mp4()
            elif self.download_type == "playlist_mp3":
                result = self._download_playlist_mp3()
            elif self.download_type == "playlist_mp4":
                result = self._download_playlist_mp4()
            else:
                result = (False, "Unknown download type")
            
            self.finished.emit(*result)
            
        except Exception as e:
            self.finished.emit(False, f"Error: {e}")

    def _download_mp3(self):
        """Download a single YouTube video as mp3 to local yt_converted folder."""
        self.progress_update.emit("Preparing MP3 download...", 20)
        
        try:
            yt_converted_dir = self._get_yt_converted_dir()
            self.progress_update.emit("Setting up download options...", 30)
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(yt_converted_dir, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'ignoreerrors': True,
                'progress_hooks': [self._yt_progress_hook],
                # Add headers to avoid 403 errors
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                # Retry options
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                # Cookie handling
                'cookiefile': None,
                'cookiesfrombrowser': None,
            }
            
            self.progress_update.emit("Starting download...", 40)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            self.progress_update.emit("Download completed!", 100)
            return True, f"✅ Downloaded video as MP3 to {yt_converted_dir}"
            
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                return False, f"❌ YouTube blocked the download (403 Forbidden). This video may be restricted or unavailable."
            elif "fragment" in error_msg.lower():
                return False, f"❌ Video download failed due to missing fragments. Try a different video or format."
            else:
                return False, f"❌ Error downloading MP3: {error_msg}"

    def _download_mp4(self):
        """Download a single YouTube video as mp4 to local yt_converted folder."""
        self.progress_update.emit("Preparing MP4 download...", 20)
        
        try:
            yt_converted_dir = self._get_yt_converted_dir()
            self.progress_update.emit("Setting up download options...", 30)
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4/best[ext=mp4]/best',
                'outtmpl': os.path.join(yt_converted_dir, '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'quiet': True,
                'ignoreerrors': True,
                'progress_hooks': [self._yt_progress_hook],
                # Add headers to avoid 403 errors
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                # Retry options
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                # Cookie handling
                'cookiefile': None,
                'cookiesfrombrowser': None,
            }
            
            self.progress_update.emit("Starting download...", 40)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            self.progress_update.emit("Download completed!", 100)
            return True, f"✅ Downloaded video as MP4 to {yt_converted_dir}"
            
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                return False, f"❌ YouTube blocked the download (403 Forbidden). This video may be restricted or unavailable."
            elif "fragment" in error_msg.lower():
                return False, f"❌ Video download failed due to missing fragments. Try a different video or format."
            else:
                return False, f"❌ Error downloading MP4: {error_msg}"

    def _download_playlist_mp3(self):
        """Download all videos in a YouTube playlist as mp3 to local yt_converted folder."""
        self.progress_update.emit("Preparing playlist MP3 download...", 20)
        
        try:
            yt_converted_dir = self._get_yt_converted_dir()
            self.progress_update.emit("Setting up playlist download options...", 30)
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(yt_converted_dir, '%(playlist_title)s/%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'ignoreerrors': True,
                'yesplaylist': True,
                'progress_hooks': [self._yt_progress_hook],
                # Add headers to avoid 403 errors
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                # Retry options
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                # Cookie handling
                'cookiefile': None,
                'cookiesfrombrowser': None,
            }
            
            self.progress_update.emit("Starting playlist download...", 40)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            self.progress_update.emit("Playlist download completed!", 100)
            return True, f"✅ Downloaded playlist as MP3 to {yt_converted_dir}"
            
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                return False, f"❌ YouTube blocked the download (403 Forbidden). This playlist may be restricted or unavailable."
            elif "fragment" in error_msg.lower():
                return False, f"❌ Playlist download failed due to missing fragments. Try a different playlist or format."
            else:
                return False, f"❌ Error downloading playlist MP3: {error_msg}"

    def _download_playlist_mp4(self):
        """Download all videos in a YouTube playlist as mp4 to local yt_converted folder."""
        self.progress_update.emit("Preparing playlist MP4 download...", 20)
        
        try:
            yt_converted_dir = self._get_yt_converted_dir()
            self.progress_update.emit("Setting up playlist download options...", 30)
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                'outtmpl': os.path.join(yt_converted_dir, '%(playlist_title)s/%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'quiet': True,
                'ignoreerrors': True,
                'yesplaylist': True,
                'progress_hooks': [self._yt_progress_hook],
                # Add headers to avoid 403 errors
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                # Retry options
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                # Cookie handling
                'cookiefile': None,
                'cookiesfrombrowser': None,
            }
            
            self.progress_update.emit("Starting playlist download...", 40)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            self.progress_update.emit("Playlist download completed!", 100)
            return True, f"✅ Downloaded playlist as MP4 to {yt_converted_dir}"
            
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                return False, f"❌ YouTube blocked the download (403 Forbidden). This playlist may be restricted or unavailable."
            elif "fragment" in error_msg.lower():
                return False, f"❌ Playlist download failed due to missing fragments. Try a different playlist or format."
            else:
                return False, f"❌ Error downloading playlist MP4: {error_msg}"

    def _get_yt_converted_dir(self):
        """Get the directory for YouTube converted files"""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/youtube_downloads'))
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    def _yt_progress_hook(self, d):
        """Progress hook for YouTube downloads"""
        if not self._is_running or self._cancel_requested:
            raise Exception("Download cancelled by user")
            
        if d['status'] == 'downloading':
            # Calculate progress percentage
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0)
            if total > 0:
                percent = min(90, 40 + int((downloaded / total) * 50))  # 40-90% range
                # Only update every 5% to reduce spam
                if not hasattr(self, '_last_percent') or percent - self._last_percent >= 5:
                    self._last_percent = percent
                    filename = d.get('filename', '')
                    # Shorten filename for cleaner display
                    short_name = os.path.basename(filename)
                    if len(short_name) > 30:
                        short_name = short_name[:27] + "..."
                    # Send detailed message for phase label, simple message for status log
                    self.progress_update.emit(f"Downloading: {short_name} ({percent}%)", percent)
        elif d['status'] == 'finished':
            self.progress_update.emit("Processing completed file...", 95)

    def stop(self):
        self._is_running = False
        self._cancel_requested = True

class ConverterTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.file_paths = []
        self.selected_type = None
        self.worker = None
        self.individual_worker = None  # For individual conversions
        self.youtube_worker = None  # For YouTube downloads
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
            "YouTube Video to Transcript (TXT)",
            "Reduce File Size"  # NEW OPTION
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
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*);;Text Files (*.txt)")
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
                yt_text = self.input_box.toPlainText() if hasattr(self.input_box, 'toPlainText') else self.input_box.text()
                yt_text = yt_text.strip()
                # Split by newlines and spaces, filter valid links
                import re
                links = re.split(r'[\s\n]+', yt_text)
                links = [l.strip() for l in links if l.strip().startswith('http')]
                if not links:
                    self.status.setText("Please enter at least one valid YouTube link.")
                    return
                self.status.append(f"Batch download: {len(links)} links detected.")
                self._batch_yt_links = links
                self._batch_yt_mode = conversion
                self._batch_yt_index = 0
                self._batch_yt_success = 0
                self._batch_yt_fail = 0
                self._batch_yt_results = []
                self._start_next_batch_yt_download()
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
                        # Create output path with timestamp in converted_files folder
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/archive_conversions'))
                        os.makedirs(converted_dir, exist_ok=True)
                        out_filename = f"unzipped_contents_{timestamp}.zip"
                        out_path = os.path.join(converted_dir, out_filename)
                        
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
                self.start_individual_conversion("audio", server, direction='mp3_to_wav')
                return
            elif conversion == "WAV to MP3":
                self.start_individual_conversion("audio", server, direction='wav_to_mp3')
                return
            elif conversion == "GIF to MP4":
                self.start_individual_conversion("gifmp4", server, direction='gif_to_mp4')
                return
            elif conversion == "MP4 to GIF":
                self.start_individual_conversion("gifmp4", server, direction='mp4_to_gif')
                return
            elif conversion == "PNG/JPG to ICO":
                self.start_individual_conversion("ico", server)
                return
            elif conversion == "JPG/PNG to SVG":
                self.start_individual_conversion("svg", server, direction='raster_to_svg')
                return
            elif conversion == "SVG to PNG":
                self.start_individual_conversion("svg", server, direction='svg_to_raster', fmt='png')
                return
            elif conversion == "SVG to JPG":
                self.start_individual_conversion("svg", server, direction='svg_to_raster', fmt='jpg')
                return
            elif conversion == "M4A to MP3":
                self.start_individual_conversion("m4amp3", server, direction='m4a_to_mp3')
                return
            elif conversion == "MP3 to M4A":
                self.start_individual_conversion("m4amp3", server, direction='mp3_to_m4a')
                return
            elif conversion == "Text to QR":
                self.start_individual_conversion("text_to_qr", server, text_input=text_input)
                return
            elif conversion == "QR to Text":
                self.start_individual_conversion("qr_to_text", server)
                return
            elif conversion == "Image to Text (OCR)":
                self.start_individual_conversion("ocr", server, mode='image_to_text')
                return
            elif conversion == "PDF to Text (OCR)":
                self.start_individual_conversion("ocr", server, mode='pdf_to_text')
                return
            # For YouTube conversions, use url from input_box
            if conversion == "YouTube Video to MP3 (native)":
                self.start_youtube_download("mp3", yt_url)
                return
            elif conversion == "YouTube Video to MP4 (native)":
                self.start_youtube_download("mp4", yt_url)
                return
            elif conversion == "YouTube Playlist to MP3 (native)":
                self.start_youtube_download("playlist_mp3", yt_url)
                return
            elif conversion == "YouTube Playlist to MP4 (native)":
                # Debug and type check
                print(f"YT playlist URL: {repr(yt_url)} (type: {type(yt_url)})")
                if not yt_url or not yt_url.startswith('http'):
                    self.status.setText("Please enter a valid YouTube playlist link (string).")
                    return
                self.start_youtube_download("playlist_mp4", yt_url)
                return
            # For text conversions, use text from input_box
            if conversion == "Text to MP3":
                self.start_individual_conversion("tts", server, text_input=text_input, fmt='mp3')
                return
            elif conversion == "Text to WAV":
                self.start_individual_conversion("tts", server, text_input=text_input, fmt='wav')
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
                        # Create output path with timestamp in converted_files folder
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/archive_conversions'))
                        os.makedirs(converted_dir, exist_ok=True)
                        out_filename = f"archive_converted_{timestamp}.zip"
                        out_path = os.path.join(converted_dir, out_filename)
                        
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
            if conversion == "Reduce File Size":
                if not self.file_paths or not self.file_paths[0].lower().endswith((".jpg", ".jpeg", ".png")):
                    self.status.setText("Please select a JPG or PNG file to reduce size.")
                    self.convert_btn.setEnabled(True)
                    return
                # Ask for quality (default 70)
                quality, ok = QInputDialog.getInt(self, "Image Quality", "JPEG Quality (1-95, lower=smaller):", 70, 10, 95)
                if not ok:
                    self.status.setText("Operation cancelled.")
                    self.convert_btn.setEnabled(True)
                    return
                # Ask for max width/height (optional)
                max_width, ok_w = QInputDialog.getInt(self, "Max Width", "Max width (0 for no resize):", 0, 0, 10000)
                if not ok_w:
                    max_width = None
                if max_width == 0:
                    max_width = None
                max_height, ok_h = QInputDialog.getInt(self, "Max Height", "Max height (0 for no resize):", 0, 0, 10000)
                if not ok_h:
                    max_height = None
                if max_height == 0:
                    max_height = None
                # Do the reduction locally using PIL
                input_path = self.file_paths[0]
                img = Image.open(input_path)
                if max_width or max_height:
                    orig_width, orig_height = img.size
                    ratio = 1.0
                    if max_width and orig_width > max_width:
                        ratio = min(ratio, max_width / orig_width)
                    if max_height and orig_height > max_height:
                        ratio = min(ratio, max_height / orig_height)
                    if ratio < 1.0:
                        new_size = (int(orig_width * ratio), int(orig_height * ratio))
                        img = img.resize(new_size, Image.LANCZOS)
                base_filename = os.path.splitext(os.path.basename(input_path))[0]
                ext = '.jpg' if input_path.lower().endswith(('.jpg', '.jpeg')) else '.png'
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/image_reduced'))
                os.makedirs(converted_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_filename = f"{base_filename}_reduced_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                if ext == '.jpg':
                    img = img.convert('RGB')
                    img.save(out_path, 'JPEG', quality=quality, optimize=True)
                else:
                    img.save(out_path, 'PNG', optimize=True)
                self.status.setText(f"Success: {out_path}")
                self.convert_btn.setEnabled(True)
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
            if url is None:
                self.status.setText("Unknown conversion type.")
                return
                
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
        if self.individual_worker:
            self.individual_worker.stop()
            self.status.append("\nIndividual conversion cancelled by user.")
            self.cancel_btn.setEnabled(False)
            self.progress.setVisible(False)
            self.phase_label.setVisible(False)
        if self.youtube_worker:
            self.youtube_worker.stop()
            self.status.append("\nYouTube download cancelled by user.")
            self.cancel_btn.setEnabled(False)
            self.progress.setVisible(False)
            self.phase_label.setVisible(False)

    def start_individual_conversion(self, conversion_type, server, **kwargs):
        """Start an individual conversion in background thread"""
        # Stop any existing worker
        if self.individual_worker and self.individual_worker.isRunning():
            self.individual_worker.stop()
            self.individual_worker.wait()
        
        # Create new worker
        self.individual_worker = IndividualConversionWorker(
            conversion_type=conversion_type,
            server=server,
            file_paths=self.file_paths,
            **kwargs
        )
        
        # Connect signals
        self.individual_worker.progress_update.connect(self.on_individual_progress)
        self.individual_worker.finished.connect(self.on_individual_finished)
        
        # Setup UI
        self.progress.setVisible(True)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.phase_label.setVisible(True)
        self.phase_label.setText('Starting...')
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # Start conversion
        self.individual_worker.start()

    def on_individual_progress(self, message, percent):
        """Handle progress updates from individual conversion worker"""
        self.progress.setValue(percent)
        self.phase_label.setText(message)
        self.status.append(message)

    def on_individual_finished(self, success, result_message):
        """Handle completion of individual conversion"""
        self.progress.setVisible(False)
        self.phase_label.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        self.status.append(result_message)
        
        if success:
            QMessageBox.information(self, "Converter", f"Conversion completed successfully!\n{result_message}")
        else:
            QMessageBox.warning(self, "Converter", f"Conversion failed!\n{result_message}")
        
        # Clean up worker
        if self.individual_worker:
            self.individual_worker.deleteLater()
            self.individual_worker = None

    def start_youtube_download(self, download_type, url):
        """Start a YouTube download in background thread"""
        # Stop any existing worker
        if self.youtube_worker and self.youtube_worker.isRunning():
            self.youtube_worker.stop()
            self.youtube_worker.wait()
        
        # Reset progress tracking
        if hasattr(self, '_last_log_percent'):
            delattr(self, '_last_log_percent')
        
        # Create new worker
        self.youtube_worker = YouTubeDownloadWorker(
            download_type=download_type,
            url=url,
            server=self.get_server_url()
        )
        
        # Connect signals
        self.youtube_worker.progress_update.connect(self.on_youtube_progress)
        self.youtube_worker.finished.connect(self.on_youtube_finished)
        
        # Setup UI
        self.progress.setVisible(True)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.phase_label.setVisible(True)
        self.phase_label.setText('Starting YouTube download...')
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # Start download
        self.youtube_worker.start()

    def on_youtube_progress(self, message, percent):
        """Handle progress updates from YouTube download worker"""
        self.progress.setValue(percent)
        self.phase_label.setText(message)
        # Only append to status log every 10% to reduce spam
        if not hasattr(self, '_last_log_percent') or percent - self._last_log_percent >= 10:
            self._last_log_percent = percent
            # Show simplified message in status log
            if "Downloading:" in message:
                self.status.append(f"Download progress: {percent}%")
            else:
                self.status.append(message)

    def on_youtube_finished(self, success, result_message):
        # Called after each download
        if hasattr(self, '_batch_yt_links') and self._batch_yt_index < len(self._batch_yt_links):
            if success:
                self._batch_yt_success += 1
            else:
                self._batch_yt_fail += 1
            self._batch_yt_results.append(result_message)
            self._batch_yt_index += 1
            self._start_next_batch_yt_download()
        else:
            # Not in batch mode, call original handler
            self.progress.setVisible(False)
            self.phase_label.setVisible(False)
            self.status.append(result_message)
            self.convert_btn.setEnabled(True)

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
                # Create output path with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/audio_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
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
                # Create output path with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/video_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
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
                # Create output path with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/image_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}.ico"
                out_path = os.path.join(converted_dir, out_filename)
                
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
                # Create output path with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/image_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
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
                # Create output path with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/audio_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"{base_filename}_converted_{timestamp}{ext}"
                out_path = os.path.join(converted_dir, out_filename)
                
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

    def convert_text_to_qr(self, server, text=None):
        if text is None:
            text, ok = QInputDialog.getText(self, "Text to QR", "Enter text to encode:")
            if not ok or not text:
                self.status.setText("No text entered.")
                return
        elif not text.strip():
            self.status.setText("No text entered.")
            return
        url = f"http://{server}:5000/convert/qr"
        try:
            import requests
            data = {'mode': 'text_to_qr', 'text': text}
            resp = requests.post(url, data=data)
            if resp.ok:
                # Create output path with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/qr_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"qr_converted_{timestamp}.png"
                out_path = os.path.join(converted_dir, out_filename)
                
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
            text, ok = QInputDialog.getText(self, f"Text to {fmt.upper()}", "Text to synthesize:")
            if not ok or not text:
                self.status.setText("No text entered.")
                return
        url = f"http://{server}:5000/convert/tts"
        try:
            import requests
            data = {'text': text, 'format': fmt}
            resp = requests.post(url, data=data)
            if resp.ok:
                # Create output path with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/tts_conversions'))
                os.makedirs(converted_dir, exist_ok=True)
                out_filename = f"tts_converted_{timestamp}.{fmt}"
                out_path = os.path.join(converted_dir, out_filename)
                
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

    # YouTube downloading functions
    def _get_yt_converted_dir(self):
        """Get the directory for YouTube converted files"""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/youtube_downloads'))
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    def _yt_progress_hook(self, d):
        """Progress hook for YouTube downloads"""
        if d['status'] == 'downloading':
            print(f"Downloading: {d.get('filename', '')} - {d.get('downloaded_bytes', 0)}/{d.get('total_bytes', 0)} bytes")
        elif d['status'] == 'finished':
            print(f"Done downloading: {d.get('filename', '')}")

    def download_yt_mp3(self, url):
        """Download a single YouTube video as mp3 to local yt_converted folder."""
        yt_converted_dir = self._get_yt_converted_dir()
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(yt_converted_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'ignoreerrors': True,
            'progress_hooks': [self._yt_progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    def download_yt_mp4(self, url):
        """Download a single YouTube video as mp4 to local yt_converted folder."""
        yt_converted_dir = self._get_yt_converted_dir()
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'outtmpl': os.path.join(yt_converted_dir, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'quiet': True,
            'ignoreerrors': True,
            'progress_hooks': [self._yt_progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    def download_yt_playlist_mp3(self, playlist_url):
        """Download all videos in a YouTube playlist as mp3 to local yt_converted folder."""
        yt_converted_dir = self._get_yt_converted_dir()
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(yt_converted_dir, '%(playlist_title)s/%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'ignoreerrors': True,
            'yesplaylist': True,
            'progress_hooks': [self._yt_progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([playlist_url])

    def download_yt_playlist_mp4(self, playlist_url):
        """Download all videos in a YouTube playlist as mp4 to local yt_converted folder."""
        yt_converted_dir = self._get_yt_converted_dir()
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'outtmpl': os.path.join(yt_converted_dir, '%(playlist_title)s/%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'quiet': True,
            'ignoreerrors': True,
            'yesplaylist': True,
            'progress_hooks': [self._yt_progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([playlist_url])

    def _start_next_batch_yt_download(self):
        if self._batch_yt_index >= len(self._batch_yt_links):
            # Done
            summary = f"\nBatch download complete! {self._batch_yt_success} succeeded, {self._batch_yt_fail} failed."
            self.status.append(summary)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Batch Download", summary)
            self.convert_btn.setEnabled(True)
            return
        link = self._batch_yt_links[self._batch_yt_index]
        self.status.append(f"\nDownloading {self._batch_yt_index+1} of {len(self._batch_yt_links)}: {link}")
        if self._batch_yt_mode == "YouTube Video to MP3 (native)":
            self.start_youtube_download("mp3", link)
        elif self._batch_yt_mode == "YouTube Video to MP4 (native)":
            self.start_youtube_download("mp4", link)
        elif self._batch_yt_mode == "YouTube Playlist to MP3 (native)":
            self.start_youtube_download("playlist_mp3", link)
        elif self._batch_yt_mode == "YouTube Playlist to MP4 (native)":
            self.start_youtube_download("playlist_mp4", link)
        # The on_youtube_finished handler will call _start_next_batch_yt_download

class YTTranscriptWorker(QThread):
    progress = Signal(str)
    finished = Signal(str, str)  # (status, out_path or error)
    def __init__(self, yt_url, out_dir=None):
        super().__init__()
        self.yt_url = yt_url
        self.out_dir = out_dir or os.getcwd()
        self._is_running = True
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
            # Save to txt file in converted_files folder
            import datetime
            import os
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files/youtube_downloads'))
            os.makedirs(base_dir, exist_ok=True)
            fname = f"yt_transcript_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            out_path = os.path.join(base_dir, fname)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(text)
            self.finished.emit("success", out_path)
        except Exception as e:
            self.finished.emit("error", str(e))

    def stop(self):
        """Stop the worker thread"""
        self._is_running = False

