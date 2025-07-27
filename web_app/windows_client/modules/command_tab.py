import os
import sys
import json
import time
import threading
import subprocess
import ctypes
import shutil
import psutil
import socket
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QProgressBar,
    QGroupBox, QCheckBox, QMessageBox, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap

# AI/ML imports
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: AI libraries not available. Install torch, transformers, sentence-transformers")

# Audio imports
try:
    import speech_recognition as sr
    import pyttsx3
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Warning: Audio libraries not available. Install speechrecognition, pyttsx3")

import gc

class ModelMemoryManager:
    """Manages model memory usage and optimization"""
    
    @staticmethod
    def get_memory_usage():
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
    
    @staticmethod
    def force_garbage_collection():
        """Force garbage collection to free memory"""
        gc.collect()
        print("🗑️ Garbage collection completed")
    
    @staticmethod
    def clear_torch_cache():
        """Clear PyTorch cache if available"""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("🎮 PyTorch CUDA cache cleared")
        except:
            pass
    
    @staticmethod
    def optimize_memory():
        """Perform comprehensive memory optimization"""
        ModelMemoryManager.force_garbage_collection()
        ModelMemoryManager.clear_torch_cache()
        
        memory_before = ModelMemoryManager.get_memory_usage()
        print(f"💾 Memory before optimization: {memory_before['rss']:.1f} MB")
        
        # Force garbage collection multiple times
        for i in range(3):
            gc.collect()
        
        memory_after = ModelMemoryManager.get_memory_usage()
        print(f"💾 Memory after optimization: {memory_after['rss']:.1f} MB")
        
        saved = memory_before['rss'] - memory_after['rss']
        if saved > 0:
            print(f"✅ Saved {saved:.1f} MB of memory")

