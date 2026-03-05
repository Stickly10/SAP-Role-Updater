# Build Windows EXE (PySide6)

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

## 2) Clean previous artifacts

```bash
# PowerShell
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
```

## 3) Build one-file executable (clean)

```bash
pyinstaller --noconsole --onefile --clean --name "SAP Role Updater" main.py
```

## 4) If Qt plugins are missing at runtime

```bash
pyinstaller --noconsole --onefile --clean --name "SAP Role Updater" --collect-all PySide6 main.py
```

## Basic troubleshooting

- Ensure you are building with the same Python where `PySide6` is installed.
- Delete previous `build/` and `dist/` outputs before rebuilding if artifacts look stale.
- If SmartScreen warns, verify hash and source before execution.
- If GUI does not start but CLI works, rebuild with `--collect-all PySide6`.
