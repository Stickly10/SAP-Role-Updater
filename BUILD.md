# Build Guide

## Runtime Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Development Dependencies

```bash
python -m pip install -r requirements-dev.txt
```

## Local Checks Before Build

```powershell
python -m ruff check .
python -m pytest
python scripts\i18n_audit.py
.\security_checks.ps1
```

## Clean Build

Recommended:

```powershell
.\scripts\build.ps1
```

Manual equivalent:

```powershell
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
pyinstaller --clean SAP-Role-Updater.spec
```

## If Qt Plugins Are Missing

```bash
pyinstaller --noconsole --onefile --clean --name "SAP Role Updater" --collect-all PySide6 main.py
```

## Build Notes

- The active code lives under `src/sap_role_updater/`.
- Root files are compatibility wrappers and valid PyInstaller entrypoints.
- Do not build from folders that contain real customer or productive SAP data.
- Prefer user-writable output folders. Avoid `Program Files`.
- Release assets expected after build:
  - `dist/SAP Role Updater.exe`
  - `templates/RULES_template.csv`
  - `RELEASE_NOTES.md`
