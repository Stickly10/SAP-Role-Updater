"""Central configuration for runtime defaults and resources."""

from __future__ import annotations

import sys
from pathlib import Path

APP_SETTINGS_ORG = "Txool"
APP_SETTINGS_NAME = "SAPRoleUpdater"
DISPLAY_NAME = "SAP Role Updater"

DEFAULT_LIMITS = {
    "base_size_mb": 300,
    "rules_size_mb": 50,
    "base_lines": 10_000_000,
    "rules_lines": 1_000_000,
}


def project_root() -> Path:
    """Return the repository root in dev mode or bundle root in frozen mode."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[3]


def resource_path(*parts: str) -> Path:
    """Resolve a project resource path relative to the runtime root."""
    return project_root().joinpath(*parts)