class AICommandProcessor:
    """AI-powered command processor with lazy loading and rest mode"""
    
    def __init__(self, config=None):
        # Default configuration
        self.config = {
            'rest_timeout': 300,  # 5 minutes
            'auto_optimize': True,
            'lazy_loading': True,
            'memory_threshold': 2048,  # 2GB
            'enable_rest_mode': True
        }
        
        if config:
            self.config.update(config)
        
        self.commands = {
            "system_control": [
                "sleep", "shutdown", "restart", "hibernate", "lock", "unlock",
                "volume up", "volume down", "mute", "brightness up", "brightness down"
            ],
            "applications": [
                "open notepad", "open calculator", "open browser", "open file explorer",
                "open word", "open excel", "open powerpoint", "open paint",
                "open settings", "open control panel", "open task manager",
                "open device manager", "open system properties"
            ],
            "utilities": [
                "take screenshot", "show ip", "check battery", "check wifi",
                "show system info", "show disk space", "show memory usage",
                "show running processes", "show network status"
            ],
            "media": [
                "play music", "pause music", "next track", "previous track",
                "volume up", "volume down", "mute audio"
            ],
            "search": [
                "search google", "search youtube", "search files", "search documents"
            ]
        }
        
        # Enhanced command mapping with synonyms
        self.command_synonyms = {
            "open notepad": ["notepad", "text editor", "write", "note"],
            "open calculator": ["calculator", "calc", "math", "compute"],
            "open browser": ["browser", "internet", "web", "chrome", "edge", "firefox"],
            "open file explorer": ["file explorer", "explorer", "files", "folders", "documents"],
            "open word": ["word", "microsoft word", "document", "write document"],
            "open excel": ["excel", "microsoft excel", "spreadsheet", "table"],
            "open powerpoint": ["powerpoint", "presentation", "slides", "ppt"],
            "open paint": ["paint", "draw", "image editor", "drawing"],
            "open settings": ["settings", "windows settings", "system settings", "preferences"],
            "open control panel": ["control panel", "system control", "windows control"],
            "open task manager": ["task manager", "processes", "running programs"],
            "take screenshot": ["screenshot", "capture screen", "screen shot", "photo screen"],
            "show ip": ["ip address", "network ip", "internet address"],
            "check battery": ["battery", "power", "battery status", "power status"],
            "check wifi": ["wifi", "wireless", "network", "internet connection"],
            "lock": ["lock computer", "lock screen", "lock workstation"],
            "unlock": ["unlock computer", "unlock screen"],
            "sleep": ["sleep computer", "sleep mode", "suspend"],
            "shutdown": ["shutdown computer", "turn off", "power off"],
            "restart": ["restart computer", "reboot", "restart system"]
        }
        
        # Initialize with no models loaded
        self.command_embeddings = None
        self.sentence_model = None
        self.phi_model = None
        self.tokenizer = None
        self.models_loaded = False
        self.rest_mode = True  # Start in rest mode
        
        # Track usage for optimization
        self.usage_count = 0
        self.last_used = None
        self.rest_timer = None
        self.memory_manager = ModelMemoryManager()
        
        # Don't initialize models immediately - lazy loading
        print("🤖 AI Command Processor initialized (lazy loading enabled)")
    
    def _ensure_models_loaded(self):
        """Load models only when first needed"""
        if not self.models_loaded:
            print("🤖 Loading AI models (first time use)...")
            self._initialize_models()
            self.models_loaded = True
            self.rest_mode = False
            print("✅ AI models loaded and ready!")
    
    def _initialize_models(self):
        """Initialize DistilBERT and Microsoft Phi-2 models"""
        try:
            # Initialize DistilBERT for sentence similarity
            print("📥 Loading DistilBERT model...")
            self.sentence_model = SentenceTransformer('distilbert-base-nli-mean-tokens')
            
            # Pre-compute embeddings for all commands and synonyms
            all_commands = []
            for category, cmds in self.commands.items():
                all_commands.extend(cmds)
            
            # Add synonyms to the command list for better matching
            for main_cmd, synonyms in self.command_synonyms.items():
                all_commands.extend(synonyms)
            
            self.command_embeddings = self.sentence_model.encode(all_commands)
            
            # Initialize Microsoft Phi-2 for natural language understanding
            print("📥 Loading Microsoft Phi-2 model...")
            model_name = "microsoft/phi-2"
            try:
                # Try to load Phi-2 (you may need to download it separately)
                model_name = "microsoft/phi-2"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.phi_model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )
            except Exception as e:
                print(f"Could not load Phi-2 model: {e}")
                # Fallback to DialoGPT
                model_name = "microsoft/DialoGPT-medium"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.phi_model = AutoModelForCausalLM.from_pretrained(model_name)
            
            print("✅ AI models loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error initializing AI models: {e}")
            self.models_loaded = False
            self.rest_mode = True
    
    def _start_rest_timer(self):
        """Start timer to put models in rest mode"""
        if self.rest_timer:
            self.rest_timer.stop()
        
        self.rest_timer = QTimer()
        self.rest_timer.timeout.connect(self._enter_rest_mode)
        self.rest_timer.start(self.config['rest_timeout'] * 1000)  # Convert to milliseconds
    
    def _enter_rest_mode(self):
        """Enhanced rest mode with memory optimization"""
        if self.models_loaded and self.rest_mode == False:
            print("😴 Entering rest mode - unloading AI models...")
            
            # Clear model references
            if self.phi_model:
                del self.phi_model
                self.phi_model = None
            
            if self.tokenizer:
                del self.tokenizer
                self.tokenizer = None
            
            if self.sentence_model:
                del self.sentence_model
                self.sentence_model = None
            
            self.command_embeddings = None
            self.models_loaded = False
            self.rest_mode = True
            
            # Optimize memory
            if self.config['auto_optimize']:
                self.memory_manager.optimize_memory()
            
            print("✅ Models unloaded, memory optimized!")
    
    def _exit_rest_mode(self):
        """Load models when needed"""
        if self.rest_mode:
            print("🌅 Exiting rest mode - loading AI models...")
            self._ensure_models_loaded()
            self._start_rest_timer()  # Restart timer
    
    def get_memory_status(self):
        """Get current memory status"""
        memory = self.memory_manager.get_memory_usage()
        
        # Additional memory info
        try:
            import torch
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.memory_allocated() / 1024 / 1024  # MB
                gpu_memory_reserved = torch.cuda.memory_reserved() / 1024 / 1024  # MB
            else:
                gpu_memory = 0
                gpu_memory_reserved = 0
        except:
            gpu_memory = 0
            gpu_memory_reserved = 0
        
        return {
            'memory_usage': memory,
            'models_loaded': self.models_loaded,
            'rest_mode': self.rest_mode,
            'usage_count': self.usage_count,
            'last_used': self.last_used,
            'gpu_memory': gpu_memory,
            'gpu_memory_reserved': gpu_memory_reserved
        }
    
    def process_natural_language(self, user_input: str) -> Dict:
        """Process natural language input with lazy loading"""
        # Update usage tracking
        self.usage_count += 1
        self.last_used = datetime.now()
        
        # Load models if not already loaded
        self._ensure_models_loaded()
        
        if not self.models_loaded:
            return {
                "command": "unknown", 
                "confidence": 0.0, 
                "raw_input": user_input,
                "context": "Models not available",
                "category": "unknown"
            }
        
        try:
            # Check for complex multi-step commands
            complex_commands = self._parse_complex_command(user_input.lower())
            if complex_commands:
                return {
                    "command": "complex_multi_step",
                    "confidence": 0.9,
                    "raw_input": user_input,
                    "context": f"Multi-step: {', '.join(complex_commands)}",
                    "category": "complex",
                    "sub_commands": complex_commands
                }
            
            # First, try exact keyword matching for common patterns
            exact_match = self._exact_keyword_match(user_input.lower())
            if exact_match:
                return {
                    "command": exact_match,
                    "confidence": 0.95,
                    "raw_input": user_input,
                    "context": "Exact keyword match",
                    "category": self._get_command_category(exact_match)
                }
            
            # Get user input embedding
            user_embedding = self.sentence_model.encode([user_input])
            
            # Find most similar command
            similarities = cosine_similarity(user_embedding, self.command_embeddings)[0]
            best_match_idx = np.argmax(similarities)
            confidence = similarities[best_match_idx]
            
            # Get all commands (including synonyms)
            all_commands = []
            for category, cmds in self.commands.items():
                all_commands.extend(cmds)
            
            # Add synonyms
            for main_cmd, synonyms in self.command_synonyms.items():
                all_commands.extend(synonyms)
            
            best_match = all_commands[best_match_idx]
            
            # Map synonym back to main command
            main_command = self._map_synonym_to_main_command(best_match)
            
            # Use Phi-2 for additional context understanding
            context = self._get_phi_context(user_input)
            
            return {
                "command": main_command,
                "confidence": float(confidence),
                "raw_input": user_input,
                "context": context,
                "category": self._get_command_category(main_command)
            }
            
        except Exception as e:
            print(f"Error processing natural language: {e}")
            return {
                "command": "unknown", 
                "confidence": 0.0, 
                "raw_input": user_input,
                "context": "",
                "category": "unknown"
            }
    
    def _parse_complex_command(self, user_input: str) -> List[str]:
        """Parse complex multi-step commands"""
        commands = []
        
        # Common conjunctions and connectors
        connectors = ["and", "also", "then", "next", "after", "while", "while also"]
        
        # Check if input contains connectors (indicates complex command)
        has_connectors = any(connector in user_input.lower() for connector in connectors)
        
        # If no connectors found, don't treat as complex command
        if not has_connectors:
            print(f"🔍 No connectors found in: '{user_input}' - not a complex command")
            return None
        
        # Split by connectors
        parts = user_input
        for connector in connectors:
            parts = parts.replace(f" {connector} ", " | ")
        
        # Split by the separator
        command_parts = [part.strip() for part in parts.split("|")]
        
        print(f"🔍 Complex command parsing:")
        print(f"   Input: '{user_input}'")
        print(f"   Split parts: {command_parts}")
        
        # Process each part
        for part in command_parts:
            if not part:
                continue
                
            print(f"   Processing part: '{part}'")
            
            # Try to extract individual commands from each part
            extracted_commands = self._extract_commands_from_text(part)
            if extracted_commands:
                print(f"     Extracted commands: {extracted_commands}")
                # Only add commands that aren't already in the list
                for cmd in extracted_commands:
                    if cmd not in commands:
                        commands.append(cmd)
            else:
                # If no commands extracted, try to match the part directly
                direct_command = self._match_part_to_command(part)
                if direct_command and direct_command not in commands:
                    print(f"     Direct match: {direct_command}")
                    commands.append(direct_command)
                else:
                    print(f"     No command found for part: '{part}'")
        
        print(f"   Final commands: {commands}")
        return commands if commands else None
    
    def _match_part_to_command(self, part: str) -> str:
        """Match a part of text to a known command"""
        part_lower = part.lower().strip()
        
        # Direct command mappings
        command_mappings = {
            "calculator": "open calculator",
            "calc": "open calculator",
            "file explorer": "open file explorer",
            "explorer": "open file explorer",
            "files": "open file explorer",
            "folders": "open file explorer",
            "notepad": "open notepad",
            "text editor": "open notepad",
            "browser": "open browser",
            "internet": "open browser",
            "web": "open browser",
            "chrome": "open browser",
            "edge": "open browser",
            "word": "open word",
            "excel": "open excel",
            "powerpoint": "open powerpoint",
            "paint": "open paint",
            "settings": "open settings",
            "control panel": "open control panel",
            "task manager": "open task manager",
            "screenshot": "take screenshot",
            "capture screen": "take screenshot",
            "screen shot": "take screenshot",
            "ip": "show ip",
            "ip address": "show ip",
            "network": "show ip",
            "battery": "check battery",
            "power": "check battery",
            "wifi": "check wifi",
            "wireless": "check wifi",
            "lock": "lock",
            "sleep": "sleep",
            "shutdown": "shutdown",
            "restart": "restart"
        }
        
        # Check for exact matches first
        for key, command in command_mappings.items():
            if key in part_lower:
                return command
        
        # Check for partial matches
        for key, command in command_mappings.items():
            if any(word in part_lower for word in key.split()):
                return command
        
        return None
    
    def _extract_commands_from_text(self, text: str) -> List[str]:
        """Extract individual commands from text"""
        commands = []
        
        # Common command patterns (more specific patterns first)
        patterns = [
            (["open", "file", "explorer"], "open file explorer"),
            (["open", "notepad"], "open notepad"),
            (["open", "calculator"], "open calculator"),
            (["open", "calc"], "open calculator"),
            (["open", "browser"], "open browser"),
            (["open", "explorer"], "open file explorer"),
            (["open", "files"], "open file explorer"),
            (["open", "folders"], "open file explorer"),
            (["open", "settings"], "open settings"),
            (["open", "control", "panel"], "open control panel"),
            (["open", "task", "manager"], "open task manager"),
            (["take", "screenshot"], "take screenshot"),
            (["show", "ip"], "show ip"),
            (["check", "battery"], "check battery"),
            (["check", "wifi"], "check wifi"),
            (["lock", "computer"], "lock"),
            (["sleep", "computer"], "sleep"),
            (["shutdown", "computer"], "shutdown"),
            (["restart", "computer"], "restart"),
            (["type", "hello", "world"], "type_text"),
            (["write", "hello", "world"], "type_text"),
            (["input", "hello", "world"], "type_text")
        ]
        
        text_lower = text.lower()
        
        # Use pattern matching first (more precise)
        for keywords, command in patterns:
            if all(keyword in text_lower for keyword in keywords):
                if command not in commands:  # Avoid duplicates
                    commands.append(command)
        
        # Only use direct word matching if no patterns matched
        if not commands:
            direct_matches = {
                "calculator": "open calculator",
                "calc": "open calculator",
                "file explorer": "open file explorer",
                "explorer": "open file explorer",
                "files": "open file explorer",
                "folders": "open file explorer",
                "notepad": "open notepad",
                "browser": "open browser",
                "settings": "open settings",
                "screenshot": "take screenshot",
                "ip": "show ip",
                "battery": "check battery",
                "wifi": "check wifi",
                "lock": "lock",
                "sleep": "sleep",
                "shutdown": "shutdown",
                "restart": "restart"
            }
            
            for term, command in direct_matches.items():
                if term in text_lower and command not in commands:
                    commands.append(command)
        
        return commands
    
    def _exact_keyword_match(self, user_input: str) -> str:
        """Try to find exact keyword matches"""
        user_input_lower = user_input.lower().strip()
        
        # Exact single-word matches first (highest priority)
        exact_matches = {
            "ip": "show ip",
            "battery": "check battery",
            "wifi": "check wifi",
            "screenshot": "take screenshot",
            "lock": "lock",
            "sleep": "sleep",
            "shutdown": "shutdown",
            "restart": "restart",
            "notepad": "open notepad",
            "calculator": "open calculator",
            "calc": "open calculator",
            "browser": "open browser",
            "explorer": "open file explorer",
            "settings": "open settings",
            "word": "open word",
            "excel": "open excel",
            "powerpoint": "open powerpoint",
            "paint": "open paint",
            "volume": "volume up",
            "mute": "mute"
        }
        
        # Check for exact single-word matches
        for word, command in exact_matches.items():
            if user_input_lower == word:
                return command
        
        # Common patterns (for multi-word inputs)
        if any(word in user_input_lower for word in ["notepad", "text", "write", "note"]):
            return "open notepad"
        elif any(word in user_input_lower for word in ["calculator", "calc", "math"]):
            return "open calculator"
        elif any(word in user_input_lower for word in ["browser", "internet", "web", "chrome", "edge"]):
            return "open browser"
        elif any(word in user_input_lower for word in ["explorer", "files", "folders", "documents"]):
            return "open file explorer"
        elif any(word in user_input_lower for word in ["word", "document"]):
            return "open word"
        elif any(word in user_input_lower for word in ["excel", "spreadsheet", "table"]):
            return "open excel"
        elif any(word in user_input_lower for word in ["powerpoint", "presentation", "slides"]):
            return "open powerpoint"
        elif any(word in user_input_lower for word in ["paint", "draw", "drawing"]):
            return "open paint"
        elif any(word in user_input_lower for word in ["settings", "preferences"]):
            return "open settings"
        elif any(word in user_input_lower for word in ["control panel", "system control"]):
            return "open control panel"
        elif any(word in user_input_lower for word in ["task manager", "processes"]):
            return "open task manager"
        elif any(word in user_input_lower for word in ["screenshot", "capture", "screen shot"]):
            return "take screenshot"
        elif any(word in user_input_lower for word in ["ip", "network", "address"]):
            return "show ip"
        elif any(word in user_input_lower for word in ["battery", "power"]):
            return "check battery"
        elif any(word in user_input_lower for word in ["wifi", "wireless", "network"]):
            return "check wifi"
        elif any(word in user_input_lower for word in ["lock", "lock screen"]):
            return "lock"
        elif any(word in user_input_lower for word in ["sleep", "suspend"]):
            return "sleep"
        elif any(word in user_input_lower for word in ["shutdown", "turn off", "power off"]):
            return "shutdown"
        elif any(word in user_input_lower for word in ["restart", "reboot"]):
            return "restart"
        # Volume control patterns (add these before other patterns)
        elif any(word in user_input_lower for word in ["volume", "sound", "audio"]) and any(word in user_input_lower for word in ["up", "increase", "raise", "higher"]):
            return "volume up"
        elif any(word in user_input_lower for word in ["volume", "sound", "audio"]) and any(word in user_input_lower for word in ["down", "decrease", "lower", "reduce"]):
            return "volume down"
        elif any(word in user_input_lower for word in ["mute", "silence", "quiet"]):
            return "mute"
        elif any(word in user_input_lower for word in ["volume", "sound", "audio"]) and any(word in user_input_lower for word in ["%", "percent", "percentage"]):
            # Extract percentage and set volume
            import re
            percentage_match = re.search(r'(\d+)%', user_input_lower)
            if percentage_match:
                percentage = int(percentage_match.group(1))
                if percentage > 50:
                    return "volume up"
                else:
                    return "volume down"
            return "volume up"  # Default to volume up if percentage not found
        
        return None
    
    def _map_synonym_to_main_command(self, synonym: str) -> str:
        """Map a synonym back to its main command"""
        for main_cmd, synonyms in self.command_synonyms.items():
            if synonym in synonyms or synonym == main_cmd:
                return main_cmd
        return synonym
    
    def _get_phi_context(self, user_input: str) -> str:
        """Get additional context using Phi-2 model"""
        try:
            if self.tokenizer and self.phi_model:
                inputs = self.tokenizer.encode(user_input, return_tensors="pt")
                with torch.no_grad():
                    outputs = self.phi_model.generate(
                        inputs, 
                        max_length=50, 
                        num_return_sequences=1,
                        temperature=0.7,
                        do_sample=True
                    )
                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                return response
        except:
            pass
        return ""
    
    def _get_command_category(self, command: str) -> str:
        """Get the category of a command"""
        for category, cmds in self.commands.items():
            if command in cmds:
                return category
        return "unknown"

