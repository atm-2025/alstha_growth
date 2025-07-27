import os
import subprocess

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))

def convert_mp4_to_mp3(input_path):
    out_dir = os.path.join(UPLOADS_DIR, 'mp4_to_mp3')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, f"{base}_converted.mp3")
    command = [
        "ffmpeg", "-i", input_path, "-vn", "-acodec", "libmp3lame", "-y", output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path

def gif_to_mp4(input_path):
    out_dir = os.path.join(UPLOADS_DIR, 'gif_to_mp4')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, f"{base}_converted.mp4")
    command = [
        "ffmpeg", "-f", "gif", "-i", input_path, "-movflags", "+faststart", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-y", output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path

def mp4_to_gif(input_path):
    out_dir = os.path.join(UPLOADS_DIR, 'mp4_to_gif')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, f"{base}_converted.gif")
    command = [
        "ffmpeg", "-i", input_path, "-vf", "fps=10,scale=320:-1:flags=lanczos", "-y", output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path