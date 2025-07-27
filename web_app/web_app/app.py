import os
import logging
import subprocess
import sys
import ctypes
import socket
import pyautogui
from flask import Flask, request, jsonify, render_template, send_from_directory, Blueprint, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
from converter.image_converter import convert_image, image_to_ico, raster_to_svg, svg_to_raster, text_to_qr, qr_to_text, reduce_image_size
from converter.video_converter import convert_mp4_to_mp3, gif_to_mp4, mp4_to_gif
from converter.document_converter import convert_word_to_pdf
import zipfile
import tempfile
from converter.archive_converter import archive_files_to_zip
from converter.audio_converter import mp3_to_wav, wav_to_mp3, m4a_to_mp3, mp3_to_m4a
from converter.ocr_converter import image_to_text, pdf_to_text
from converter.tts_converter import text_to_mp3, text_to_wav
import time
from converter.yt_downloader import download_yt_mp3, download_yt_mp4, download_yt_playlist_mp3, download_yt_playlist_mp4

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure Flask for large file uploads
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max file size
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'mp4', 'avi', 'mov', 'mkv', 'mp3', 'wav', 'flac', 'aac', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'json', 'xml', 'zip', 'rar', '7z', 'tar', 'gz'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

MOBILE_UPLOADS_FOLDER = os.path.join(BASE_DIR, 'mobile_uploads')
if not os.path.exists(MOBILE_UPLOADS_FOLDER):
    os.makedirs(MOBILE_UPLOADS_FOLDER)

SEND_TO_MOBILE_FOLDER = os.path.join(BASE_DIR, 'send_to_mobile')
if not os.path.exists(SEND_TO_MOBILE_FOLDER):
    os.makedirs(SEND_TO_MOBILE_FOLDER)

latest_result = {'text': '', 'filename': ''} 

@app.route('/')
def home():
    return "Flask server is running!"

