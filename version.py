#!/usr/bin/env python3
"""Backward-compatible version wrapper."""

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from sap_role_updater.version import *  # noqa: F403