class VoiceRecognitionWorker(QThread):
    """Worker thread for voice recognition"""
    voice_detected = Signal(str)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.is_listening = False
        self.recognizer = None
        self.microphone = None
        
        if AUDIO_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
    
    def run(self):
        if not AUDIO_AVAILABLE:
            self.error.emit("Audio libraries not available")
            return
        
        self.is_listening = True
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                text = self.recognizer.recognize_google(audio)
                if text:
                    self.voice_detected.emit(text)
                    
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                self.error.emit(f"Voice recognition error: {str(e)}")
                break
    
    def stop(self):
        self.is_listening = False

class TextToSpeechWorker(QThread):
    """Worker thread for text-to-speech"""
    finished = Signal()
    
    def __init__(self, text: str):
        super().__init__()
        self.text = text
        self.engine = None
        
        if AUDIO_AVAILABLE:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.8)
    
    def run(self):
        if self.engine:
            self.engine.say(self.text)
            self.engine.runAndWait()
        self.finished.emit()

class CommandExecutor:
    """Execute system commands"""
    
    @staticmethod
    def execute_command(command: str, context: Dict = None) -> Tuple[bool, str]:
        """Execute a command and return success status and message"""
        try:
            if command == "sleep":
                return CommandExecutor._sleep_system()
            elif command == "shutdown":
                return CommandExecutor._shutdown_system()
            elif command == "restart":
                return CommandExecutor._restart_system()
            elif command == "hibernate":
                return CommandExecutor._hibernate_system()
            elif command == "lock":
                return CommandExecutor._lock_workstation()
            elif command == "unlock":
                return CommandExecutor._unlock_workstation()
            elif command == "take screenshot":
                return CommandExecutor._take_screenshot()
            elif command == "show ip":
                return CommandExecutor._show_ip_address()
            elif command == "check battery":
                return CommandExecutor._check_battery()
            elif command == "check wifi":
                return CommandExecutor._check_wifi()
            elif command == "show system info":
                return CommandExecutor._show_system_info()
            elif command == "show disk space":
                return CommandExecutor._show_disk_space()
            elif command == "show memory usage":
                return CommandExecutor._show_memory_usage()
            elif command == "show running processes":
                return CommandExecutor._show_running_processes()
            elif command == "show network status":
                return CommandExecutor._show_network_status()
            elif command == "type_text":
                return CommandExecutor._type_text("hello world")  # Default text
            elif command == "open settings":
                return CommandExecutor._open_settings()
            elif command.startswith("open "):
                return CommandExecutor._open_application(command[5:])
            elif command.startswith("volume "):
                return CommandExecutor._control_volume(command)
            elif command.startswith("brightness "):
                return CommandExecutor._control_brightness(command)
            else:
                return False, f"Unknown command: {command}"
                
        except Exception as e:
            return False, f"Error executing command: {str(e)}"
    
    @staticmethod
    def _sleep_system():
        try:
            subprocess.run(["powercfg", "/hibernate", "off"], shell=True)
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)
            return True, "System going to sleep..."
        except Exception as e:
            return False, f"Failed to sleep: {e}"
    
    @staticmethod
    def _shutdown_system():
        try:
            subprocess.run(["shutdown", "/s", "/t", "0"], shell=True)
            return True, "System shutting down..."
        except Exception as e:
            return False, f"Failed to shutdown: {e}"
    
    @staticmethod
    def _restart_system():
        try:
            subprocess.run(["shutdown", "/r", "/t", "0"], shell=True)
            return True, "System restarting..."
        except Exception as e:
            return False, f"Failed to restart: {e}"
    
    @staticmethod
    def _hibernate_system():
        try:
            subprocess.run(["shutdown", "/h"], shell=True)
            return True, "System hibernating..."
        except Exception as e:
            return False, f"Failed to hibernate: {e}"
    
    @staticmethod
    def _lock_workstation():
        try:
            ctypes.windll.user32.LockWorkStation()
            return True, "Workstation locked"
        except Exception as e:
            return False, f"Failed to lock: {e}"
    
    @staticmethod
    def _unlock_workstation():
        try:
            # This is a simplified implementation for unlocking
            # In a real scenario, you'd need a specific unlock mechanism
            # For example, using a key combination or a separate process
            # For now, we'll just return success
            return True, "Workstation unlocked (simulated)"
        except Exception as e:
            return False, f"Failed to unlock: {e}"
    
    @staticmethod
    def _take_screenshot():
        try:
            import pyautogui
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            return True, f"Screenshot saved as {filename}"
        except Exception as e:
            return False, f"Failed to take screenshot: {e}"
    
    @staticmethod
    def _show_ip_address():
        try:
            # Use the better IP detection function that's already available
            from utils import get_wifi_ip_address
            
            ip_address = get_wifi_ip_address()
            if ip_address:
                return True, f"🌐 Your IP Address: {ip_address}"
            else:
                # Fallback to basic method
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                return True, f"🌐 Your IP Address: {ip_address}"
        except Exception as e:
            return False, f"Failed to get IP: {e}"
    
    @staticmethod
    def _check_battery():
        try:
            battery = psutil.sensors_battery()
            if battery:
                percent = battery.percent
                plugged = battery.power_plugged
                status = "Plugged in" if plugged else "On battery"
                return True, f"Battery: {percent}% ({status})"
            else:
                return True, "Battery information not available"
        except Exception as e:
            return False, f"Failed to check battery: {e}"
    
    @staticmethod
    def _check_wifi():
        try:
            # Get WiFi information using Windows commands
            result = subprocess.run(["netsh", "wlan", "show", "interfaces"], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "SSID" in line and "BSSID" not in line:
                        ssid = line.split(':')[1].strip()
                        return True, f"Connected to: {ssid}"
            return True, "WiFi status checked"
        except Exception as e:
            return False, f"Failed to check WiFi: {e}"
    
    @staticmethod
    def _show_system_info():
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            return True, f"CPU: {cpu_percent}% | RAM: {memory.percent}% used"
        except Exception as e:
            return False, f"Failed to get system info: {e}"
    
    @staticmethod
    def _show_disk_space():
        try:
            disk = psutil.disk_usage('/')
            total_gb = disk.total / (1024**3)
            used_gb = disk.used / (1024**3)
            free_gb = disk.free / (1024**3)
            return True, f"Disk: {used_gb:.1f}GB used, {free_gb:.1f}GB free of {total_gb:.1f}GB"
        except Exception as e:
            return False, f"Failed to get disk space: {e}"
    
    @staticmethod
    def _show_memory_usage():
        try:
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024**3)
            used_gb = memory.used / (1024**3)
            return True, f"Memory: {used_gb:.1f}GB used of {total_gb:.1f}GB ({memory.percent}%)"
        except Exception as e:
            return False, f"Failed to get memory usage: {e}"
    
    @staticmethod
    def _show_running_processes():
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            return True, "\n".join([f"{p['pid']}: {p['name']} ({p['username']})" for p in processes])
        except Exception as e:
            return False, f"Failed to show running processes: {e}"
    
    @staticmethod
    def _show_network_status():
        try:
            # This is a simplified check, not a full network status
            # For a more comprehensive check, you'd use netsh or similar
            return True, "Network status checked (simplified)"
        except Exception as e:
            return False, f"Failed to check network status: {e}"
    
    @staticmethod
    def _type_text(text: str):
        try:
            import pyautogui
            pyautogui.write(text)
            return True, f"Typed: {text}"
        except Exception as e:
            return False, f"Failed to type text: {e}"
    
    @staticmethod
    def _open_application(app_name: str):
        app_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "browser": "msedge.exe",
            "file explorer": "explorer.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "paint": "mspaint.exe",
            "settings": "ms-settings:",  # Windows Settings URI
            "control panel": "control.exe",
            "task manager": "taskmgr.exe",
            "device manager": "devmgmt.msc",
            "system properties": "msinfo32.exe"
        }
        
        try:
            app_path = app_map.get(app_name.lower())
            if app_path:
                if app_path.startswith("ms-settings:"):
                    # Use start command for Windows Settings URI
                    subprocess.Popen(["start", app_path], shell=True)
                else:
                    subprocess.Popen([app_path])
                return True, f"Opening {app_name}..."
            else:
                return False, f"Unknown application: {app_name}"
        except Exception as e:
            return False, f"Failed to open {app_name}: {e}"
    
    @staticmethod
    def _open_settings():
        """Special method to open Windows Settings with multiple fallbacks"""
        try:
            # Method 1: Try Windows Settings URI
            subprocess.Popen(["start", "ms-settings:"], shell=True)
            return True, "Opening Windows Settings..."
        except Exception as e1:
            try:
                # Method 2: Try using the settings app directly
                subprocess.Popen(["start", "ms-settings:"], shell=True)
                return True, "Opening Windows Settings..."
            except Exception as e2:
                try:
                    # Method 3: Try using the control panel
                    subprocess.Popen(["control.exe"])
                    return True, "Opening Control Panel (Settings fallback)..."
                except Exception as e3:
                    return False, f"Failed to open Settings: {e1}, {e2}, {e3}"
    
    @staticmethod
    def _control_volume(command: str):
        try:
            # Check for percentage in command
            import re
            percentage_match = re.search(r'(\d+)%', command)
            
            if percentage_match:
                percentage = int(percentage_match.group(1))
                # Use a simpler PowerShell approach that should work reliably
                ps_script = f"""
                $obj = New-Object -ComObject Shell.Application
                $obj.NameSpace(17).Items() | Where-Object {{ $_.Name -eq "Control Panel" }} | ForEach-Object {{ $_.InvokeVerb("open") }}
                
                # Try using Windows Media Control
                try {{
                    $obj = New-Object -ComObject WMPlayer.OCX.7
                    $obj.settings.volume = {percentage}
                    Write-Output "SUCCESS:{percentage}"
                }} catch {{
                    Write-Output "FAILED:WMPlayer not available"
                }}
                """
                
                result = subprocess.run(["powershell", "-Command", ps_script], 
                                      capture_output=True, text=True, shell=True)
                
                if result.returncode == 0 and "SUCCESS:" in result.stdout:
                    return True, f"Volume set to {percentage}%"
                else:
                    # Use a more aggressive keyboard shortcut approach
                    # First, get current volume by pressing volume keys and counting
                    # Then calculate how many steps needed
                    
                    # For high percentages (like 99%), use many more steps
                    if percentage >= 90:
                        steps = 30  # Many steps for high volume
                    elif percentage >= 70:
                        steps = 20  # More steps for medium-high volume
                    elif percentage >= 50:
                        steps = 15  # Medium steps for medium volume
                    else:
                        steps = 10  # Fewer steps for low volume
                    
                    # Press volume up/down keys
                    if percentage > 50:
                        for i in range(steps):
                            subprocess.run(["powershell", "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"])
                        return True, f"Volume set to approximately {percentage}% (using {steps} steps)"
                    else:
                        for i in range(steps):
                            subprocess.run(["powershell", "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"])
                        return True, f"Volume set to approximately {percentage}% (using {steps} steps)"
            elif "up" in command:
                # Increase volume
                for i in range(5):
                    subprocess.run(["powershell", "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"])
                return True, "Volume increased"
            elif "down" in command:
                # Decrease volume
                for i in range(5):
                    subprocess.run(["powershell", "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"])
                return True, "Volume decreased"
            elif "mute" in command:
                # Toggle mute
                subprocess.run(["powershell", "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"])
                return True, "Volume muted/unmuted"
            else:
                return False, "Unknown volume command"
        except Exception as e:
            return False, f"Failed to control volume: {e}"
    
    @staticmethod
    def _control_brightness(command: str):
        try:
            # This is a simplified implementation
            # For actual brightness control, you'd need specific hardware APIs
            if "up" in command:
                return True, "Brightness increased (simulated)"
            elif "down" in command:
                return True, "Brightness decreased (simulated)"
            else:
                return False, "Unknown brightness command"
        except Exception as e:
            return False, f"Failed to control brightness: {e}"

