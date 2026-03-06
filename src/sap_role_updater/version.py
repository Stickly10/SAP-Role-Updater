#!/usr/bin/env python3
"""Single source of truth for semantic versioning."""

from __future__ import annotations

import re
from typing import Final

SEMVER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)

APP_VERSION = "2.0.1"


def parse_version(version: str) -> tuple[int, int, int]:
    """Validate and split a semantic version in ``major.minor.patch`` form."""
    match = SEMVER_PATTERN.fullmatch(version.strip())
    if not match:
        raise ValueError(
            f"Invalid version '{version}'. Expected semantic version x.y.z."
        )
    return tuple(int(part) for part in match.groups())


def bump_version(version: str, part: str) -> str:
    """Return the next semantic version for the requested part."""
    major, minor, patch = parse_version(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unsupported bump part '{part}'. Use major, minor, or patch.")


MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION = parse_version(APP_VERSION)

__all__ = [
    "APP_VERSION",
    "MAJOR_VERSION",
    "MINOR_VERSION",
    "PATCH_VERSION",
    "SEMVER_PATTERN",
    "bump_version",
    "parse_version",
]
