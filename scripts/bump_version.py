#!/usr/bin/env python3
"""Bump SAP Role Updater version using semantic versioning."""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "src" / "sap_role_updater" / "version.py"
VERSION_INFO_FILE = ROOT / "version_info.txt"


def _load_version_api():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    bootstrap = importlib.import_module("_bootstrap")
    bootstrap.ensure_src_on_path()
    version_module = importlib.import_module("sap_role_updater.version")
    return (
        version_module.APP_VERSION,
        version_module.bump_version,
        version_module.parse_version,
    )


APP_VERSION, bump_version, parse_version = _load_version_api()


def _replace_once(text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Pattern not found or ambiguous: {pattern}")
    return updated


def _update_version_py(new_version: str) -> None:
    content = VERSION_FILE.read_text(encoding="utf-8")
    content = _replace_once(
        content,
        r'^APP_VERSION = ".*"$',
        f'APP_VERSION = "{new_version}"',
    )
    VERSION_FILE.write_text(content, encoding="utf-8")


def _update_version_info(new_version: str) -> None:
    major, minor, patch = parse_version(new_version)
    content = VERSION_INFO_FILE.read_text(encoding="utf-8")
    content = _replace_once(
        content,
        r"filevers=\(\d+, \d+, \d+, 0\)",
        f"filevers=({major}, {minor}, {patch}, 0)",
    )
    content = _replace_once(
        content,
        r"prodvers=\(\d+, \d+, \d+, 0\)",
        f"prodvers=({major}, {minor}, {patch}, 0)",
    )
    content = _replace_once(
        content,
        r"StringStruct\('FileVersion', '.*'\)",
        f"StringStruct('FileVersion', '{new_version}')",
    )
    content = _replace_once(
        content,
        r"StringStruct\('ProductVersion', '.*'\)",
        f"StringStruct('ProductVersion', '{new_version}')",
    )
    VERSION_INFO_FILE.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump semantic version (major.minor.patch) for SAP Role Updater."
    )
    parser.add_argument(
        "mode",
        choices=["major", "minor", "patch", "set"],
        help="Version bump mode.",
    )
    parser.add_argument(
        "value",
        nargs="?",
        help="Explicit semantic version when mode=set, for example 2.0.0",
    )
    args = parser.parse_args()

    current = APP_VERSION
    if args.mode == "set":
        if not args.value:
            raise SystemExit("Mode 'set' requires an explicit version like 2.0.0.")
        new_version = args.value.strip()
        parse_version(new_version)
    else:
        new_version = bump_version(current, args.mode)

    _update_version_py(new_version)
    _update_version_info(new_version)
    print(f"{current} -> {new_version}")
    print("Version files updated. Review README.md, CHANGELOG.md, and docs/releases/RELEASE_NOTES.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
