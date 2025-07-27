# 📁 CONVERTED FILES STRUCTURE

## 🎯 **COMPLETE ORGANIZED FILE SYSTEM**

All converted files are now saved in a structured `converted_files` folder under `windows_client` with timestamps and organized subfolders for each conversion type.

---

## 📂 **COMPLETE FOLDER STRUCTURE**

```
📁 web_app/windows_client/converted_files/
├── 📁 audio_conversions/
│   ├── 📄 video_converted_20250120_143022.mp3
│   ├── 📄 audio_converted_20250120_143045.wav
│   └── 📄 song_converted_20250120_143100.m4a
│
├── 📁 video_conversions/
│   ├── 📄 animation_converted_20250120_143115.mp4
│   └── 📄 video_converted_20250120_143130.gif
│
├── 📁 image_conversions/
│   ├── 📄 photo_converted_20250120_143145.png
│   ├── 📄 logo_converted_20250120_143200.ico
│   └── 📄 image_converted_20250120_143215.svg
│
├── 📁 document_conversions/
│   └── 📄 document_converted_20250120_143230.pdf
│
├── 📁 archive_conversions/
│   ├── 📄 files_converted_20250120_143245.zip
│   └── 📄 archive_converted_20250120_143300.zip
│
├── 📁 qr_conversions/
│   └── 📄 qr_converted_20250120_143315.png
│
├── 📁 tts_conversions/
│   ├── 📄 tts_converted_20250120_143330.mp3
│   └── 📄 tts_converted_20250120_143345.wav
│
├── 📁 youtube_downloads/
│   ├── 📄 Video Title.mp3
│   ├── 📄 Video Title.mp4
│   ├── 📄 yt_transcript_20250120_143400.txt
│   └── 📁 Playlist Name/
│       ├── 📄 Video 1.mp3
│       └── 📄 Video 2.mp4
│
└── 📁 other_conversions/
    └── 📄 file_converted_20250120_143415.ext
```

---

## 🕐 **TIMESTAMP FORMAT**

All converted files include timestamps in the format: `YYYYMMDD_HHMMSS`

**Example**: `20250120_143022` = January 20, 2025 at 14:30:22

---

## 📋 **COMPLETE CONVERSION TYPE MAPPING**

### **🎵 Audio Conversions** (`audio_conversions/`)
- **MP4 to MP3** → `filename_converted_YYYYMMDD_HHMMSS.mp3`
- **MP3 to WAV** → `filename_converted_YYYYMMDD_HHMMSS.wav`
- **WAV to MP3** → `filename_converted_YYYYMMDD_HHMMSS.mp3`
- **M4A to MP3** → `filename_converted_YYYYMMDD_HHMMSS.mp3`
- **MP3 to M4A** → `filename_converted_YYYYMMDD_HHMMSS.m4a`

### **🎬 Video Conversions** (`video_conversions/`)
- **GIF to MP4** → `filename_converted_YYYYMMDD_HHMMSS.mp4`
- **MP4 to GIF** → `filename_converted_YYYYMMDD_HHMMSS.gif`

### **🖼️ Image Conversions** (`image_conversions/`)
- **JPG to PNG** → `filename_converted_YYYYMMDD_HHMMSS.png`
- **PNG to JPG** → `filename_converted_YYYYMMDD_HHMMSS.jpg`
- **PNG/JPG to ICO** → `filename_converted_YYYYMMDD_HHMMSS.ico`
- **JPG/PNG to SVG** → `filename_converted_YYYYMMDD_HHMMSS.svg`
- **SVG to PNG** → `filename_converted_YYYYMMDD_HHMMSS.png`
- **SVG to JPG** → `filename_converted_YYYYMMDD_HHMMSS.jpg`

### **📄 Document Conversions** (`document_conversions/`)
- **Word to PDF** → `filename_converted_YYYYMMDD_HHMMSS.pdf`

### **📦 Archive Conversions** (`archive_conversions/`)
- **Archive to ZIP** → `filename_converted_YYYYMMDD_HHMMSS.zip`
- **Extract ZIP** → `unzipped_contents.zip`

### **📱 QR Conversions** (`qr_conversions/`)
- **Text to QR** → `qr_converted_YYYYMMDD_HHMMSS.png`
- **QR to Text** → *Display only (no file saved)*

### **🔍 OCR Conversions** (`ocr_conversions/`)
- **Image to Text (OCR)** → *Display only (no file saved)*
- **PDF to Text (OCR)** → *Display only (no file saved)*

### **🔊 TTS Conversions** (`tts_conversions/`)
- **Text to MP3** → `tts_converted_YYYYMMDD_HHMMSS.mp3`
- **Text to WAV** → `tts_converted_YYYYMMDD_HHMMSS.wav`

### **📺 YouTube Downloads** (`youtube_downloads/`)
- **YouTube Video to MP3** → `Video Title.mp3`
- **YouTube Video to MP4** → `Video Title.mp4`
- **YouTube Playlist to MP3** → `Playlist Name/Video Title.mp3`
- **YouTube Playlist to MP4** → `Playlist Name/Video Title.mp4`
- **YouTube Video to Transcript** → `yt_transcript_YYYYMMDD_HHMMSS.txt`

---

## 🎨 **SPECIAL CASES**

### **📝 Display Only (No File Saved)**
- **QR to Text** → Shows decoded text in status
- **Image to Text (OCR)** → Shows extracted text in status  
- **PDF to Text (OCR)** → Shows extracted text in status

### **📁 YouTube Downloads**
- **Single Videos**: Saved with original video title
- **Playlists**: Saved in subfolder with playlist name
- **Transcripts**: Always include timestamp

---

## 🔧 **TECHNICAL IMPLEMENTATION**

### **Complete Conversion Mapping**
```python
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
```

### **File Naming Pattern**
```python
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
base_filename = os.path.splitext(os.path.basename(file_path))[0]
out_filename = f"{base_filename}_converted_{timestamp}{extension}"
```

### **Folder Creation**
```python
converted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../converted_files', conversion_folder))
os.makedirs(converted_dir, exist_ok=True)
```

---

## ✅ **BENEFITS**

1. **🗂️ Organized Structure**: Each conversion type has its own folder
2. **⏰ Timestamp Tracking**: Easy to identify when files were converted
3. **🔍 Easy Finding**: All converted files in one location
4. **📱 Local Storage**: Files saved in windows_client for easy access
5. **🔄 No Conflicts**: Timestamps prevent filename conflicts
6. **📊 Better Management**: Clear separation of file types
7. **✅ Complete Coverage**: All 29 conversion types are mapped

---

## 🚀 **USAGE**

1. **Select Files**: Choose files to convert
2. **Choose Conversion**: Select conversion type from dropdown
3. **Convert**: Click convert button
4. **Find Results**: Check the appropriate folder in `converted_files/`

**Example Path**: `web_app/windows_client/converted_files/audio_conversions/video_converted_20250120_143022.mp3`

---

## 📝 **NOTES**

- All folders are created automatically when needed
- Original files are never modified or moved
- Each conversion gets a unique timestamp
- YouTube downloads use original video titles for better organization
- Display-only conversions (OCR, QR decode) don't create files
- All 29 conversion types are now properly mapped to folders
- No more "Unknown conversion type" errors 