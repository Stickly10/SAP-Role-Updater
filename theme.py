#!/usr/bin/env python3
"""Backward-compatible theme wrapper."""

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from sap_role_updater.gui.theme import *  # noqa: F403
