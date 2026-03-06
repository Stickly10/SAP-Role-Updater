#!/usr/bin/env python3
"""Generate a multi-resolution Windows ICO from the branding PNG."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ICON_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    branding_dir = repo_root / "assets" / "branding"
    png_path = branding_dir / "SAP Role Updater Logo.png"
    ico_path = branding_dir / "SAP-Role-Updater-Logo.ico"
    temp_path = branding_dir / "SAP-Role-Updater-Logo.ico.tmp"

    image = Image.open(png_path).convert("RGBA")
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(temp_path, format="ICO", sizes=ICON_SIZES)
    temp_path.replace(ico_path)


if __name__ == "__main__":
    main()
