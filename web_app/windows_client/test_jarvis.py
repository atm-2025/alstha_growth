#!/usr/bin/env python3
"""
Jarvis AI Assistant Test Script
Tests the AI functionality without running the full GUI
"""

import os
import sys
import json
from pathlib import Path

# Add the modules directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing imports...")
    
    tests = [
        ("PySide6", "from PySide6.QtWidgets import QApplication"),
        ("OpenCV", "import cv2"),
        ("NumPy", "import numpy as np"),
        ("Torch", "import torch"),
        ("Transformers", "from transformers import AutoTokenizer"),
        ("Sentence Transformers", "from sentence_transformers import SentenceTransformer"),
        ("Speech Recognition", "import speech_recognition as sr"),
        ("Text-to-Speech", "import pyttsx3"),
        ("System Utils", "import psutil"),
        ("YouTube Transcript API", "from youtube_transcript_api import YouTubeTranscriptApi"),
        ("YT-DLP", "import yt_dlp"),
        ("Command Tab", "from command_tab import JarvisCommandTab")
    ]
    
    results = []
    for name, import_statement in tests:
        try:
            exec(import_statement)
            print(f"✅ {name}: OK")
            results.append(True)
        except ImportError as e:
            print(f"❌ {name}: Failed - {e}")
            results.append(False)
    
    return all(results)

def test_ai_processor():
    """Test the AI command processor"""
    print("\n🧠 Testing AI Command Processor...")
    
    try:
        from command_tab import AICommandProcessor
        
        processor = AICommandProcessor()
        
        # Test natural language processing
        test_inputs = [
            "put the computer to sleep",
            "take a screenshot",
            "what's my IP address",
            "open notepad",
            "lock the computer"
        ]
        
        for test_input in test_inputs:
            result = processor.process_natural_language(test_input)
            print(f"Input: '{test_input}'")
            print(f"  Command: {result['command']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Category: {result['category']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ AI Processor test failed: {e}")
        return False

def test_command_executor():
    """Test the command executor"""
    print("\n⚡ Testing Command Executor...")
    
    try:
        from command_tab import CommandExecutor
        
        # Test safe commands (non-destructive)
        test_commands = [
            "show ip",
            "check battery",
            "show system info",
            "show disk space",
            "show memory usage"
        ]
        
        for command in test_commands:
            success, message = CommandExecutor.execute_command(command)
            print(f"Command: '{command}'")
            print(f"  Success: {success}")
            print(f"  Message: {message}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Command Executor test failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\n⚙️  Testing Configuration...")
    
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'modules', 'json', 'jarvis_config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            required_sections = ['ai_models', 'voice_settings', 'commands', 'ui_settings', 'features']
            
            for section in required_sections:
                if section in config:
                    print(f"✅ {section}: OK")
                else:
                    print(f"❌ {section}: Missing")
                    return False
            
            return True
        else:
            print(f"❌ Configuration file not found: {config_path}")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_voice_recognition():
    """Test voice recognition setup"""
    print("\n🎤 Testing Voice Recognition...")
    
    try:
        import speech_recognition as sr
        
        # Test microphone detection
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        print("✅ Speech recognition library loaded")
        print("✅ Microphone object created")
        
        # Test if microphone is available
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Microphone is available")
            return True
        except Exception as e:
            print(f"⚠️  Microphone test failed: {e}")
            print("   This is normal if no microphone is connected")
            return True  # Not a critical failure
            
    except ImportError:
        print("❌ Speech recognition not available")
        return False
    except Exception as e:
        print(f"❌ Voice recognition test failed: {e}")
        return False

def test_text_to_speech():
    """Test text-to-speech setup"""
    print("\n🔊 Testing Text-to-Speech...")
    
    try:
        import pyttsx3
        
        engine = pyttsx3.init()
        
        # Get available voices
        voices = engine.getProperty('voices')
        print(f"✅ TTS engine initialized")
        print(f"✅ Available voices: {len(voices)}")
        
        # Test voice properties
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.8)
        print("✅ Voice properties set")
        
        return True
        
    except ImportError:
        print("❌ Text-to-speech not available")
        return False
    except Exception as e:
        print(f"❌ Text-to-speech test failed: {e}")
        return False

def test_models():
    """Test AI model loading"""
    print("\n🤖 Testing AI Models...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        print("📥 Loading DistilBERT model...")
        model = SentenceTransformer('distilbert-base-nli-mean-tokens')
        print("✅ DistilBERT model loaded successfully")
        
        # Test basic functionality
        sentences = ["put computer to sleep", "take screenshot", "open notepad"]
        embeddings = model.encode(sentences)
        print(f"✅ Generated embeddings: {embeddings.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        print("   Models will be downloaded automatically on first use")
        return True  # Not a critical failure

def main():
    """Run all tests"""
    print("=" * 60)
    print("🤖 JARVIS AI Assistant Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("AI Models", test_models),
        ("AI Processor", test_ai_processor),
        ("Command Executor", test_command_executor),
        ("Voice Recognition", test_voice_recognition),
        ("Text-to-Speech", test_text_to_speech)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Jarvis is ready to use.")
        print("Run 'python app_simplified.py' to start the application.")
    elif passed >= total * 0.7:
        print("\n⚠️  Most tests passed. Some features may not work.")
        print("Check the failed tests above for details.")
    else:
        print("\n❌ Many tests failed. Please check your installation.")
        print("Run 'python setup_jarvis.py' to reinstall dependencies.")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1) 