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

Recomendado:

```powershell
.\scripts\build.ps1 -Package
```

Este script hace lo siguiente:

- limpia `build/`
- mantiene archivos ajenos existentes en `dist/`
- instala dependencias runtime
- regenera `templates/RULES_template.xlsx`
- compila con `SAP-Role-Updater.spec`
- genera `dist/SAP Role Updater v2.0.0.zip`

## Manual Equivalent

```powershell
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (-not (Test-Path dist)) { New-Item -ItemType Directory -Force dist | Out-Null }
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts\generate_rules_template.py
pyinstaller --clean SAP-Role-Updater.spec
.\scripts\package_release.ps1 -Version 2.0.0
```

## Spec Highlights

El spec incorpora:

- icono del ejecutable: `SAP-Role-Updater-Logo.ico`
- icono en runtime dentro del bundle
- `locales/*.json`
- `templates/RULES_template.xlsx`

Fallback manual si necesitas compilar sin el spec:

```powershell
pyinstaller --noconsole --onefile --clean --name "SAP Role Updater" --icon "SAP-Role-Updater-Logo.ico" --add-data "SAP-Role-Updater-Logo.ico;." --add-data "templates\RULES_template.xlsx;templates" --collect-all PySide6 main.py
```

## Build Notes

- El código activo vive en `src/sap_role_updater/`.
- Los archivos raíz siguen como wrappers de compatibilidad.
- La documentación secundaria vive en `docs/`.
- `dist/` es carpeta de trabajo local y no se versiona.
- El release público recomendado es el ZIP, no el `.exe` suelto.
