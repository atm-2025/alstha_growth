# 🚀 Quick Start Guide

Get Alstha Growth running in 5 minutes!

## ⚡ Quick Setup

### 1. Clone and Setup
```bash
git clone https://github.com/atm-2025/alstha_growth.git
cd alstha_growth
python setup.py
```

### 2. Configure API Keys
Edit the `.env` file and add your API keys:
```env
GROQ_API_KEY=your_actual_groq_key
COHERE_API_KEY=your_actual_cohere_key
# ... add other keys as needed
```

### 3. Run the Applications

#### Windows Client
```bash
cd web_app/windows_client
python app.py
```

#### Web App
```bash
cd web_app/web_app
python app.py
```

#### Android App
- Open `web_app/alstha_growth/` in Android Studio
- Build and run on device/emulator

## 🎯 What You Get

### Windows Client Features
- **AI Chat**: Talk to multiple AI models (Groq, Cohere, Gemini, etc.)
- **Voice Commands**: Use Windows speech-to-text (Win+H)
- **File Converter**: Convert between various file formats
- **Daily Logs**: Personal activity tracking
- **System Commands**: Execute commands remotely
- **Web Search**: Integrated search capabilities

### Android App Features
- **Camera**: Photo capture and processing
- **File Management**: Upload/download files
- **AI Chat**: Mobile AI conversation interface
- **Data Tables**: Visualize your data
- **Settings**: Configure the app

### Web App Features
- **File Upload**: Web-based file management
- **Converter**: Online file conversion tools
- **Dashboard**: Web interface for operations

## 🔑 Getting API Keys

### Free Options
1. **Groq**: [Console](https://console.groq.com/) - Free tier available
2. **Cohere**: [Platform](https://platform.cohere.ai/) - Free tier available
3. **Google Gemini**: [AI Studio](https://aistudio.google.com/) - Free tier available

### Paid Options
1. **OpenRouter**: [OpenRouter](https://openrouter.ai/) - Access to multiple models
2. **Cerebras**: [Cerebras](https://www.cerebras.ai/) - High-performance models
3. **Mistral**: [Mistral AI](https://mistral.ai/) - Advanced models

## 🐛 Troubleshooting

### Common Issues

1. **"Module not found" errors**
   ```bash
   pip install -r requirements.txt
   ```

2. **Android build errors**
   - Make sure Android Studio is installed
   - Update `local.properties` with correct SDK path
   - Sync Gradle dependencies

3. **API key errors**
   - Check that your API keys are correct in `.env`
   - Ensure you have credits/quota for the API service

4. **Database errors**
   - The database will be created automatically
   - Check that the `db/` directory exists

### Getting Help

- 📖 **Documentation**: Check `README.md` and files in `readme/` folder
- 🐛 **Issues**: Create an issue on GitHub
- 💬 **Community**: Check the project discussions

## 🎉 You're Ready!

Your Alstha Growth setup is complete! Start exploring the features:

1. **Try the AI chat** - Ask questions to different AI models
2. **Test voice commands** - Use Windows speech-to-text
3. **Convert some files** - Try the file converter
4. **Log your activities** - Use the daily logs feature
5. **Explore the mobile app** - Test the Android features

Happy coding! 🚀 