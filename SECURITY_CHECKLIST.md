# Security Checklist

## Quick Run

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pip-audit bandit
.\security_checks.ps1
```

## Manual Commands

```powershell
python -m ruff check .
pip-audit
bandit -r . -x .venv,build,dist
python smoke_test.py
```

## What To Review

- No accidental secrets in the repo (`rg -n "password|token|apikey|secret" .`)
- Output files generated only inside the selected output folder
- Large base/rules files rejected with clear SEV2 errors
- GUI and CLI both handle errors without exposing full tracebacks by default
- Privacy mode enabled when logs may contain sensitive LOW/HIGH values
