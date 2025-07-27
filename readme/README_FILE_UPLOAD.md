# File Upload Functionality

## Overview
The Android app now supports uploading **all types of files** to the Flask backend server. Users can select any file from their device and upload it to the `mobile_uploads` folder on the server.

## Features

### Android App Features
- **Camera Capture**: Take photos and upload them
- **File Selection**: Pick any file type from device storage
- **File Type Support**: All file types are supported including:
  - Images (JPG, PNG, GIF, BMP, WebP, TIFF, SVG)
  - Videos (MP4, AVI, MOV, MKV, WMV, FLV, WebM, 3GP, M4V)
  - Audio (MP3, WAV, FLAC, AAC, OGG, WMA, M4A)
  - Documents (PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, JSON, XML, HTML, CSS, JS, MD, RTF)
  - Archives (ZIP, RAR, 7Z, TAR, GZ, BZ2)
  - Executables (APK, EXE, DMG, DEB, RPM)
  - Other formats (ISO, TORRENT, EPUB, MOBI)

### Backend Features
- **Universal File Acceptance**: Mobile uploads accept any file type with an extension
- **Proper MIME Type Detection**: Files are uploaded with correct MIME types
- **Organized Storage**: Files are saved to the `mobile_uploads` folder
- **Error Handling**: Comprehensive error handling and logging

## How to Use

### From Android App
1. Open the app
2. Choose one of two options:
   - **"Open Camera"**: Take a photo and upload it
   - **"Select File"**: Pick any file from your device
3. Click "Upload" to send the file to the server
4. The app will show upload status and results

### File Selection Process
1. Tap "Select File" button
2. Android's system file picker opens
3. Navigate to and select any file
4. File info (name and size) is displayed
5. Tap "Upload" to send to server

## Technical Implementation

### Android Changes
- **CameraFragment.kt**: Added file picker functionality using `ActivityResultContracts.GetContent()`
- **MainActivity.kt**: Updated to handle generic file uploads
- **UploadRepository.kt**: Enhanced with comprehensive MIME type detection
- **ApiService.kt**: Added generic file upload endpoint
- **Layout**: Added "Select File" button to UI

### Backend Changes
- **app.py**: Updated `allowed_file()` function to accept all file types for mobile uploads
- **File Validation**: Mobile uploads bypass file type restrictions
- **MIME Type Support**: Extended list of supported file extensions

### File Flow
1. User selects file in Android app
2. File is copied to app's cache directory
3. App detects MIME type based on file extension
4. File is uploaded to Flask server with proper MIME type
5. Server saves file to `mobile_uploads` folder
6. Server returns success/error response

## Testing

### Test Script
Run the test script to verify functionality:
```bash
cd web_app
python test_file_upload.py
```

This script tests various file types and reports success/failure rates.

### Manual Testing
1. Build and install the Android app
2. Ensure Flask server is running on the correct IP
3. Test with different file types:
   - Text files (.txt, .json, .csv)
   - Images (.jpg, .png)
   - Documents (.pdf, .docx)
   - Archives (.zip, .rar)

## File Storage

### Server Location
All mobile uploads are stored in:
```
web_app/web_app/mobile_uploads/
```

### File Naming
- Files retain their original names
- Names are sanitized for security
- No duplicate handling (files with same name will overwrite)

## Security Considerations

### File Validation
- Mobile uploads accept any file with an extension
- Web uploads still use restricted file type list
- File names are sanitized using `secure_filename()`

### Network Security
- HTTP cleartext traffic is allowed for local development
- Network security config allows local IP addresses
- CORS is enabled for cross-origin requests

## Troubleshooting

### Common Issues
1. **Upload Fails**: Check server IP address in app settings
2. **File Not Found**: Ensure file exists and is accessible
3. **Network Error**: Verify both devices are on same network
4. **Permission Denied**: Check Android storage permissions

### Debug Information
- Check Flask server logs for upload details
- Android app shows upload status in toast messages
- Use test script to verify server functionality

## Future Enhancements
- File size limits and validation
- Progress indicators for large files
- File preview functionality
- Batch upload support
- File management interface 