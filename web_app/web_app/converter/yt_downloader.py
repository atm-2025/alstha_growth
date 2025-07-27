import os
import yt_dlp

YT_CONVERTED_DIR = os.path.join(os.path.dirname(__file__), 'yt_converted')
os.makedirs(YT_CONVERTED_DIR, exist_ok=True)

def _progress_hook(d):
    if d['status'] == 'downloading':
        print(f"Downloading: {d.get('filename', '')} - {d.get('downloaded_bytes', 0)}/{d.get('total_bytes', 0)} bytes")
    elif d['status'] == 'finished':
        print(f"Done downloading: {d.get('filename', '')}")

def download_yt_mp3(url):
    """Download a single YouTube video as mp3 to yt_converted."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(YT_CONVERTED_DIR, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'ignoreerrors': True,
        'progress_hooks': [_progress_hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_yt_mp4(url):
    """Download a single YouTube video as mp4 to yt_converted."""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'outtmpl': os.path.join(YT_CONVERTED_DIR, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': True,
        'ignoreerrors': True,
        'progress_hooks': [_progress_hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_yt_playlist_mp3(playlist_url):
    """Download all videos in a YouTube playlist as mp3 to yt_converted."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(YT_CONVERTED_DIR, '%(playlist_title)s/%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'ignoreerrors': True,
        'yesplaylist': True,
        'progress_hooks': [_progress_hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])


def download_yt_playlist_mp4(playlist_url):
    """Download all videos in a YouTube playlist as mp4 to yt_converted."""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'outtmpl': os.path.join(YT_CONVERTED_DIR, '%(playlist_title)s/%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': True,
        'ignoreerrors': True,
        'yesplaylist': True,
        'progress_hooks': [_progress_hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url]) 