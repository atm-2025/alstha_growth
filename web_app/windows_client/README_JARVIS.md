# 🤖 JARVIS AI Assistant

## Overview

JARVIS (Just A Rather Very Intelligent System) is an AI-powered personal assistant integrated into your multimedia application. It uses **DistilBERT** for natural language understanding and **Microsoft Phi-2** for advanced language processing to provide intelligent voice and text command execution.

## 🚀 Features

### 🎤 Voice Commands
- **Real-time voice recognition** using Google Speech Recognition
- **Natural language processing** to understand spoken commands
- **Text-to-speech responses** for feedback and confirmation
- **Background voice monitoring** with noise cancellation

### 🧠 AI-Powered Intelligence
- **DistilBERT** for sentence similarity and command matching
- **Microsoft Phi-2** for advanced natural language understanding
- **Confidence scoring** to ensure accurate command execution
- **Context awareness** for better command interpretation

### ⚡ System Control
- **Power management**: Sleep, shutdown, restart, hibernate
- **Workstation control**: Lock/unlock, volume control, brightness
- **Application launching**: Notepad, Calculator, Browser, File Explorer
- **System monitoring**: Battery, IP address, disk space, memory usage

### 📋 Command History
- **Persistent command history** with timestamps
- **Success/failure tracking** for each command
- **Export capabilities** for command logs
- **Search and filter** through past commands

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Windows 10/11 (primary support)
- Microphone and speakers for voice features

### Quick Setup
1. **Run the setup script**:
   ```bash
   python setup_jarvis.py
   ```

2. **Or install manually**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application**:
   ```bash
   python app_simplified.py
   ```

### Manual Installation
If the setup script fails, install dependencies manually:

```bash
# Core dependencies
pip install PySide6 opencv-python numpy requests pyautogui pyperclip

# AI/ML dependencies
pip install torch transformers sentence-transformers accelerate bitsandbytes scikit-learn scipy

# Audio dependencies
pip install speechrecognition pyttsx3 pyaudio

# System utilities
pip install psutil pywin32 ctypes-windows-sdk python-dotenv colorama tqdm
```

## 🎯 Usage

### Voice Commands

1. **Start Voice Recognition**:
   - Click the "🎤 Start Listening" button
   - Speak your command clearly
   - The system will process and execute your command

2. **Example Voice Commands**:
   ```
   "Put the computer to sleep"
   "Take a screenshot"
   "What's my IP address?"
   "Open notepad"
   "Lock the computer"
   "Check battery status"
   ```

### Text Commands

1. **Natural Language Input**:
   - Type commands in the "Type natural language commands..." field
   - Press Enter to process
   - The AI will interpret and execute your command

2. **Example Text Commands**:
   ```
   "I want to sleep my computer"
   "Can you show me the system information?"
   "Please open the calculator"
   "Take a screenshot of my screen"
   ```

### Quick Commands

Use the quick command buttons for common actions:
- **Sleep**: Put computer to sleep
- **Lock**: Lock workstation
- **Screenshot**: Take screenshot
- **IP Address**: Show network IP
- **Battery**: Check battery status
- **System Info**: Show system information
- **Disk Space**: Show disk usage

### Manual Commands

Browse commands by category:
- **System Control**: Power management commands
- **Applications**: Launch applications
- **Utilities**: System utilities and monitoring
- **Media**: Audio/video controls
- **Search**: Search functionality

## 🧠 AI Models

### DistilBERT
- **Purpose**: Sentence similarity and command matching
- **Model**: `distilbert-base-nli-mean-tokens`
- **Function**: Converts natural language to command embeddings
- **Performance**: Fast inference with high accuracy

### Microsoft Phi-2
- **Purpose**: Advanced natural language understanding
- **Model**: `microsoft/phi-2`
- **Function**: Context analysis and command interpretation
- **Performance**: State-of-the-art language model

### Model Configuration
Models are configured in `modules/json/jarvis_config.json`:
```json
{
  "ai_models": {
    "sentence_transformer": "distilbert-base-nli-mean-tokens",
    "language_model": "microsoft/phi-2",
    "confidence_threshold": 0.6
  }
}
```

## 📁 File Structure

```
web_app/windows_client/
├── modules/
│   ├── command_tab.py          # Main Jarvis implementation
│   └── json/
│       └── jarvis_config.json  # AI model configuration
├── setup_jarvis.py             # Installation script
├── requirements.txt            # Dependencies
├── jarvis_history.json        # Command history (auto-generated)
└── README_JARVIS.md           # This file
```

## ⚙️ Configuration

### Voice Settings
```json
{
  "voice_settings": {
    "speech_rate": 150,
    "volume": 0.8,
    "timeout": 1,
    "phrase_time_limit": 5
  }
}
```

### UI Settings
```json
{
  "ui_settings": {
    "theme": "light",
    "accent_color": "#1565c0",
    "success_color": "#4CAF50",
    "error_color": "#f44336"
  }
}
```

## 🔧 Troubleshooting

### Common Issues

1. **Voice Recognition Not Working**:
   - Check microphone permissions
   - Ensure PyAudio is installed correctly
   - Test microphone in Windows settings

2. **AI Models Not Loading**:
   - Check internet connection for model download
   - Ensure sufficient disk space (models are ~2GB)
   - Verify torch and transformers installation

3. **Commands Not Executing**:
   - Check Windows permissions
   - Ensure applications exist on system
   - Verify command syntax

4. **Performance Issues**:
   - Close other applications to free memory
   - Use SSD for faster model loading
   - Consider using CPU-only models for lower memory usage

### Error Messages

- **"Audio libraries not available"**: Install speechrecognition and pyttsx3
- **"AI libraries not available"**: Install torch, transformers, sentence-transformers
- **"Voice recognition error"**: Check microphone and internet connection
- **"Model download failed"**: Check internet connection and disk space

## 🚀 Advanced Features

### Custom Commands
Add custom commands by modifying the `AICommandProcessor` class:

```python
self.commands["custom"] = [
    "your custom command",
    "another custom command"
]
```

### Model Customization
- **Fine-tune models** on your specific command set
- **Add domain-specific vocabulary** for better recognition
- **Custom confidence thresholds** for different command types

### Integration
- **Webhook support** for external API calls
- **Database integration** for persistent command storage
- **Plugin system** for extensible functionality

## 📊 Performance

### System Requirements
- **CPU**: Intel i5 or equivalent
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 5GB free space for models
- **GPU**: Optional, CUDA-compatible for acceleration

### Optimization Tips
- **Use SSD** for faster model loading
- **Close background applications** during voice recognition
- **Adjust confidence threshold** based on your needs
- **Use CPU-only models** if GPU memory is limited

## 🔒 Security

### Privacy
- **Voice data** is processed locally when possible
- **No voice recordings** are stored permanently
- **Command history** is stored locally only

### Permissions
- **Microphone access** required for voice commands
- **System permissions** needed for power management
- **Application launch** permissions for program execution

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Install development dependencies
3. Create a feature branch
4. Implement your changes
5. Test thoroughly
6. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Add type hints for functions
- Include docstrings for classes and methods
- Write unit tests for new features

## 📄 License

This project is part of the Alstha Growth multimedia application. See the main project license for details.

## 🙏 Acknowledgments

- **Hugging Face** for the transformers library
- **Microsoft** for the Phi-2 language model
- **Google** for speech recognition services
- **PySide6** for the Qt framework

---

**Happy commanding! 🚀** 