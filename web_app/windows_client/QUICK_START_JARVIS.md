# 🚀 Quick Start Guide - JARVIS AI Assistant

## ⚡ Get Started in 5 Minutes

### Step 1: Install Dependencies
```bash
# Run the automated setup script
python setup_jarvis.py
```

### Step 2: Test Installation
```bash
# Verify everything is working
python test_jarvis.py
```

### Step 3: Launch Jarvis
```bash
# Start the application
python app_simplified.py
```

### Step 4: Use Jarvis
1. Click on the **"Command"** tab
2. Click **"🎤 Start Listening"** for voice commands
3. Or type commands in the text field
4. Try saying: *"Take a screenshot"* or *"What's my IP address?"*

---

## 🎯 Quick Commands to Try

### Voice Commands
- *"Put computer to sleep"*
- *"Take a screenshot"*
- *"Open notepad"*
- *"Lock computer"*
- *"Check battery"*

### Text Commands
- *"I want to sleep my computer"*
- *"Can you show me the system information?"*
- *"Please open the calculator"*

### Quick Buttons
- **Sleep** - Put computer to sleep
- **Lock** - Lock workstation
- **Screenshot** - Take screenshot
- **IP Address** - Show network IP
- **Battery** - Check battery status

---

## 🔧 Troubleshooting

### If Setup Fails:
```bash
# Manual installation
pip install PySide6 torch transformers sentence-transformers speechrecognition pyttsx3 psutil
```

### If Voice Doesn't Work:
1. Check microphone permissions in Windows
2. Test microphone in Windows settings
3. Ensure PyAudio is installed

### If AI Models Don't Load:
1. Check internet connection
2. Ensure 5GB free disk space
3. Models download automatically on first use

### If Commands Don't Execute:
1. Check Windows permissions
2. Ensure applications exist on system
3. Run as administrator if needed

---

## 📱 Features Overview

### 🎤 Voice Control
- Real-time voice recognition
- Natural language processing
- Text-to-speech responses

### 🧠 AI Intelligence
- DistilBERT for command matching
- Microsoft Phi-2 for language understanding
- Confidence scoring

### ⚡ System Control
- Power management (sleep, shutdown, restart)
- Application launching
- System monitoring
- Volume and brightness control

### 📋 History & Logging
- Command history with timestamps
- Success/failure tracking
- Export capabilities

---

## 🎨 Interface Guide

### Left Panel
- **Voice Control**: Start/stop voice recognition
- **AI Processing**: Natural language input
- **Quick Commands**: Common actions

### Right Panel
- **Command History**: Past commands and results
- **Manual Commands**: Browse by category

### Status Bar
- Shows current status and feedback
- Color-coded messages (green=success, red=error)

---

## 🔒 Privacy & Security

- **Voice data** processed locally
- **No recordings** stored permanently
- **Command history** stored locally only
- **System permissions** required for commands

---

## 📞 Support

### Common Issues:
- **"Audio libraries not available"** → Run `pip install speechrecognition pyttsx3`
- **"AI libraries not available"** → Run `pip install torch transformers sentence-transformers`
- **"Voice recognition error"** → Check microphone and internet

### Getting Help:
1. Run `python test_jarvis.py` for diagnostics
2. Check the full README_JARVIS.md
3. Verify your Python version (3.8+ required)

---

## 🎉 You're Ready!

Your personal Jarvis AI assistant is now ready to help you control your computer with voice and natural language commands!

**Happy commanding! 🚀** 