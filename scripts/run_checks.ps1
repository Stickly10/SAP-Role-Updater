$ErrorActionPreference = "Stop"

python -m ruff check .
python -m pytest
python scripts\i18n_audit.py
.\security_checks.ps1
