#!/usr/bin/env python3
"""
Jarvis AI Assistant Setup Script
Installs required dependencies for AI-powered command processing
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Fix for typing.Self compatibility in Python 3.10
if sys.version_info < (3, 11):
    try:
        import typing_extensions
        if not hasattr(typing_extensions, 'Self'):
            # Create a fallback Self type for older typing_extensions versions
            from typing import TypeVar
            Self = TypeVar('Self', bound='object')
            setattr(typing_extensions, 'Self', Self)
    except ImportError:
        pass

def print_banner():
    """Print setup banner"""
    print("=" * 60)
    print("🤖 JARVIS AI Assistant Setup")
    print("=" * 60)
    print("This script will install the required dependencies for")
    print("AI-powered voice commands and natural language processing.")
    print("=" * 60)

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def install_package(package, description=""):
    """Install a Python package"""
    print(f"📦 Installing {package}...")
    if description:
        print(f"   {description}")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def install_core_dependencies():
    """Install core dependencies"""
    print("\n🔧 Installing Core Dependencies...")
    
    core_packages = [
        ("typing-extensions>=4.5.0", "Enhanced typing support for older Python versions"),
        ("PySide6>=6.5.0", "Qt GUI framework"),
        ("opencv-python>=4.8.0", "Computer vision library"),
        ("numpy>=1.24.0", "Numerical computing"),
        ("requests>=2.31.0", "HTTP library"),
        ("pyautogui>=0.9.54", "GUI automation"),
        ("pyperclip>=1.8.2", "Clipboard operations"),
        ("youtube-transcript-api>=0.6.0", "YouTube transcript extraction"),
        ("yt-dlp>=2023.0.0", "YouTube video downloading")
    ]
    
    success_count = 0
    for package, description in core_packages:
        if install_package(package, description):
            success_count += 1
    
    return success_count == len(core_packages)

def install_ai_dependencies():
    """Install AI/ML dependencies"""
    print("\n🧠 Installing AI/ML Dependencies...")
    
    ai_packages = [
        ("torch>=2.0.0", "PyTorch deep learning framework"),
        ("transformers>=4.30.0", "Hugging Face transformers library"),
        ("sentence-transformers>=2.2.0", "Sentence embeddings for DistilBERT"),
        ("accelerate>=0.20.0", "Accelerated model loading"),
        ("bitsandbytes>=0.41.0", "Quantization for Phi-2"),
        ("scikit-learn>=1.3.0", "Machine learning utilities"),
        ("scipy>=1.10.0", "Scientific computing")
    ]
    
    success_count = 0
    for package, description in ai_packages:
        if install_package(package, description):
            success_count += 1
    
    return success_count == len(ai_packages)

def install_audio_dependencies():
    """Install audio processing dependencies"""
    print("\n🎤 Installing Audio Dependencies...")
    
    audio_packages = [
        ("speechrecognition>=3.10.0", "Speech recognition library"),
        ("pyttsx3>=2.90", "Text-to-speech library")
    ]
    
    # PyAudio installation is platform-specific
    if platform.system() == "Windows":
        try:
            print("📦 Installing PyAudio for Windows...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyaudio"])
            print("✅ PyAudio installed successfully")
        except subprocess.CalledProcessError:
            print("⚠️  PyAudio installation failed. You may need to install it manually.")
            print("   Download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio")
    else:
        audio_packages.append(("pyaudio>=0.2.11", "Audio I/O library"))
    
    success_count = 0
    for package, description in audio_packages:
        if install_package(package, description):
            success_count += 1
    
    return success_count == len(audio_packages)

def install_system_dependencies():
    """Install system utility dependencies"""
    print("\n⚙️  Installing System Dependencies...")
    
    system_packages = [
        ("psutil>=5.9.0", "System and process utilities"),
        ("python-dotenv>=1.0.0", "Environment variable management"),
        ("colorama>=0.4.6", "Cross-platform colored terminal text"),
        ("tqdm>=4.65.0", "Progress bars")
    ]
    
    # Windows-specific packages
    if platform.system() == "Windows":
        system_packages.extend([
            ("pywin32>=306", "Windows API access"),
            ("ctypes-windows-sdk>=0.0.1", "Windows SDK utilities")
        ])
    
    success_count = 0
    for package, description in system_packages:
        if install_package(package, description):
            success_count += 1
    
    return success_count == len(system_packages)

def fix_typing_compatibility():
    """Fix typing compatibility issues"""
    print("\n🔧 Fixing Typing Compatibility...")
    
    try:
        # Ensure typing_extensions is installed
        import typing_extensions
        print("✅ typing_extensions is available")
        
        # Create a compatibility patch for packages that use typing.Self
        if sys.version_info < (3, 11):
            import typing
            if not hasattr(typing, 'Self'):
                from typing import TypeVar
                Self = TypeVar('Self', bound='object')
                setattr(typing, 'Self', Self)
                print("✅ Added typing.Self compatibility for Python 3.10")
        
    except ImportError:
        print("❌ typing_extensions not available")
        return False
    
    return True

def download_models():
    """Download AI models (optional)"""
    print("\n📥 Downloading AI Models...")
    print("This step is optional and can be done later when you first use Jarvis.")
    print("Models will be downloaded automatically on first use.")
    
    response = input("Download models now? (y/N): ").lower().strip()
    if response in ['y', 'yes']:
        try:
            print("📥 Downloading DistilBERT model...")
            subprocess.check_call([
                sys.executable, "-c", 
                "from sentence_transformers import SentenceTransformer; "
                "SentenceTransformer('distilbert-base-nli-mean-tokens')"
            ])
            print("✅ DistilBERT model downloaded")
            
            print("📥 Downloading Microsoft Phi-2 model...")
            subprocess.check_call([
                sys.executable, "-c",
                "from transformers import AutoTokenizer, AutoModelForCausalLM; "
                "tokenizer = AutoTokenizer.from_pretrained('microsoft/phi-2'); "
                "model = AutoModelForCausalLM.from_pretrained('microsoft/phi-2')"
            ])
            print("✅ Phi-2 model downloaded")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Model download failed: {e}")
            print("Models will be downloaded automatically when needed.")

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating Directories...")
    
    base_dir = Path(__file__).parent
    directories = [
        base_dir / "models",
        base_dir / "logs",
        base_dir / "cache"
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)
        print(f"✅ Created: {directory}")

def test_installation():
    """Test the installation"""
    print("\n🧪 Testing Installation...")
    
    tests = [
        ("Typing Extensions", "import typing_extensions"),
        ("PySide6", "from PySide6.QtWidgets import QApplication"),
        ("OpenCV", "import cv2"),
        ("NumPy", "import numpy as np"),
        ("Torch", "import torch"),
        ("Transformers", "from transformers import AutoTokenizer"),
        ("Sentence Transformers", "from sentence_transformers import SentenceTransformer"),
        ("Speech Recognition", "import speech_recognition as sr"),
        ("Text-to-Speech", "import pyttsx3"),
        ("System Utils", "import psutil")
    ]
    
    success_count = 0
    for name, import_statement in tests:
        try:
            exec(import_statement)
            print(f"✅ {name}: OK")
            success_count += 1
        except ImportError as e:
            print(f"❌ {name}: Failed - {e}")
    
    return success_count == len(tests)

def cleanup_tensorflow_keras():
    """Uninstall tensorflow, keras, tf-keras if present"""
    print("\n🧹 Cleaning up TensorFlow/Keras (not needed for PyTorch-only setup)...")
    pkgs = ["tensorflow", "keras", "tf-keras"]
    for pkg in pkgs:
        try:
            subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", pkg])
        except Exception:
            pass
    print("✅ TensorFlow/Keras cleanup complete.")

# Call cleanup at the start
cleanup_tensorflow_keras()

# Warn if Python 3.12+
if sys.version_info.major == 3 and sys.version_info.minor >= 12:
    print("⚠️  Warning: Some AI libraries may not yet fully support Python 3.12+. If you encounter issues, use Python 3.10 or 3.11.")

def main():
    """Main setup function"""
    print_banner()
    
    if not check_python_version():
        return False
    
    print(f"\n🖥️  Platform: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {sys.executable}")
    
    # Install dependencies
    core_ok = install_core_dependencies()
    ai_ok = install_ai_dependencies()
    audio_ok = install_audio_dependencies()
    system_ok = install_system_dependencies()
    
    # Fix typing compatibility
    typing_ok = fix_typing_compatibility()
    
    # Create directories
    create_directories()
    
    # Download models (optional)
    download_models()
    
    # Test installation
    test_ok = test_installation()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Installation Summary")
    print("=" * 60)
    print(f"Core Dependencies: {'✅' if core_ok else '❌'}")
    print(f"AI Dependencies: {'✅' if ai_ok else '❌'}")
    print(f"Audio Dependencies: {'✅' if audio_ok else '❌'}")
    print(f"System Dependencies: {'✅' if system_ok else '❌'}")
    print(f"Typing Compatibility: {'✅' if typing_ok else '❌'}")
    print(f"Installation Test: {'✅' if test_ok else '❌'}")
    
    if all([core_ok, ai_ok, audio_ok, system_ok, typing_ok, test_ok]):
        print("\n🎉 Setup completed successfully!")
        print("You can now run the Jarvis AI Assistant.")
        print("\nTo start Jarvis:")
        print("  python app_simplified.py")
        return True
    else:
        print("\n⚠️  Setup completed with some issues.")
        print("Some features may not work properly.")
        print("Please check the error messages above and try again.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1) 