#!/usr/bin/env python3
"""Backward-compatible error handler wrapper."""

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from sap_role_updater.utils.error_handler import *  # noqa: F403
