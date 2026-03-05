# SAP Role Updater v1.3.12

Herramienta de escritorio para preparar cambios masivos de roles SAP antes de cargarlos en PFCG.

La herramienta toma:

- un archivo base exportado desde `PFCG Mass Download`
- un `RULES.csv`

Y genera localmente:

- `<base>_MOD`
- `<base>_MOD_LOG.txt`
- opcional `<base>_MOD_META.json`

No cambia la logica funcional del algoritmo de reemplazo ni el formato final del MOD.

## Requisitos

- Windows 10/11
- Para uso funcional: no necesitas Python si usas `SAP Role Updater.exe`
- Para desarrollo: Python 3.11 y dependencias de `requirements.txt`

## Versionado

El proyecto usa versionado semantico `MAJOR.MINOR.PATCH`.

- `MAJOR`: cambios incompatibles o ruptura de flujo aprobado
- `MINOR`: funcionalidades nuevas compatibles
- `PATCH`: correcciones, hardening, docs, QA o mejoras sin romper compatibilidad

Para futuros releases no se debe editar la version “a mano” en varios archivos. Usa:

```powershell
python scripts\bump_version.py patch
python scripts\bump_version.py minor
python scripts\bump_version.py major
```

## Paso A Paso Para Consultor SAP

1. Exporta el rol o conjunto de roles desde `PFCG Mass Download`.
2. Guarda el archivo base. Puede venir sin extension o como `.sap`.
3. Prepara `RULES.csv` usando `templates/RULES_template.csv`.
4. Abre `SAP Role Updater.exe`.
5. Selecciona:
   - Base
   - Reglas
   - Carpeta de salida
6. Ejecuta **Validar**.
7. Revisa:
   - `Errores (SEV1/SEV2)`: bloquean **Procesar**
   - `Advertencias (SEV3)`: permiten continuar, pero deben revisarse
8. Ejecuta **Procesar**.
9. Revisa `_MOD_LOG.txt`.
10. Carga el `_MOD` en QA antes de usarlo en PRD.

## Estructura De RULES.csv

Columnas obligatorias:

- `ACTION`
- `TABLE`
- `MANDT`
- `AGR_NAME`
- `OBJECT`
- `AUTH`
- `FIELD`
- `LOW`
- `HIGH`

Reglas principales:

- `ACTION`: solo `replace_list`
- `TABLE`: solo `AGR_1251` o `AGR_1252`
- `MANDT`: exactamente 3 digitos
- `AGR_NAME`: sin espacios, maximo 30 caracteres
- `LOW` y `HIGH`: opcionales, maximo 40 caracteres por valor
- listas: usar `|` o `,`

Dependencias por tabla:

- `AGR_1251`: requiere `OBJECT`, `AUTH`, `FIELD`
- `AGR_1252`: requiere `FIELD` tipo `VARBL`, por ejemplo `$WERKS`

Ejemplo `AGR_1251`:

```csv
replace_list,AGR_1251,100,Z:FSBP_CRM_ZSALSPRO_EXT_1004,S_RFC,T-BD08132800,RFC_NAME,0*|A*,9*|Z*
```

Ejemplo `AGR_1252`:

```csv
replace_list,AGR_1252,100,Z:FSBP_CRM_ZSALSPRO_EXT_1004,,,$WERKS,0*|A*,9*|Z*
```

## Errores Comunes

- Faltan columnas obligatorias en el header
- `MANDT` no tiene 3 digitos
- `AGR_NAME` tiene espacios o supera 30 caracteres
- `FIELD` de `AGR_1252` no empieza por `$`
- algun valor de `LOW/HIGH` supera 40 caracteres
- la regla no encuentra lineas base coincidentes

## Interfaz

- **Idioma**: cambia entre `Espanol (ES)` y `English (EN)` sin reiniciar
- **Modo oscuro**: toggle animado, persistente
- **Ayuda**: boton `?` con quick start
- **Log privado**: redacta `LOW/HIGH` en log y muestra GUI
- **Meta SHA-256**: genera `_MOD_META.json` opcional para auditoria local

## Seguridad Y Buenas Practicas

- La herramienta no envia informacion a internet
- Si el log puede contener valores sensibles, activa `Log privado`
- Si necesitas trazabilidad local, activa `Meta SHA-256`
- Evita shares de red si no controlas permisos e integridad
- La aplicacion rechaza rutas inseguras, archivos demasiado grandes y salidas fuera de la carpeta elegida

Documentos relacionados:

- `HELP.md`
- `SECURITY.md`
- `PRIVACY.md`
- `USAGE.md`

## CLI

Proceso normal:

```bash
python main.py --in <base> --rules <rules> --outdir <outdir> --lang es
```

Preview:

```bash
python main.py --in <base> --rules <rules> --preview --lang en
```

Opciones de seguridad:

```bash
python main.py --in <base> --rules <rules> --outdir <outdir> --redact-log --write-meta --debug
```

## Desarrollo

Checks locales:

```powershell
python -m ruff check .
python -m pytest
python scripts\i18n_audit.py
.\security_checks.ps1
```

Build:

```powershell
.\scripts\build.ps1
```
