"""Test harness specific configuration that doesn't mock cv2."""
import sys
from pathlib import Path

# Ensure the project is in the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))