import os
import time
import requests
import subprocess
from PySide6.QtCore import QThread, Signal
from modules.utils import FileWithProgress

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

class YTTranscriptWorker(QThread):
    progress = Signal(str)
    finished = Signal(str, str)  # (status, out_path or error)
    
    def __init__(self, yt_url, out_dir=None):
        super().__init__()
        self.yt_url = yt_url
        self.out_dir = out_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), '../../web_app/files/Audio'))
        os.makedirs(self.out_dir, exist_ok=True)
    
    def run(self):
        try:
            self.progress.emit("Starting YouTube transcript extraction...")
            
            # Use youtube_transcript_api directly
            try:
                from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
                import re
                
                # Extract video ID from URL
                video_id = None
                match = re.search(r"(?:v=|youtu.be/)([\w-]{11})", self.yt_url)
                if match:
                    video_id = match.group(1)
                
                if not video_id:
                    self.finished.emit("error", "Could not extract video ID from URL.")
                    return
                
                self.progress.emit("Fetching transcript...")
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = transcript_list.find_transcript(["en"]).fetch()
                transcript_text = "\n".join([entry.text for entry in transcript])
                
                if transcript_text:
                    # Save transcript to file
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"transcript_{timestamp}.txt"
                    out_path = os.path.join(self.out_dir, filename)
                    
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(transcript_text)
                    
                    self.progress.emit(f"Transcript saved: {filename}")
                    self.finished.emit("success", out_path)
                else:
                    self.finished.emit("error", "No transcript found for this video")
                    
            except TranscriptsDisabled:
                self.finished.emit("error", "Transcripts are disabled for this video")
            except NoTranscriptFound:
                self.finished.emit("error", "No transcript found for this video")
            except Exception as e:
                self.finished.emit("error", f"Transcript fetch failed: {str(e)}")
                
        except Exception as e:
            self.finished.emit("error", f"Failed to extract transcript: {str(e)}")

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