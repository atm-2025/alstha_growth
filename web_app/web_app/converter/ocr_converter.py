import pytesseract
from PIL import Image
import os
import time

# Set Tesseract path explicitly to avoid PATH issues
# Try multiple common installation paths
tesseract_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Users\alsth\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
]

tesseract_found = False
for path in tesseract_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        tesseract_found = True
        break

if not tesseract_found:
    # If no explicit path found, try to use PATH (fallback)
    try:
        import subprocess
        result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            tesseract_found = True
    except:
        pass

if not tesseract_found:
    raise RuntimeError("Tesseract not found. Please install Tesseract OCR and ensure it's in your PATH or update the paths in this file.")

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))

def image_to_text(input_path):
    try:
        # Create OCR output directory
        ocr_out_dir = os.path.join(UPLOADS_DIR, 'ocr_results')
        os.makedirs(ocr_out_dir, exist_ok=True)
        
        img = Image.open(input_path)
        text = pytesseract.image_to_string(img)
        
        # Save extracted text to file
        base = os.path.splitext(os.path.basename(input_path))[0]
        timestamp = int(time.time())
        text_file_path = os.path.join(ocr_out_dir, f"{base}_extracted_text_{timestamp}.txt")
        
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        return text
    except Exception as e:
        # Provide detailed error information
        error_msg = f"OCR processing failed: {str(e)}"
        if "tesseract" in str(e).lower():
            error_msg += "\nTesseract path: " + pytesseract.pytesseract.tesseract_cmd
        raise RuntimeError(error_msg)

def pdf_to_text(input_path):
    try:
        from pdf2image import convert_from_path
        # Create OCR output directory
        ocr_out_dir = os.path.join(UPLOADS_DIR, 'ocr_results')
        os.makedirs(ocr_out_dir, exist_ok=True)
        
        pages = convert_from_path(input_path)
        text = ''
        for page in pages:
            text += pytesseract.image_to_string(page) + '\n'
        
        # Save extracted text to file
        base = os.path.splitext(os.path.basename(input_path))[0]
        timestamp = int(time.time())
        text_file_path = os.path.join(ocr_out_dir, f"{base}_extracted_text_{timestamp}.txt")
        
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        return text
    except Exception as e:
        # Provide detailed error information
        error_msg = f"PDF OCR processing failed: {str(e)}"
        if "tesseract" in str(e).lower():
            error_msg += "\nTesseract path: " + pytesseract.pytesseract.tesseract_cmd
        raise RuntimeError(error_msg) 