class JarvisCommandTab(QWidget):
    """Enhanced command tab with lazy loading and memory monitoring"""
    
    def __init__(self):
        super().__init__()
        self.ai_processor = None  # Don't initialize immediately
        self.models_initialized = False
        self.voice_worker = None
        self.tts_worker = None
        self.is_listening = False
        self.command_history = []
        self.memory_timer = None
        
        self.init_ui()
        self.load_command_history()
        print("🤖 Command Tab initialized (AI models will load when tab is opened)")
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("🤖 JARVIS - AI Assistant")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #1565c0; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Voice and AI controls
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Command history and manual commands
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def _ensure_ai_processor(self):
        """Initialize AI processor only when needed"""
        if not self.models_initialized:
            print("🤖 Initializing AI processor (first time use)...")
            self.ai_processor = AICommandProcessor()
            self.models_initialized = True
            print("✅ AI processor ready!")
    
    def showEvent(self, event):
        """Called when tab becomes visible"""
        super().showEvent(event)
        # Initialize AI processor when tab is shown
        self._ensure_ai_processor()
        self.update_memory_status()
        
        # Start memory update timer
        if not self.memory_timer:
            self.memory_timer = QTimer()
            self.memory_timer.timeout.connect(self.update_memory_status)
            self.memory_timer.start(5000)  # Update every 5 seconds
    
    def hideEvent(self, event):
        """Called when tab becomes hidden"""
        super().hideEvent(event)
        # Optionally enter rest mode when tab is hidden
        if self.ai_processor:
            self.ai_processor._start_rest_timer()
    
    def update_memory_status(self):
        """Update memory status display"""
        if self.ai_processor:
            status = self.ai_processor.get_memory_status()
            memory = status['memory_usage']
            
            status_text = f"Memory: {memory['rss']:.1f} MB"
            if status['models_loaded']:
                status_text += " (Models Loaded)"
                if status['gpu_memory'] > 0:
                    status_text += f" | GPU: {status['gpu_memory']:.1f} MB"
            else:
                status_text += " (Rest Mode)"
            
            self.memory_label.setText(status_text)
    
    def optimize_memory(self):
        """Optimize memory usage"""
        if self.ai_processor:
            self.ai_processor.memory_manager.optimize_memory()
            self.update_memory_status()
            self.show_message("Memory optimized!", "success")
    
    def force_rest_mode(self):
        """Force models into rest mode"""
        if self.ai_processor:
            self.ai_processor._enter_rest_mode()
            self.update_memory_status()
            self.show_message("Models unloaded!", "info")
    
    def show_current_ip(self):
        """Show the current IP address in the dedicated display area"""
        try:
            from utils import get_wifi_ip_address
            
            ip_address = get_wifi_ip_address()
            if ip_address:
                self.ip_label.setText(f"🌐 Your IP Address:\n{ip_address}")
                self.ip_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 8px; background-color: #f0f8ff; border: 2px solid #4CAF50; border-radius: 5px;")
                self.show_message(f"🌐 IP Address: {ip_address}", "success")
            else:
                # Fallback to basic method
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                self.ip_label.setText(f"🌐 Your IP Address:\n{ip_address}")
                self.ip_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 8px; background-color: #f0f8ff; border: 2px solid #4CAF50; border-radius: 5px;")
                self.show_message(f"🌐 IP Address: {ip_address}", "success")
        except Exception as e:
            self.ip_label.setText(f"❌ Failed to get IP address:\n{str(e)}")
            self.ip_label.setStyleSheet("color: #f44336; font-weight: bold; padding: 8px; background-color: #ffebee; border: 2px solid #f44336; border-radius: 5px;")
            self.show_message(f"❌ Failed to get IP: {e}", "error")
    
    def _create_left_panel(self):
        """Create the left panel with voice controls and AI features"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Voice Control Section
        voice_group = QGroupBox("🎤 Voice Control")
        voice_layout = QVBoxLayout()
        
        # Voice input display
        self.voice_display = QTextEdit()
        self.voice_display.setMaximumHeight(100)
        self.voice_display.setPlaceholderText("Voice input will appear here...")
        self.voice_display.setReadOnly(True)
        voice_layout.addWidget(self.voice_display)
        
        # Voice control buttons
        voice_btn_layout = QHBoxLayout()
        
        self.voice_btn = QPushButton("🎤 Start Dictation (Win+H)")
        self.voice_btn.clicked.connect(self.trigger_windows_dictation)
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #45a049;
            }
        """)
        voice_btn_layout.addWidget(self.voice_btn)
        
        self.tts_btn = QPushButton("🔊 TTS Response")
        self.tts_btn.clicked.connect(self.toggle_tts)
        self.tts_btn.setCheckable(True)
        self.tts_btn.setChecked(True)
        voice_btn_layout.addWidget(self.tts_btn)
        
        voice_layout.addLayout(voice_btn_layout)
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # AI Processing Section
        ai_group = QGroupBox("🧠 AI Processing")
        ai_layout = QVBoxLayout()
        
        # Natural language input
        self.natural_input = QLineEdit()
        self.natural_input.setPlaceholderText("Type natural language commands...")
        self.natural_input.returnPressed.connect(self.process_natural_language)
        ai_layout.addWidget(self.natural_input)
        
        # AI confidence display
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setVisible(False)
        ai_layout.addWidget(self.confidence_bar)
        
        # AI response display
        self.ai_response = QTextEdit()
        self.ai_response.setMaximumHeight(120)
        self.ai_response.setPlaceholderText("AI processing results...")
        self.ai_response.setReadOnly(True)
        ai_layout.addWidget(self.ai_response)
        
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)
        
        # Quick Commands Section
        quick_group = QGroupBox("⚡ Quick Commands")
        quick_layout = QVBoxLayout()
        
        quick_commands = [
            "Sleep", "Lock", "Screenshot", "IP Address", 
            "Battery", "System Info", "Disk Space"
        ]
        
        for cmd in quick_commands:
            btn = QPushButton(cmd)
            btn.clicked.connect(lambda checked, c=cmd: self.execute_quick_command(c))
            btn.setStyleSheet("""
                QPushButton {
                    background: #2196F3;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background: #1976D2;
                }
            """)
            quick_layout.addWidget(btn)
        
        quick_group.setLayout(quick_layout)
        layout.addWidget(quick_group)
        
        # Memory Status Section
        memory_group = QGroupBox("💾 Memory Status")
        memory_layout = QVBoxLayout()
        
        self.memory_label = QLabel("Memory: Loading...")
        memory_layout.addWidget(self.memory_label)
        
        # Memory control buttons
        memory_btn_layout = QHBoxLayout()
        
        self.optimize_btn = QPushButton("🗑️ Optimize Memory")
        self.optimize_btn.clicked.connect(self.optimize_memory)
        memory_btn_layout.addWidget(self.optimize_btn)
        
        self.rest_btn = QPushButton("😴 Force Rest Mode")
        self.rest_btn.clicked.connect(self.force_rest_mode)
        memory_btn_layout.addWidget(self.rest_btn)
        
        memory_layout.addLayout(memory_btn_layout)
        memory_group.setLayout(memory_layout)
        layout.addWidget(memory_group)
        
        # IP Address Display Section
        ip_group = QGroupBox("🌐 Network Information")
        ip_layout = QVBoxLayout()
        
        # IP display label
        self.ip_label = QLabel("Click 'Show IP' to display your IP address")
        self.ip_label.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
        self.ip_label.setWordWrap(True)
        ip_layout.addWidget(self.ip_label)
        
        # Show IP button
        show_ip_btn = QPushButton("Show IP Address")
        show_ip_btn.clicked.connect(self.show_current_ip)
        ip_layout.addWidget(show_ip_btn)
        
        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)
        
        panel.setLayout(layout)
        return panel
    
    def _create_right_panel(self):
        """Create the right panel with command history and manual commands"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Command History Section
        history_group = QGroupBox("📋 Command History")
        history_layout = QVBoxLayout()
        
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(200)
        history_layout.addWidget(self.history_list)
        
        # Clear history button
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.clear_history)
        history_layout.addWidget(clear_btn)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        # Manual Commands Section
        manual_group = QGroupBox("🔧 Manual Commands")
        manual_layout = QVBoxLayout()
        
        # Command categories
        categories = ["System Control", "Applications", "Utilities", "Media", "Search"]
        self.category_combo = QComboBox()
        self.category_combo.addItems(categories)
        self.category_combo.currentTextChanged.connect(self.update_command_list)
        manual_layout.addWidget(QLabel("Category:"))
        manual_layout.addWidget(self.category_combo)
        
        # Command list
        self.command_list = QListWidget()
        self.command_list.itemDoubleClicked.connect(self.execute_list_command)
        manual_layout.addWidget(self.command_list)
        
        # Update initial command list
        self.update_command_list("System Control")
        
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)
        
        panel.setLayout(layout)
        return panel
    
    def trigger_windows_dictation(self):
        """Trigger Windows dictation (Win+H) for native STT"""
        import platform
        if platform.system() == 'Windows':
            try:
                import ctypes
                import time
                self.natural_input.setFocus()
                # Simulate Win+H
                user32 = ctypes.windll.user32
                user32.keybd_event(0x5B, 0, 0, 0)  # Win down
                user32.keybd_event(0x48, 0, 0, 0)  # H down
                user32.keybd_event(0x48, 0, 2, 0)  # H up
                user32.keybd_event(0x5B, 0, 2, 0)  # Win up
                self.status_label.setText("🎤 Windows dictation started (Win+H). Speak now...")
            except Exception as e:
                self.status_label.setText(f"❌ Could not trigger Windows dictation: {e}")
        else:
            self.status_label.setText("❌ Windows dictation is only available on Windows.")
    
    def toggle_voice_recognition(self):
        """Toggle voice recognition on/off"""
        if not AUDIO_AVAILABLE:
            self.show_message("Audio libraries not available", "error")
            return
        
        if not self.is_listening:
            self.start_voice_recognition()
        else:
            self.stop_voice_recognition()
    
    def start_voice_recognition(self):
        """Start voice recognition"""
        self.voice_worker = VoiceRecognitionWorker()
        self.voice_worker.voice_detected.connect(self.on_voice_detected)
        self.voice_worker.error.connect(self.on_voice_error)
        self.voice_worker.start()
        
        self.is_listening = True
        self.voice_btn.setText("🛑 Stop Listening")
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #d32f2f;
            }
        """)
        self.status_label.setText("Listening for voice commands...")
    
    def stop_voice_recognition(self):
        """Stop voice recognition"""
        if self.voice_worker:
            self.voice_worker.stop()
            self.voice_worker.wait()
            self.voice_worker = None
        
        self.is_listening = False
        self.voice_btn.setText("🎤 Start Listening")
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #45a049;
            }
        """)
        self.status_label.setText("Voice recognition stopped")
    
    def on_voice_detected(self, text: str):
        """Handle voice input"""
        self.voice_display.append(f"🎤 {text}")
        self.process_natural_language_input(text)
    
    def on_voice_error(self, error: str):
        """Handle voice recognition error"""
        self.show_message(f"Voice error: {error}", "error")
        self.stop_voice_recognition()
    
    def process_natural_language(self):
        """Process natural language input from text field"""
        text = self.natural_input.text().strip()
        if text:
            self.process_natural_language_input(text)
            self.natural_input.clear()
    
    def process_natural_language_input(self, text: str):
        """Process natural language input using AI"""
        # Ensure AI processor is loaded
        self._ensure_ai_processor()
        
        if not self.ai_processor:
            self.show_message("❌ AI processor not available", "error")
            return
        
        self.status_label.setText("Processing with AI...")
        
        # Process with AI
        result = self.ai_processor.process_natural_language(text)
        
        # Display AI response
        ai_text = f"Input: {result.get('raw_input', 'Unknown')}\n"
        ai_text += f"Detected Command: {result.get('command', 'unknown')}\n"
        ai_text += f"Confidence: {result.get('confidence', 0.0):.2f}\n"
        ai_text += f"Category: {result.get('category', 'unknown')}\n"
        if result.get('context'):
            ai_text += f"Context: {result['context']}\n"
        
        self.ai_response.setText(ai_text)
        
        # Show confidence bar
        confidence = result.get('confidence', 0.0)
        if confidence > 0.2:  # Lowered threshold for better recognition
            self.confidence_bar.setVisible(True)
            self.confidence_bar.setValue(int(confidence * 100))
            
            # Execute command if confidence is high enough
            if confidence > 0.4:  # Lowered threshold from 0.6 to 0.4
                self.execute_ai_command(result)
            else:
                self.show_message(f"Low confidence ({confidence:.2f}). Please try rephrasing.", "warning")
        else:
            self.confidence_bar.setVisible(False)
            self.show_message("Command not recognized. Please try again.", "warning")
        
        self.status_label.setText("AI processing complete")
    
    def execute_ai_command(self, result: Dict):
        """Execute command detected by AI"""
        command = result.get('command', 'unknown')
        
        # Handle complex multi-step commands
        if command == "complex_multi_step":
            sub_commands = result.get('sub_commands', [])
            if sub_commands:
                self.execute_complex_commands(sub_commands, result.get('raw_input', ''))
            else:
                self.show_message("❌ No sub-commands found in complex command", "error")
            return
        
        success, message = CommandExecutor.execute_command(command, result)
        
        if success:
            self.show_message(f"✅ {message}", "success")
            self.speak_response(f"Executed {command}")
        else:
            self.show_message(f"❌ {message}", "error")
            self.speak_response(f"Failed to execute {command}")
        
        # Add to history
        self.add_to_history(f"AI: {result.get('raw_input', 'Unknown')} → {command}", success)
    
    def execute_complex_commands(self, sub_commands: List[str], original_input: str):
        """Execute multiple commands sequentially"""
        self.show_message(f"🔄 Executing {len(sub_commands)} commands...", "info")
        
        success_count = 0
        failed_commands = []
        
        for i, sub_command in enumerate(sub_commands, 1):
            self.status_label.setText(f"Executing command {i}/{len(sub_commands)}: {sub_command}")
            
            # Add delay between commands for better user experience
            if i > 1:
                import time
                time.sleep(0.5)
            
            success, message = CommandExecutor.execute_command(sub_command)
            
            if success:
                success_count += 1
                self.show_message(f"✅ {i}/{len(sub_commands)}: {message}", "success")
            else:
                failed_commands.append(sub_command)
                self.show_message(f"❌ {i}/{len(sub_commands)}: {message}", "error")
        
        # Final summary
        if success_count == len(sub_commands):
            self.show_message(f"🎉 All {len(sub_commands)} commands executed successfully!", "success")
            self.speak_response(f"Executed all {len(sub_commands)} commands")
        else:
            self.show_message(f"⚠️ {success_count}/{len(sub_commands)} commands succeeded. Failed: {', '.join(failed_commands)}", "warning")
            self.speak_response(f"Executed {success_count} out of {len(sub_commands)} commands")
        
        # Add to history
        self.add_to_history(f"AI: {original_input} → {len(sub_commands)} commands ({success_count} success)", success_count == len(sub_commands))
        self.status_label.setText("Complex command execution complete")
    
    def execute_quick_command(self, command: str):
        """Execute a quick command"""
        # Handle special cases
        if command.lower() == "ip address":
            self.show_current_ip()
            return
        
        success, message = CommandExecutor.execute_command(command.lower())
        
        if success:
            self.show_message(f"✅ {message}", "success")
            self.speak_response(f"Executed {command}")
        else:
            self.show_message(f"❌ {message}", "error")
        
        self.add_to_history(f"Quick: {command}", success)
    
    def execute_list_command(self, item: QListWidgetItem):
        """Execute command from list"""
        command = item.text().lower()
        success, message = CommandExecutor.execute_command(command)
        
        if success:
            self.show_message(f"✅ {message}", "success")
            self.speak_response(f"Executed {command}")
        else:
            self.show_message(f"❌ {message}", "error")
        
        self.add_to_history(f"Manual: {command}", success)
    
    def update_command_list(self, category: str):
        """Update the command list based on selected category"""
        self.command_list.clear()
        
        category_map = {
            "System Control": ["sleep", "shutdown", "restart", "hibernate", "lock", "unlock"],
            "Applications": ["open notepad", "open calculator", "open browser", "open file explorer", "open settings", "open control panel", "open task manager", "open device manager", "open system properties"],
            "Utilities": ["take screenshot", "show ip", "check battery", "check wifi", "show system info", "show disk space", "show memory usage", "show running processes", "show network status"],
            "Media": ["volume up", "volume down", "mute", "play music", "pause music", "next track", "previous track"],
            "Search": ["search google", "search youtube", "search files", "search documents"]
        }
        
        commands = category_map.get(category, [])
        for cmd in commands:
            item = QListWidgetItem(cmd.title())
            self.command_list.addItem(item)
    
    def add_to_history(self, command: str, success: bool):
        """Add command to history"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = "✅" if success else "❌"
        history_entry = f"{timestamp} {status} {command}"
        
        self.command_history.append(history_entry)
        self.history_list.insertItem(0, history_entry)
        
        # Keep only last 50 entries
        if self.history_list.count() > 50:
            self.history_list.takeItem(self.history_list.count() - 1)
        
        self.save_command_history()
    
    def clear_history(self):
        """Clear command history"""
        self.history_list.clear()
        self.command_history.clear()
        self.save_command_history()
    
    def load_command_history(self):
        """Load command history from file"""
        try:
            history_file = os.path.join(os.path.dirname(__file__), "../jarvis_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.command_history = json.load(f)
                    for entry in self.command_history[-50:]:  # Load last 50
                        self.history_list.addItem(entry)
        except Exception as e:
            print(f"Error loading history: {e}")
    
    def save_command_history(self):
        """Save command history to file"""
        try:
            history_file = os.path.join(os.path.dirname(__file__), "../jarvis_history.json")
            with open(history_file, 'w') as f:
                json.dump(self.command_history, f)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def speak_response(self, text: str):
        """Speak response using text-to-speech"""
        if self.tts_btn.isChecked() and AUDIO_AVAILABLE:
            self.tts_worker = TextToSpeechWorker(text)
            self.tts_worker.start()
    
    def toggle_tts(self):
        """Toggle text-to-speech on/off"""
        if self.tts_btn.isChecked():
            self.show_message("Text-to-speech enabled", "info")
        else:
            self.show_message("Text-to-speech disabled", "info")
    
    def show_message(self, message: str, message_type: str = "info"):
        """Show a message to the user"""
        color_map = {
            "success": "#4CAF50",
            "error": "#f44336",
            "warning": "#ff9800",
            "info": "#2196F3"
        }
        
        color = color_map.get(message_type, "#2196F3")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; padding: 4px; font-size: 14px;")
        self.status_label.setText(message)
        
        # For important info like IP addresses, make it more prominent
        if "IP Address" in message or "🌐" in message:
            self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; padding: 8px; font-size: 16px; background-color: #f0f8ff; border: 2px solid {color}; border-radius: 5px;")
            # Keep IP address visible longer
            QTimer.singleShot(8000, lambda: self.status_label.setStyleSheet("color: #666; font-style: italic; padding: 4px; font-size: 12px;"))
        else:
            # Reset after 3 seconds for regular messages
            QTimer.singleShot(3000, lambda: self.status_label.setStyleSheet("color: #666; font-style: italic; padding: 4px; font-size: 12px;"))
    
    def closeEvent(self, event):
        """Clean up resources on close"""
        self.stop_voice_recognition()
        if self.tts_worker:
            self.tts_worker.quit()
            self.tts_worker.wait()
        event.accept()

# Backward compatibility - keep the old CommandTab class
class CommandTab(JarvisCommandTab):
    """Backward compatibility wrapper"""
    pass 