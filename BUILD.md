# Build Windows EXE (PySide6)

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

## 2) Build one-file executable

```bash
pyinstaller --noconsole --onefile --name "SAP Role Updater" main.py
```

## 3) If Qt plugins are missing at runtime

```bash
pyinstaller --noconsole --onefile --name "SAP Role Updater" --collect-all PySide6 main.py
```

## Basic troubleshooting

- Ensure you are building with the same Python where `PySide6` is installed.
- Delete previous `build/` and `dist/` outputs before rebuilding if artifacts look stale.
- If SmartScreen warns, verify hash and source before execution.
- If GUI does not start but CLI works, rebuild with `--collect-all PySide6`.
