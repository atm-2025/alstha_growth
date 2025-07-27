#!/usr/bin/env python3
"""
Test script for command processing improvements
"""

import sys
import os

# Add the modules directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

# Fix for typing.Self compatibility in Python 3.10 - MUST BE FIRST
if sys.version_info < (3, 11):
    try:
        import typing_extensions
        if not hasattr(typing_extensions, 'Self'):
            from typing import TypeVar
            Self = TypeVar('Self', bound='object')
            setattr(typing_extensions, 'Self', Self)
    except ImportError:
        pass
    
    # Apply the fix to the main typing module as well
    import typing
    if not hasattr(typing, 'Self'):
        from typing import TypeVar
        Self = TypeVar('Self', bound='object')
        setattr(typing, 'Self', Self)

from modules.command_tab import AICommandProcessor

def test_command_processing():
    """Test the improved command processing"""
    print("🤖 Testing Jarvis Command Processing...")
    print("=" * 50)
    
    # Initialize the AI processor
    processor = AICommandProcessor()
    
    # Test cases that were failing before
    test_cases = [
        "Open the settings",
        "Open the control panel", 
        "Open notepad",
        "Open the file explorer",
        "Take a screenshot",
        "Show my IP address",
        "Check battery status",
        "Lock the computer",
        "Sleep the computer",
        # Complex multi-step commands
        "I want you to open the notepad and open the calculator and also open the notepad again and type hello world",
        "Open notepad and calculator",
        "Take screenshot and show IP address",
        "Open settings and control panel"
    ]
    
    print("Testing command recognition:")
    print("-" * 30)
    
    for test_input in test_cases:
        result = processor.process_natural_language(test_input)
        
        print(f"Input: '{test_input}'")
        print(f"Detected: '{result['command']}'")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Category: {result['category']}")
        
        # Show sub-commands for complex commands
        if result.get('sub_commands'):
            print(f"Sub-commands: {result['sub_commands']}")
        
        print("-" * 30)
    
    print("\n✅ Command processing test completed!")

if __name__ == "__main__":
    test_command_processing() 