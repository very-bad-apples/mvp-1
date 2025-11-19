"""
Test suite for the backend application.

This package contains all test files organized to mirror the source code structure.
"""

import sys
import os

# Add parent directory to path so tests can import from backend modules
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

