#!/usr/bin/env python3
"""Backward-compatible core wrapper."""

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from sap_role_updater.core.processor import *  # noqa: F403
