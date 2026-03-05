#!/usr/bin/env python3
"""Backward-compatible i18n wrapper."""

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from sap_role_updater.gui.i18n import *  # noqa: F403
