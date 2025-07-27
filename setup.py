#!/usr/bin/env python3
"""
Setup script for Alstha Growth project
This script helps configure the environment and install dependencies.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_banner():
    """Print the setup banner."""
    print("=" * 60)
    print("🚀 Alstha Growth - Setup Script")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 10):
        print("❌ Error: Python 3.10 or higher is required.")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")

def create_env_file():
    """Create .env file with template values."""
    env_path = Path(".env")
    if env_path.exists():
        print("✅ .env file already exists")
        return
    
    env_content = """# API Keys (replace with your actual keys)
GROQ_API_KEY=your_groq_api_key_here
COHERE_API_KEY=your_cohere_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
GOOGLE_GEMINI_API_KEY=your_google_gemini_api_key_here
CEREBRAS_API_KEY=your_cerebras_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
MIXTRAL_API_KEY=your_mixtral_api_key_here

# Web App Configuration
WEB_APP_PORT=5000
WEB_APP_HOST=0.0.0.0

# Database Configuration
DATABASE_PATH=db/daily_logs.db
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    print("✅ Created .env file with template values")

def create_db_directory():
    """Create database directory."""
    db_path = Path("db")
    db_path.mkdir(exist_ok=True)
    print("✅ Database directory created")

def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing dependencies...")
    
    # Windows client dependencies
    windows_client_path = Path("web_app/windows_client")
    if windows_client_path.exists():
        print("Installing Windows client dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", 
                       windows_client_path / "requirements.txt"], check=True)
    
    # Web app dependencies
    web_app_path = Path("web_app/web_app")
    if web_app_path.exists():
        print("Installing web app dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", 
                       web_app_path / "requirements.txt"], check=True)
    
    print("✅ Dependencies installed successfully")

def create_android_local_properties():
    """Create local.properties for Android project."""
    android_path = Path("web_app/alstha_growth/local.properties")
    if android_path.exists():
        print("✅ Android local.properties already exists")
        return
    
    # Detect Android SDK path
    sdk_path = None
    if platform.system() == "Windows":
        possible_paths = [
            os.path.expanduser("~/AppData/Local/Android/Sdk"),
            "C:/Users/Public/AppData/Local/Android/Sdk",
            "C:/Android/Sdk"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                sdk_path = path.replace("/", "\\")
                break
    
    if not sdk_path:
        sdk_path = "C:\\Users\\YourUsername\\AppData\\Local\\Android\\Sdk"
        print("⚠️  Could not detect Android SDK path automatically")
        print(f"   Please update {android_path} with your SDK path")
    
    content = f"""## This file must *NOT* be checked into Version Control Systems,
# as it contains information specific to your local configuration.
#
# Location of the SDK. This is only used by Gradle.
# For customization when using a Version Control System, please read the
# header note.
sdk.dir={sdk_path}
"""
    
    android_path.parent.mkdir(parents=True, exist_ok=True)
    with open(android_path, 'w') as f:
        f.write(content)
    print("✅ Created Android local.properties")

def print_next_steps():
    """Print next steps for the user."""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("1. Edit .env file with your API keys")
    print("2. Update web_app/alstha_growth/local.properties with your Android SDK path")
    print("3. For Android development: Open web_app/alstha_growth/ in Android Studio")
    print("4. For Windows client: cd web_app/windows_client && python app.py")
    print("5. For web app: cd web_app/web_app && python app.py")
    print("\n📚 Documentation:")
    print("- README.md - Main project documentation")
    print("- readme/APPLICATION_STATUS.md - Current status")
    print("- readme/README_MODULAR.md - Architecture details")
    print("\n🔗 Repository: https://github.com/atm-2025/alstha_growth")
    print("=" * 60)

def main():
    """Main setup function."""
    print_banner()
    
    try:
        check_python_version()
        create_env_file()
        create_db_directory()
        install_dependencies()
        create_android_local_properties()
        print_next_steps()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 