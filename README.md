# Alstha Growth - Multi-Platform AI Assistant

A comprehensive AI assistant application with web, Android, and Windows client components.

## 🚀 Features

### Windows Client
- **LLM Integration**: Support for multiple AI providers (Groq, Cohere, OpenRouter, Google Gemini, etc.)
- **Voice Commands**: Windows speech-to-text integration
- **File Conversion**: Multi-format file converter
- **Daily Logs**: Personal logging system
- **Remote Commands**: Server-client communication
- **Search Integration**: Web search capabilities

### Android App
- **Camera Integration**: Photo capture and processing
- **File Management**: Upload and download files
- **LLM Chat**: AI conversation interface
- **Daily Logs**: Mobile logging system
- **Table View**: Data visualization
- **Settings**: App configuration

### Web App
- **File Upload**: Web-based file management
- **Converter**: Online file conversion tools
- **Dashboard**: Web interface for file operations

## 📋 Prerequisites

- Python 3.10+
- Android Studio (for Android development)
- Windows 10/11 (for Windows client)
- Git

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/atm-2025/alstha_growth.git
cd alstha_growth
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```env
# API Keys (replace with your actual keys)
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
```

### 3. Install Dependencies

#### Windows Client
```bash
cd web_app/windows_client
pip install -r requirements.txt
```

#### Web App
```bash
cd web_app/web_app
pip install -r requirements.txt
```

#### Android App
Open `web_app/alstha_growth/` in Android Studio and sync Gradle dependencies.

### 4. Android Setup

1. Create `web_app/alstha_growth/local.properties`:
```properties
sdk.dir=C:\\Users\\YourUsername\\AppData\\Local\\Android\\Sdk
```

2. Build and run the Android app through Android Studio.

## 🚀 Running the Applications

### Windows Client
```bash
cd web_app/windows_client
python app.py
```

### Web App
```bash
cd web_app/web_app
python app.py
```

### Android App
- Open the project in Android Studio
- Build and run on device/emulator

## 📁 Project Structure

```
alstha_growth/
├── web_app/
│   ├── alstha_growth/          # Android app
│   ├── web_app/                # Web application
│   └── windows_client/         # Windows desktop app
├── db/                         # Database files
├── readme/                     # Documentation
└── .gitignore                  # Git ignore rules
```

## 🔧 Configuration

### API Keys Setup

1. **Groq**: Get API key from [Groq Console](https://console.groq.com/)
2. **Cohere**: Get API key from [Cohere Platform](https://platform.cohere.ai/)
3. **OpenRouter**: Get API key from [OpenRouter](https://openrouter.ai/)
4. **Google Gemini**: Get API key from [Google AI Studio](https://aistudio.google.com/)
5. **Cerebras**: Get API key from [Cerebras](https://www.cerebras.ai/)
6. **Mistral**: Get API key from [Mistral AI](https://mistral.ai/)

### Database Setup

The application uses SQLite for data storage. The database will be automatically created at `db/daily_logs.db`.

## 🎯 Usage

### Windows Client Features

1. **LLM Tab**: Chat with various AI models
2. **Converter Tab**: Convert files between formats
3. **Daily Logs**: Track personal activities
4. **Command Tab**: Execute system commands
5. **Search Tab**: Web search integration
6. **Upload Tab**: File upload to web server

### Android App Features

1. **Home**: Main dashboard
2. **Camera**: Photo capture
3. **Files**: File management
4. **LLM**: AI chat interface
5. **Table**: Data visualization
6. **Settings**: App configuration

## 🔒 Security

- API keys are stored as environment variables
- Sensitive files are excluded from version control
- Database files are stored locally
- OAuth tokens are managed securely

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Check the documentation in the `readme/` folder
- Review the application status in `readme/APPLICATION_STATUS.md`
- Create an issue on GitHub

## 🔄 Updates

The application is actively maintained with regular updates for:
- New AI model integrations
- Bug fixes and improvements
- Security updates
- Feature enhancements 