@app.route('/test', methods=['GET'])
def test_connection():
    """Test endpoint for Android app to verify connection"""
    return jsonify({
        'status': 'success',
        'message': 'Server is reachable',
        'timestamp': time.time()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check if upload folders exist
        web_uploads_ok = os.path.exists(app.config['UPLOAD_FOLDER'])
        mobile_uploads_ok = os.path.exists(MOBILE_UPLOADS_FOLDER)
        
        return jsonify({
            'status': 'healthy',
            'web_uploads_folder': web_uploads_ok,
            'mobile_uploads_folder': mobile_uploads_ok,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/command', methods=['POST'])
def handle_command():
    """Handle commands from Android app"""
    try:
        data = request.get_json()
        action = data.get('action')
        
        logger.info(f"Received command: {action}")
        
        if action == "sleep":
            # Use AutoHotkey script for sleep
            try:
                # Try to find and run the AutoHotkey script
                script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'sleep.ahk')
                if os.path.exists(script_path):
                    subprocess.run([script_path])
                    return jsonify({"status": "ok", "result": "Sleep triggered"})
                else:
                    return jsonify({"status": "error", "result": "Sleep script not found"})
            except Exception as e:
                return jsonify({"status": "error", "result": f"Sleep failed: {e}"})
        
        elif action == "shutdown":
            subprocess.run(["shutdown", "/s", "/t", "0"])
            return jsonify({"status": "ok", "result": "Shutdown triggered"})
        
        elif action == "hibernate":
            subprocess.run(["shutdown", "/h"])
            return jsonify({"status": "ok", "result": "Hibernate triggered"})
        
        elif action == "restart":
            subprocess.run(["shutdown", "/r", "/t", "0"])
            return jsonify({"status": "ok", "result": "Restart triggered"})
        
        elif action == "open_notepad":
            if sys.platform.startswith("win"):
                subprocess.Popen(["notepad.exe"])
                return jsonify({"status": "ok", "result": "Notepad opened"})
            else:
                return jsonify({"status": "error", "result": "Notepad only available on Windows"})
        
        elif action == "lock_workstation":
            ctypes.windll.user32.LockWorkStation()
            return jsonify({"status": "ok", "result": "Workstation locked"})
        
        elif action == "open_calculator":
            subprocess.Popen(["calc.exe"])
            return jsonify({"status": "ok", "result": "Calculator opened"})
        
        elif action == "show_ip_address":
            ip = socket.gethostbyname(socket.gethostname())
            return jsonify({"status": "ok", "result": f"IP Address: {ip}"})
        
        elif action == "take_screenshot":
            try:
                screenshot = pyautogui.screenshot()
                screenshot_path = os.path.join(app.config['UPLOAD_FOLDER'], "screenshot.png")
                screenshot.save(screenshot_path)
                return jsonify({"status": "ok", "result": f"Screenshot saved as {screenshot_path}"})
            except Exception as e:
                return jsonify({"status": "error", "result": f"Screenshot failed: {e}"})
        
        elif action == "show_message_box":
            ctypes.windll.user32.MessageBoxW(0, "Hello from Android Command!", "Message", 1)
            return jsonify({"status": "ok", "result": "Message box shown"})
        
        else:
            return jsonify({"status": "error", "result": f"Unknown command: {action}"})
            
    except Exception as e:
        logger.error(f"Error handling command: {e}")
        return jsonify({"status": "error", "result": str(e)}), 500

def allowed_file(filename, source=None):
    # For mobile uploads, allow all file types
    if source == 'mobile':
        return '.' in filename  # Allow any file with an extension
    # For web uploads, use the restricted list
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def dummy_ml_process(image_path):
    # Replace this with your ML code
    # For now, just return the filename as 'recognized text'
    return f"Processed: {os.path.basename(image_path)}"

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Safely get remote address
        try:
            remote_addr = request.remote_addr or "unknown"
            logger.info(f"Upload request received from: {remote_addr}")
        except Exception as e:
            logger.info(f"Upload request received from: unknown (error getting address: {e})")
        
        # Check if client is still connected before processing
        try:
            # Safely log headers
            try:
                logger.info(f"Request headers: {dict(request.headers)}")
            except Exception as e:
                logger.info(f"Could not log headers: {e}")
            
            # Get source from headers first (safer than form data)
            source = request.headers.get('Source') or 'unknown'
            logger.info(f"Source from headers: {source}")
            
            # Check if we can access form data
            try:
                form_data = dict(request.form)
                logger.info(f"Request form data: {form_data}")
                # Update source from form if available
                if 'source' in form_data:
                    source = form_data['source']
                    logger.info(f"Source updated from form: {source}")
            except Exception as e:
                logger.info(f"Could not access form data: {e}")
                # If we can't access form data, client might have disconnected
                return jsonify({'error': 'Client disconnected during upload'}), 400
            
            # Check if file is present
            if 'file' not in request.files:
                logger.info("No file part in request")
                return jsonify({'error': 'No file part'}), 400
            
            file = request.files['file']
            if file.filename == '':
                logger.info("No selected file")
                return jsonify({'error': 'No selected file'}), 400
            
            if file and allowed_file(file.filename, source):
                filename = secure_filename(os.path.basename(file.filename))
                
                # Check file size (optional, Flask will handle this automatically)
                try:
                    # Get content length from headers
                    content_length = request.content_length
                    if content_length:
                        size_mb = content_length / (1024 * 1024)
                        logger.info(f"Processing file: {filename} (Size: {size_mb:.2f} MB)")
                        
                        # Warn for very large files
                        if size_mb > 100:
                            logger.warning(f"Large file detected: {filename} ({size_mb:.2f} MB)")
                        if size_mb > 500:
                            logger.warning(f"Very large file: {filename} ({size_mb:.2f} MB) - This may take a while")
                    else:
                        logger.info(f"Processing file: {filename} (Size: unknown)")
                except Exception as e:
                    logger.info(f"Processing file: {filename} (Size check failed: {e})")
                
                # Determine upload folder
                if source == 'mobile':
                    upload_folder = MOBILE_UPLOADS_FOLDER
                else:
                    upload_folder = app.config['UPLOAD_FOLDER']
                logger.info(f"Upload folder: {upload_folder}")
                
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                    logger.info(f"Created upload folder: {upload_folder}")
                
                filepath = os.path.join(upload_folder, filename)
                logger.info(f"Saving file to: {filepath}")
                
                # Save file with error handling and progress logging
                try:
                    start_time = time.time()
                    file.save(filepath)
                    end_time = time.time()
                    
                    # Log file save completion
                    if content_length:
                        size_mb = content_length / (1024 * 1024)
                        duration = end_time - start_time
                        speed = size_mb / duration if duration > 0 else 0
                        logger.info(f"File saved successfully: {filepath}")
                        logger.info(f"Upload stats: {size_mb:.2f} MB in {duration:.2f} seconds ({speed:.2f} MB/s)")
                    else:
                        logger.info(f"File saved successfully to: {filepath}")
                        
                except Exception as save_error:
                    logger.error(f"Error saving file: {save_error}")
                    return jsonify({'error': f'Failed to save file: {str(save_error)}'}), 500
                
                # Run dummy ML
                result_text = dummy_ml_process(filepath)
                global latest_result
                latest_result = {'text': result_text, 'filename': filename}
                logger.info(f"Processing complete: {result_text}")
                return jsonify({'result': result_text}), 200
            else:
                logger.info(f"File type not allowed: {file.filename}")
                return jsonify({'error': f'File type not allowed: {file.filename}'}), 400
                
        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            return jsonify({'error': f'Upload processing failed: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/result', methods=['GET'])
def get_result():
    return jsonify(latest_result)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('dashboard.html', result=latest_result)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/files', methods=['GET'])
def list_files():
    """List all files available for download from send_to_mobile folder"""
    try:
        files = []
        folder = SEND_TO_MOBILE_FOLDER
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    file_size = int(os.path.getsize(file_path))
                    file_modified = int(os.path.getmtime(file_path))
                    # Format file size
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size // 1024} KB"
                    else:
                        size_str = f"{file_size // (1024 * 1024)} MB"
                    file_ext = os.path.splitext(filename)[1].lower()
                    files.append({
                        'name': filename,
                        'size': size_str,
                        'size_bytes': file_size,
                        'modified': file_modified,
                        'extension': file_ext
                    })
        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({
            'status': 'success',
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to list files: {str(e)}'
        }), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download a specific file from send_to_mobile folder"""
    try:
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        file_path = os.path.join(SEND_TO_MOBILE_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        if not os.path.isfile(file_path):
            return jsonify({'error': 'Not a file'}), 400
        logger.info(f"File download requested: {filename}")
        return send_from_directory(
            SEND_TO_MOBILE_FOLDER,
            filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({
            'error': f'Download failed: {str(e)}'
        }), 500

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file from the send_to_mobile folder"""
    try:
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        file_path = os.path.join(SEND_TO_MOBILE_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        if not os.path.isfile(file_path):
            return jsonify({'error': 'Not a file'}), 400
        os.remove(file_path)
        logger.info(f"File deleted: {filename}")
        return jsonify({
            'status': 'success',
            'message': f'File {filename} deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}")
        return jsonify({
            'error': f'Delete failed: {str(e)}'
        }), 500

@app.route('/file-info/<filename>', methods=['GET'])
def get_file_info(filename):
    """Get detailed information about a file in send_to_mobile folder"""
    try:
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        file_path = os.path.join(SEND_TO_MOBILE_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        if not os.path.isfile(file_path):
            return jsonify({'error': 'Not a file'}), 400
        file_size = int(os.path.getsize(file_path))
        file_modified = int(os.path.getmtime(file_path))
        file_created = int(os.path.getctime(file_path))
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size // 1024} KB"
        else:
            size_str = f"{file_size // (1024 * 1024)} MB"
        file_ext = os.path.splitext(filename)[1].lower()
        return jsonify({
            'status': 'success',
            'file': {
                'name': filename,
                'size': size_str,
                'size_bytes': file_size,
                'modified': file_modified,
                'created': file_created,
                'extension': file_ext,
                'path': file_path
            }
        })
    except Exception as e:
        logger.error(f"Error getting file info for {filename}: {e}")
        return jsonify({
            'error': f'Failed to get file info: {str(e)}'
        }), 500

converter_bp = Blueprint('converter', __name__, url_prefix='/convert')

@converter_bp.route('/image', methods=['POST'])
def convert_image_endpoint():
    if 'file' not in request.files or 'format' not in request.form:
        return jsonify({'error': 'File and format required'}), 400
    file = request.files['file']
    output_format = request.form['format']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    output_path = convert_image(input_path, output_format)
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/video', methods=['POST'])
def convert_video_endpoint():
    if 'file' not in request.files:
        return jsonify({'error': 'File required'}), 400
    file = request.files['file']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    output_path = convert_mp4_to_mp3(input_path)
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/document', methods=['POST'])
def convert_document_endpoint():
    if 'file' not in request.files:
        return jsonify({'error': 'File required'}), 400
    file = request.files['file']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    output_path = convert_word_to_pdf(input_path)
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/archive', methods=['POST'])
def convert_archive_endpoint():
    # Accepts multiple files, returns a ZIP archive
    if 'files' not in request.files:
        return jsonify({'error': 'Files required'}), 400
    files = request.files.getlist('files')
    zip_name = archive_files_to_zip(files)
    return send_file(zip_name, as_attachment=True, download_name='archive.zip')

@converter_bp.route('/unzip', methods=['POST'])
def convert_unzip_endpoint():
    if 'file' not in request.files:
        return jsonify({'error': 'ZIP file required'}), 400
    zip_file = request.files['file']
    from converter.archive_converter import extract_zip_to_zip
    out_zip = extract_zip_to_zip(zip_file)
    return send_file(out_zip, as_attachment=True, download_name='unzipped_contents.zip')

@converter_bp.route('/audio', methods=['POST'])
def convert_audio_endpoint():
    if 'file' not in request.files or 'direction' not in request.form:
        return jsonify({'error': 'File and direction required'}), 400
    file = request.files['file']
    direction = request.form['direction']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    if direction == 'mp3_to_wav':
        output_path = mp3_to_wav(input_path)
    elif direction == 'wav_to_mp3':
        output_path = wav_to_mp3(input_path)
    else:
        return jsonify({'error': 'Invalid direction'}), 400
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/gifmp4', methods=['POST'])
def convert_gifmp4_endpoint():
    if 'file' not in request.files or 'direction' not in request.form:
        return jsonify({'error': 'File and direction required'}), 400
    file = request.files['file']
    direction = request.form['direction']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    if direction == 'gif_to_mp4':
        output_path = gif_to_mp4(input_path)
    elif direction == 'mp4_to_gif':
        output_path = mp4_to_gif(input_path)
    else:
        return jsonify({'error': 'Invalid direction'}), 400
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/ico', methods=['POST'])
def convert_ico_endpoint():
    if 'file' not in request.files:
        return jsonify({'error': 'File required'}), 400
    file = request.files['file']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    output_path = image_to_ico(input_path)
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/svg', methods=['POST'])
def convert_svg_endpoint():
    if 'file' not in request.files or 'direction' not in request.form:
        return jsonify({'error': 'File and direction required'}), 400
    file = request.files['file']
    direction = request.form['direction']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    if direction == 'raster_to_svg':
        output_path = raster_to_svg(input_path)
    elif direction == 'svg_to_raster':
        output_format = request.form.get('format', 'png')
        output_path = svg_to_raster(input_path, output_format)
    else:
        return jsonify({'error': 'Invalid direction'}), 400
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/m4amp3', methods=['POST'])
def convert_m4amp3_endpoint():
    if 'file' not in request.files or 'direction' not in request.form:
        return jsonify({'error': 'File and direction required'}), 400
    file = request.files['file']
    direction = request.form['direction']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    if direction == 'm4a_to_mp3':
        output_path = m4a_to_mp3(input_path)
    elif direction == 'mp3_to_m4a':
        output_path = mp3_to_m4a(input_path)
    else:
        return jsonify({'error': 'Invalid direction'}), 400
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/qr', methods=['POST'])
def convert_qr_endpoint():
    if 'mode' not in request.form:
        return jsonify({'error': 'Mode required'}), 400
    mode = request.form['mode']
    if mode == 'text_to_qr':
        text = request.form.get('text', '')
        if not text:
            return jsonify({'error': 'Text required'}), 400
        output_path = text_to_qr(text)
        return send_file(output_path, as_attachment=True)
    elif mode == 'qr_to_text':
        if 'file' not in request.files:
            return jsonify({'error': 'QR image file required'}), 400
        file = request.files['file']
        filename = secure_filename(os.path.basename(file.filename))
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        decoded = qr_to_text(input_path)
        # Delete the original file after conversion
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({'text': decoded})
    else:
        return jsonify({'error': 'Invalid mode'}), 400

@converter_bp.route('/ocr', methods=['POST'])
def convert_ocr_endpoint():
    if 'file' not in request.files or 'mode' not in request.form:
        return jsonify({'error': 'File and mode required'}), 400
    file = request.files['file']
    mode = request.form['mode']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    if mode == 'image_to_text':
        text = image_to_text(input_path)
    elif mode == 'pdf_to_text':
        text = pdf_to_text(input_path)
    else:
        return jsonify({'error': 'Invalid mode'}), 400
    # Delete the original file after conversion
    if os.path.exists(input_path):
        os.remove(input_path)
    return text, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@converter_bp.route('/tts', methods=['POST'])
def convert_tts_endpoint():
    text = request.form.get('text', '')
    fmt = request.form.get('format', 'mp3')
    if not text:
        return jsonify({'error': 'Text required'}), 400
    if fmt == 'mp3':
        output_path = text_to_mp3(text)
    elif fmt == 'wav':
        output_path = text_to_wav(text)
    else:
        return jsonify({'error': 'Invalid format'}), 400
    return send_file(output_path, as_attachment=True)

@converter_bp.route('/yt-mp3', methods=['POST'])
def convert_yt_mp3_endpoint():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'URL required'}), 400
    try:
        download_yt_mp3(url)
        return jsonify({'status': 'success', 'message': 'Downloaded as mp3 to yt_converted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@converter_bp.route('/yt-mp4', methods=['POST'])
def convert_yt_mp4_endpoint():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'URL required'}), 400
    try:
        download_yt_mp4(url)
        return jsonify({'status': 'success', 'message': 'Downloaded as mp4 to yt_converted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@converter_bp.route('/yt-playlist-mp3', methods=['POST'])
def convert_yt_playlist_mp3_endpoint():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'Playlist URL required'}), 400
    try:
        download_yt_playlist_mp3(url)
        return jsonify({'status': 'success', 'message': 'Playlist downloaded as mp3 to yt_converted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@converter_bp.route('/yt-playlist-mp4', methods=['POST'])
def convert_yt_playlist_mp4_endpoint():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'Playlist URL required'}), 400
    try:
        download_yt_playlist_mp4(url)
        return jsonify({'status': 'success', 'message': 'Playlist downloaded as mp4 to yt_converted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@converter_bp.route('/reduce', methods=['POST'])
def reduce_file_size_endpoint():
    if 'file' not in request.files or 'type' not in request.form:
        return jsonify({'error': 'File and type required'}), 400
    file = request.files['file']
    file_type = request.form['type']
    filename = secure_filename(os.path.basename(file.filename))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)
    try:
        if file_type == 'image':
            output_format = request.form.get('format', 'jpg')
            quality = int(request.form.get('quality', 70))
            max_width = request.form.get('max_width', type=int)
            max_height = request.form.get('max_height', type=int)
            output_path = reduce_image_size(input_path, output_format, quality, max_width, max_height)
        elif file_type == 'video':
            # TODO: Implement video size reduction (use FFmpeg)
            return jsonify({'error': 'Video reduction not implemented yet'}), 501
        elif file_type == 'audio':
            # TODO: Implement audio size reduction (use FFmpeg)
            return jsonify({'error': 'Audio reduction not implemented yet'}), 501
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({'error': str(e)}), 500
    if os.path.exists(input_path):
        os.remove(input_path)
    return send_file(output_path, as_attachment=True)

app.register_blueprint(converter_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 