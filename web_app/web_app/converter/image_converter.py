import os
import subprocess
from PIL import Image

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))

def convert_image(input_path, output_format):
    """
    Convert an image to the specified format (e.g., 'png', 'jpg') using ImageMagick.
    Returns the output file path.
    """
    out_dir = os.path.join(UPLOADS_DIR, f'image_to_{output_format}')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, f"{base}_converted.{output_format}")
    result = subprocess.run(
        [r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe", input_path, output_path],
        capture_output=False, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if result.returncode != 0:
        raise RuntimeError("ImageMagick failed")
    return output_path

def image_to_ico(input_path):
    # Create ICO output directory
    ico_out_dir = os.path.join(UPLOADS_DIR, 'image_to_ico')
    os.makedirs(ico_out_dir, exist_ok=True)
    
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(ico_out_dir, f"{base}_converted.ico")
    img = Image.open(input_path)
    # ICO best practice: provide multiple sizes for Windows icons
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_path, format='ICO', sizes=sizes)
    return output_path

def raster_to_svg(input_path):
    # Convert PNG/JPG to SVG using potrace (requires PBM input)
    # Create SVG output directory
    svg_out_dir = os.path.join(UPLOADS_DIR, 'raster_to_svg')
    os.makedirs(svg_out_dir, exist_ok=True)
    
    base = os.path.splitext(os.path.basename(input_path))[0]
    pbm_path = os.path.join(svg_out_dir, f"{base}_trace.pbm")
    svg_path = os.path.join(svg_out_dir, f"{base}_converted.svg")
    # Convert to PBM (black and white)
    img = Image.open(input_path).convert('L').point(lambda x: 0 if x < 128 else 255, '1')
    img.save(pbm_path, 'PBM')
    # Call potrace
    command = ["potrace", pbm_path, "-s", "-o", svg_path]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Clean up temporary PBM file
    if os.path.exists(pbm_path):
        os.remove(pbm_path)
    return svg_path

def svg_to_raster(input_path, output_format):
    # Convert SVG to PNG or JPG using cairosvg
    import cairosvg
    # Create SVG to raster output directory
    svg_raster_out_dir = os.path.join(UPLOADS_DIR, f'svg_to_{output_format}')
    os.makedirs(svg_raster_out_dir, exist_ok=True)
    
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(svg_raster_out_dir, f"{base}_converted.{output_format}")
    
    if output_format == 'png':
        cairosvg.svg2png(url=input_path, write_to=output_path)
    elif output_format == 'jpg':
        # Convert to PNG first, then to JPG
        png_path = os.path.join(svg_raster_out_dir, f"{base}_converted.png")
        cairosvg.svg2png(url=input_path, write_to=png_path)
        img = Image.open(png_path).convert('RGB')
        img.save(output_path, 'JPEG')
        os.remove(png_path)  # Clean up temporary PNG
    else:
        cairosvg.svg2pdf(url=input_path, write_to=output_path)
    
    return output_path

def text_to_qr(text, output_path=None):
    import qrcode
    import time
    
    # Create QR code output directory
    qr_out_dir = os.path.join(UPLOADS_DIR, 'qr_codes')
    os.makedirs(qr_out_dir, exist_ok=True)
    
    if output_path is None:
        # Generate filename with timestamp
        timestamp = int(time.time())
        safe_text = "".join(c for c in text[:20] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_text = safe_text.replace(' ', '_')
        filename = f"qr_{safe_text}_{timestamp}.png"
        output_path = os.path.join(qr_out_dir, filename)
    
    # Create QR code with better settings for compatibility
    qr = qrcode.QRCode(
        version=1,  # Auto-determine version
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # Low error correction for better compatibility
        box_size=10,  # Larger boxes for better scanning
        border=4,  # White border around QR code
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    # Create image with better contrast
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize for better quality (minimum 300x300 pixels)
    if img.size[0] < 300:
        img = img.resize((300, 300), Image.Resampling.NEAREST)
    
    img.save(output_path, 'PNG', optimize=True)
    return output_path

def qr_to_text(input_path):
    from pyzbar.pyzbar import decode
    img = Image.open(input_path)
    decoded = decode(img)
    if decoded:
        return decoded[0].data.decode('utf-8')
    return ''

def reduce_image_size(input_path, output_format, quality=70, max_width=None, max_height=None):
    """
    Reduce the file size of an image by resizing and/or compressing.
    output_format: 'jpg' or 'png'
    quality: JPEG quality (1-95), PNG compression (optimize)
    max_width, max_height: if set, resize to fit within these dimensions
    Returns the output file path.
    """
    img = Image.open(input_path)
    if max_width or max_height:
        # Calculate new size maintaining aspect ratio
        orig_width, orig_height = img.size
        ratio = 1.0
        if max_width and orig_width > max_width:
            ratio = min(ratio, max_width / orig_width)
        if max_height and orig_height > max_height:
            ratio = min(ratio, max_height / orig_height)
        if ratio < 1.0:
            new_size = (int(orig_width * ratio), int(orig_height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_dir = os.path.join(UPLOADS_DIR, f'image_reduced_{output_format}')
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, f"{base}_reduced.{output_format}")
    if output_format.lower() == 'jpg' or output_format.lower() == 'jpeg':
        img = img.convert('RGB')
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
    elif output_format.lower() == 'png':
        img.save(output_path, 'PNG', optimize=True)
    else:
        raise ValueError('Unsupported format for image size reduction')
    return output_path