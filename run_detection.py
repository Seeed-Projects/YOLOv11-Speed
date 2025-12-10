#!/usr/bin/env python3
"""
Main entry point for the object detection and tracking application.
This script runs the object detection pipeline from the project root.
"""

import sys
import os

# Add the src directory to the Python path so imports work correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main function from object_detection
if __name__ == "__main__":
    # Add src to path and import main function
    from src.object_detection import main
    main()