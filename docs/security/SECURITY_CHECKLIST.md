# Security Checklist

## Local Commands

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest
python scripts\i18n_audit.py
.\scripts\security_checks.ps1
```

`scripts/security_checks.ps1` audita las dependencias declaradas del proyecto y el código productivo. No usa el entorno completo como fuente de verdad.

## Review Points

- No accidental secrets in the repo:

```powershell
rg -n "password|token|apikey|secret" .
```

- Inputs rejected when paths are unsafe or files exceed limits
- Preview mode writes no files
- Processing writes outputs only inside the selected output folder
- Privacy mode redacts LOW/HIGH in the log
- GUI does not expose raw tracebacks by default
- Optional metadata file contains only local hashes and run metadata
