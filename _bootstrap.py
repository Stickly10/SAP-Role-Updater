"""Helpers to expose the src/ package from legacy root entrypoints."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_src_on_path():
    src_dir = Path(__file__).resolve().parent / "src"
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
