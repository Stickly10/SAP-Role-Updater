#!/usr/bin/env python3
"""Backward-compatible security/path wrapper."""

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from sap_role_updater.utils.path_safety import *  # noqa: F403
