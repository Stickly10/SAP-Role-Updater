#!/usr/bin/env python3
"""Root entrypoint wrapper for the packaged application."""

from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from sap_role_updater.main import main

if __name__ == "__main__":
    main()
