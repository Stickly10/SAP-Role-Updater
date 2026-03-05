# Build Windows EXE (PySide6)

## 1) Upgrade pip and install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2) Optional dependency audit

```bash
python -m pip install pip-audit
pip-audit
```

## 3) Clean previous artifacts

```powershell
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
```

## 4) Reproducible clean build

```bash
pyinstaller --clean SAP-Role-Updater.spec
```

## 5) If Qt plugins are missing at runtime

```bash
pyinstaller --noconsole --onefile --clean --name "SAP Role Updater" --collect-all PySide6 main.py
```

## 6) Optional local security checks

```powershell
.\security_checks.ps1
```

## Notes

- Build with the same Python interpreter where `PySide6` is installed.
- Do not package secrets, tokens, personal paths, or temporary outputs.
- The EXE writes outputs only to the folder selected by the user.
- Prefer a user-writable folder. Avoid `Program Files` and other privileged locations.
- `SAP-Role-Updater.spec` includes `locales/*.json` and `templates/RULES_template.csv`.
