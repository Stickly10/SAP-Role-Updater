#!/usr/bin/env python3
"""Simple JSON-based i18n manager."""

from __future__ import annotations

import json
import locale
from pathlib import Path

_LOCALES: dict[str, dict[str, str]] = {}
_CURRENT_LANG = "en"
_FALLBACK_LANG = "en"


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _default_locales_dir() -> Path:
    return Path(__file__).resolve().parent / "locales"


def load_locales(locales_dir: str | Path = "locales") -> dict[str, dict[str, str]]:
    global _LOCALES
    candidate = Path(locales_dir)
    if not candidate.is_absolute():
        candidate = _default_locales_dir() if locales_dir == "locales" else (Path.cwd() / candidate)
    loaded: dict[str, dict[str, str]] = {}
    if candidate.exists() and candidate.is_dir():
        for fp in sorted(candidate.glob("*.json")):
            try:
                loaded[fp.stem] = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
    _LOCALES = loaded
    return _LOCALES


def get_available_languages() -> list[str]:
    return sorted(_LOCALES.keys())


def detect_system_language(default: str = "es") -> str:
    loc = (locale.getdefaultlocale()[0] if locale.getdefaultlocale() else None) or ""
    normalized = loc.lower()
    if normalized.startswith("es"):
        return "es"
    if normalized.startswith("en"):
        return "en"
    return default


def set_language(lang_code: str | None) -> str:
    global _CURRENT_LANG
    if not _LOCALES:
        load_locales()
    lang = (lang_code or "").strip().lower()
    if lang in _LOCALES:
        _CURRENT_LANG = lang
    elif _FALLBACK_LANG in _LOCALES:
        _CURRENT_LANG = _FALLBACK_LANG
    elif _LOCALES:
        _CURRENT_LANG = next(iter(_LOCALES))
    else:
        _CURRENT_LANG = "en"
    return _CURRENT_LANG


def get_language() -> str:
    if not _LOCALES:
        load_locales()
    return _CURRENT_LANG


def t(message_key: str, **kwargs) -> str:
    if not _LOCALES:
        load_locales()
    lang = _CURRENT_LANG if _CURRENT_LANG in _LOCALES else _FALLBACK_LANG
    text = _LOCALES.get(lang, {}).get(message_key)
    if text is None:
        text = _LOCALES.get(_FALLBACK_LANG, {}).get(message_key, message_key)
    try:
        return str(text).format_map(_SafeDict(**kwargs))
    except Exception:  # noqa: BLE001
        return str(text)


load_locales()
if _CURRENT_LANG not in _LOCALES:
    set_language(detect_system_language())
