import os
import socket
import subprocess
import re
import requests
from PySide6.QtCore import QObject

FLASK_URL = "http://127.0.0.1:5000/upload"  # Change to your Flask server IP if needed

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

def format_time(ms):
    """Format milliseconds to MM:SS format"""
    s = int(ms // 1000)
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}"

def format_time_seconds(seconds):
    """Format seconds to MM:SS format"""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}" 