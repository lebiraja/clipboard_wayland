#!/usr/bin/env python3
"""Launcher script for ClipNote."""

import sys
from pathlib import Path

# Add the project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from clipnote.main import main

if __name__ == "__main__":
    sys.exit(main())
