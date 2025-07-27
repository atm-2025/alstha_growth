import os
import zipfile
import tempfile
from werkzeug.utils import secure_filename

def archive_files_to_zip(files):
    temp_dir = tempfile.mkdtemp()
    zip_name = os.path.join(temp_dir, 'archive.zip')
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            filename = secure_filename(os.path.basename(file.filename))
            file_path = os.path.join(temp_dir, filename)
            file.save(file_path)
            zipf.write(file_path, arcname=filename)
    return zip_name

def extract_zip_to_zip(zip_file):
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, secure_filename(os.path.basename(zip_file.filename)))
    zip_file.save(zip_path)
    extract_dir = os.path.join(temp_dir, 'extracted')
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(extract_dir)
    # Re-zip the extracted files (preserving folder structure)
    out_zip = os.path.join(temp_dir, 'unzipped_contents.zip')
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, extract_dir)
                zipf.write(abs_path, arcname=rel_path)
    return out_zip 