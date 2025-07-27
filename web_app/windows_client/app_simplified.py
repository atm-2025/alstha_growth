#!/usr/bin/env python3
"""
Simplified Main Application
This is the refactored version of the multimedia application with modular structure.
"""

import sys
import os

# Fix for typing.Self compatibility in Python 3.10 - MUST BE FIRST
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
    
    # Apply the fix to the main typing module as well
    import typing
    if not hasattr(typing, 'Self'):
        from typing import TypeVar
        Self = TypeVar('Self', bound='object')
        setattr(typing, 'Self', Self)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add the modules directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

# Import the main window from modules
from modules.main_window import MainWindow

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Multimedia Converter & Player")
    app.setApplicationVersion("2.0")
    
    # Create and show the main window
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    
    # Start the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 