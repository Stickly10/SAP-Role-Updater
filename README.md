# SAP Role Updater

Actualiza exportes de roles SAP (AGR_1251 y AGR_1252) a partir de un archivo de reglas CSV. Preserva las líneas no objetivo, reutiliza COUNTER libres y genera log tabulado.

## Características
- Soporta AGR_1251 y AGR_1252 en un solo run con un único archivo de reglas.
- Acción: `replace_list` (borra coincidencias y recrea con LOW/HIGH).
- Reutiliza COUNTER vacantes antes de incrementar.
- Log TSV (`*_MOD_LOG.csv`) y archivo modificado (`*_MOD.ext`).
- GUI (tkinter/ttk) o CLI.
- Errores estructurados (JSON por stderr).

## Requisitos
- Python 3.9+ (probado en 3.11).
- Tkinter (incluido en Python para Windows).
- Windows (para el .exe) o cualquier SO con Python+tcl/tk para CLI/GUI.

## Estructura
- `SAP-Role-Updater.py`: entrada principal (CLI/GUI).
- `gui_app.py`: interfaz gráfica, tema oscuro, progreso, abrir carpeta/log.
- `error_handler.py`: errores estructurados.
- `RULES.csv`: ejemplo de reglas.

## Reglas CSV
Columnas (case-insensitive): `ACTION, TABLE, MANDT, AGR_NAME, OBJECT, AUTH, FIELD, LOW, HIGH`
- AGR_1251: OBJECT/AUTH requeridos; FIELD = campo auth; LOW/HIGH (40).
- AGR_1252: OBJECT/AUTH vacíos; FIELD = org field (ej. `$WERKS`); LOW/HIGH (40).
- Separador autodetectado (; , o tab); líneas vacías se omiten.
- `replace_list` elimina coincidencias y crea una línea por par LOW/HIGH.

## Uso GUI
```bash
python SAP-Role-Updater.py --gui
```
- Selecciona archivo base, reglas y carpeta de salida. Se generan `<base>_MOD.ext` y `<base>_MOD_LOG.csv` (TSV). Botones para abrir carpeta/log al terminar.

## Uso CLI
```bash
python SAP-Role-Updater.py --in EXPORT.txt --rules RULES.csv --outdir ./salida
```

## Binario y verificación
- SmartScreen puede advertir: verifica hash y origen oficial (este repo).
- SHA256 (SAP-Role-Updater.exe v1.3.6):
  `0DD53CFF21D5D485ECE4F6DC38F52E4857495D70C5C3E95E1621892DB05713AA`

## Sobre el repositorio (sugerido para About)
- Description: `Modifier para exportes SAP de roles (AGR_1251/1252) con GUI/CLI y reglas CSV.`
- Topics: `sap`, `roles`, `authorization`, `agr_1251`, `agr_1252`, `python`, `tkinter`, `cli`, `gui`

## Notas técnicas
- Log delimitado por `\t` para evitar conflictos con comas.
- COUNTER se libera al borrar y se asigna el menor disponible.
- Tablas no objetivo se preservan 1:1.
- Errores: `SYS-500`, `VAL-*` en JSON por stderr.

## Licencia
Pending (define tu licencia preferida, ej. MIT).
