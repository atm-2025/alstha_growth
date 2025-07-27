import os
import subprocess

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))

def convert_word_to_pdf(input_path):
    input_dir = os.path.dirname(input_path)
    filename_wo_ext = os.path.splitext(os.path.basename(input_path))[0]
    expected_pdf = os.path.join(input_dir, f"{filename_wo_ext}.pdf")
    out_dir = os.path.join(UPLOADS_DIR, 'word_to_pdf')
    os.makedirs(out_dir, exist_ok=True)
    output_pdf = os.path.join(out_dir, f"{filename_wo_ext}_converted.pdf")
    try:
        result = subprocess.run([
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            "--headless", "--convert-to", "pdf", "--outdir", input_dir, input_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            raise RuntimeError("LibreOffice failed")
        if not os.path.exists(expected_pdf):
            raise FileNotFoundError(f"LibreOffice did not create {expected_pdf}")
        os.replace(expected_pdf, output_pdf)
        return output_pdf
    except Exception as e:
        print(f"Error in convert_word_to_pdf: {e}")
        raise 