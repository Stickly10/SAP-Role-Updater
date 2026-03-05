# SAP Role Updater v1.3.10

Herramienta de escritorio para preparar cambios masivos de roles SAP antes de cargarlos en PFCG.

Toma un archivo base exportado desde Mass Download y un `RULES.csv`, valida reglas y genera:

- Archivo modificado (`_MOD`)
- Log tabulado (`_MOD_LOG.txt`)
- Metadata local opcional (`_MOD_META.json`)

No altera tablas no objetivo y mantiene la logica de reemplazo existente.

## Requisitos

- Windows 10/11
- Para usuario final: no requiere Python si usas `SAP Role Updater.exe` del release
- Para desarrollo: Python 3.9+ y dependencias de `requirements.txt`

## Flujo Para Consultor SAP

1. Exporta roles desde PFCG (Mass Download).
2. Guarda el archivo base (puede venir sin extension o como `.sap`).
3. Prepara `RULES.csv` usando `templates/RULES_template.csv`.
4. Abre `SAP Role Updater.exe`.
5. Selecciona Base, Reglas y Carpeta de salida.
6. Pulsa **Validar**:
   - Errores `SEV1/SEV2`: bloquean **Procesar**
   - Advertencias `SEV3`: permiten continuar, pero deben revisarse
7. Pulsa **Procesar**.
8. Revisa:
   - `<base>_MOD`
   - `<base>_MOD_LOG.txt`
   - `<base>_MOD_META.json` si activaste metadata
9. Carga el `_MOD` en PFCG y prueba primero en QA.

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

Reglas clave:

- `ACTION`: solo `replace_list`
- `TABLE`: solo `AGR_1251` o `AGR_1252`
- `MANDT`: 3 digitos (ej. `100`)
- `AGR_NAME`: sin espacios, max 30
- `LOW/HIGH`: opcionales, max 40 por valor
- Listas: usar `|` o `,` (`0*|A*`, `9*|Z*`)

Dependiendo de `TABLE`:

- `AGR_1251`: `OBJECT` y `AUTH` obligatorios
- `AGR_1252`: `FIELD` tipo VARBL (ej. `$WERKS`), `OBJECT/AUTH` se ignoran

## Ejemplos

Ejemplo `AGR_1251`:

```csv
replace_list,AGR_1251,100,Z:FSBP_CRM_ZSALSPRO_EXT_1004,S_RFC,T-BD08132800,RFC_NAME,0*|A*,9*|Z*
```

Ejemplo `AGR_1252`:

```csv
replace_list,AGR_1252,100,Z:FSBP_CRM_ZSALSPRO_EXT_1004,,,$WERKS,0*|A*,9*|Z*
```

## Seguridad Y Buenas Practicas

- Valida y prueba en QA antes de cargar en PRD.
- Si el log puede contener valores sensibles, activa **Log privado** o usa `--redact-log`.
- No compartas `_MOD_LOG.txt` fuera del equipo si contiene LOW/HIGH sensibles.
- Si necesitas trazabilidad local, activa **Meta SHA-256** o usa `--write-meta`.
- Evita procesar desde rutas de red si no controlas permisos e integridad del share.
- La aplicacion rechaza archivos demasiado grandes, rutas inseguras y salidas fuera de la carpeta elegida.

Mas detalle tecnico en `SECURITY.md`.

## Compatibilidad CLI

CLI base:

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

## Notas De Log

El archivo log se mantiene en formato tabulado estable (`.txt`) para compatibilidad:

- Header: `action`, `before`, `after`
- Delimitador: tab (`\t`)

## Checks Locales

```powershell
.\security_checks.ps1
python smoke_test.py
```
