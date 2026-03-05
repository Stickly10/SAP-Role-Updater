#!/usr/bin/env python3
"""Security-focused helpers for safe file handling."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from error_handler import raise_error
from i18n import t

DEFAULT_LIMITS = {
    "base_size_mb": 300,
    "rules_size_mb": 50,
    "base_lines": 10_000_000,
    "rules_lines": 1_000_000,
}

WINDOWS_PATH_WARN_LEN = 240


def contains_control_chars(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value or "")


def is_unc_path(path_value: str | Path) -> bool:
    return str(path_value).startswith("\\\\")


def is_within_directory(base_dir: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(base_dir)
        return True
    except ValueError:
        return False


def _clean_input_path(path_value: str, label: str) -> str:
    txt = (path_value or "").strip()
    if not txt:
        raise_error(
            "VAL-PATH-EMPTY",
            "SEV2",
            t("sec.path_empty", label=label),
            err_type="Validation",
            origin="security_utils",
        )
    if contains_control_chars(txt):
        raise_error(
            "VAL-PATH-CTRL",
            "SEV2",
            t("sec.path_control", label=label),
            details=repr(txt),
            err_type="Validation",
            origin="security_utils",
        )
    return txt


def _check_path_length(path_obj: Path, label: str):
    if os.name == "nt" and len(str(path_obj)) > WINDOWS_PATH_WARN_LEN:
        raise_error(
            "VAL-PATH-LONG",
            "SEV2",
            t("sec.path_too_long", label=label, name=path_obj.name),
            details=str(path_obj),
            err_type="Validation",
            origin="security_utils",
        )


def resolve_regular_file(
    path_value: str,
    *,
    label: str,
    max_size_mb: int,
    max_lines: int,
) -> dict:
    raw = _clean_input_path(path_value, label)
    original = Path(raw)
    try:
        resolved = original.resolve(strict=True)
    except OSError as exc:
        raise_error(
            "VAL-PATH-RESOLVE",
            "SEV2",
            t("sec.path_resolve_failed", label=label, name=original.name or raw),
            details=str(exc),
            err_type="Validation",
            origin="security_utils",
        )
    if not resolved.is_file():
        raise_error(
            "VAL-PATH-NOFILE",
            "SEV2",
            t("sec.file_not_regular", label=label, name=resolved.name),
            err_type="Validation",
            origin="security_utils",
        )
    _check_path_length(resolved, label)
    size_bytes = resolved.stat().st_size
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        size_mb = round(size_bytes / (1024 * 1024), 2)
        raise_error(
            "VAL-FILE-SIZE",
            "SEV2",
            t("sec.file_too_large", label=label, size_mb=size_mb, max_mb=max_size_mb),
            err_type="Validation",
            origin="security_utils",
        )
    line_count = count_lines_with_limit(resolved, max_lines=max_lines, label=label)
    return {
        "path": resolved,
        "name": resolved.name,
        "size_bytes": size_bytes,
        "line_count": line_count,
        "is_unc": is_unc_path(raw),
    }


def resolve_output_dir(path_value: str, *, label: str = "output") -> dict:
    raw = _clean_input_path(path_value, label)
    original = Path(raw)
    try:
        resolved = original.resolve(strict=True)
    except OSError as exc:
        raise_error(
            "VAL-OUTDIR-RESOLVE",
            "SEV2",
            t("sec.outdir_resolve_failed", name=original.name or raw),
            details=str(exc),
            err_type="Validation",
            origin="security_utils",
        )
    if not resolved.is_dir():
        raise_error(
            "VAL-OUTDIR-NODIR",
            "SEV2",
            t("sec.outdir_not_directory", name=resolved.name),
            err_type="Validation",
            origin="security_utils",
        )
    if not os.access(resolved, os.W_OK):
        raise_error(
            "VAL-OUTDIR-NOWRITE",
            "SEV2",
            t("sec.outdir_not_writable", name=resolved.name),
            err_type="Validation",
            origin="security_utils",
        )
    _check_path_length(resolved, label)
    return {"path": resolved, "name": resolved.name, "is_unc": is_unc_path(raw)}


def safe_output_path(outdir: str | Path, filename: str, *, label: str) -> Path:
    if contains_control_chars(filename):
        raise_error(
            "VAL-FILENAME-CTRL",
            "SEV2",
            t("sec.filename_control", label=label),
            details=repr(filename),
            err_type="Validation",
            origin="security_utils",
        )
    base_dir = Path(outdir).resolve(strict=True)
    candidate = (base_dir / filename).resolve(strict=False)
    if not is_within_directory(base_dir, candidate):
        raise_error(
            "SEC-PATH-TRAVERSAL",
            "SEV2",
            t("sec.output_escape_blocked", label=label),
            details=str(candidate),
            err_type="Security",
            origin="security_utils",
        )
    _check_path_length(candidate, label)
    return candidate


def count_lines_with_limit(path_obj: Path, *, max_lines: int, label: str) -> int:
    count = 0
    last_byte = b""
    with path_obj.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            count += chunk.count(b"\n")
            last_byte = chunk[-1:]
            if count > max_lines:
                raise_error(
                    "VAL-FILE-LINES",
                    "SEV2",
                    t("sec.file_too_many_lines", label=label, max_lines=max_lines),
                    err_type="Validation",
                    origin="security_utils",
                )
    if path_obj.stat().st_size > 0 and last_byte != b"\n":
        count += 1
    if count > max_lines:
        raise_error(
            "VAL-FILE-LINES",
            "SEV2",
            t("sec.file_too_many_lines", label=label, max_lines=max_lines),
            err_type="Validation",
            origin="security_utils",
        )
    return count


def sha256_file(path_obj: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path_obj).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
