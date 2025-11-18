"""
Pytest configuration for character persistence tests.

This file is automatically loaded by pytest and sets up the environment
for all test files in this directory.
"""

import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# This ensures all test files can import from backend modules

