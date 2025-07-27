import os

def text_to_mp3(text, output_path=None):
    from gtts import gTTS
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads', 'text_to_mp3'))
    os.makedirs(out_dir, exist_ok=True)
    if output_path is None:
        import tempfile
        fd, output_path = tempfile.mkstemp(suffix='.mp3', dir=out_dir)
        os.close(fd)
    tts = gTTS(text)
    tts.save(output_path)
    return output_path

def text_to_wav(text, output_path=None):
    import pyttsx3
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads', 'text_to_wav'))
    os.makedirs(out_dir, exist_ok=True)
    if output_path is None:
        import tempfile
        fd, output_path = tempfile.mkstemp(suffix='.wav', dir=out_dir)
        os.close(fd)
    engine = pyttsx3.init()
    engine.save_to_file(text, output_path)
    engine.runAndWait()
    return output_path 