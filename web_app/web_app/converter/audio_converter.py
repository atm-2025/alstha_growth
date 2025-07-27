import os
import subprocess

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))

def mp3_to_wav(input_path):
    out_dir = os.path.join(UPLOADS_DIR, 'mp3_to_wav')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, f"{base}_converted.wav")
    command = [
        "ffmpeg", "-i", input_path, "-y", output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path

def wav_to_mp3(input_path):
    out_dir = os.path.join(UPLOADS_DIR, 'wav_to_mp3')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, f"{base}_converted.mp3")
    command = [
        "ffmpeg", "-i", input_path, "-y", output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path

def m4a_to_mp3(input_path):
    out_dir = os.path.join(UPLOADS_DIR, 'm4a_to_mp3')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, f"{base}_converted.mp3")
    command = [
        "ffmpeg", "-i", input_path, "-y", output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path

def mp3_to_m4a(input_path):
    out_dir = os.path.join(UPLOADS_DIR, 'mp3_to_m4a')
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, f"{base}_converted.m4a")
    command = [
        "ffmpeg", "-i", input_path, "-y", output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path 