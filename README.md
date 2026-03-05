# SAP Role Updater

Actualiza exportes de roles SAP (AGR_1251 y AGR_1252) a partir de un archivo de reglas CSV/TSV.

Preserva lineas no objetivo, reutiliza COUNTER libres y genera log tabulado.

## Caracteristicas

- Soporta AGR_1251 y AGR_1252 en un solo run con un unico archivo de reglas.
- Accion soportada: `replace_list` (borra coincidencias y recrea con LOW/HIGH).
- Reutiliza COUNTER vacantes antes de incrementar.
- Log TSV (`*_MOD_LOG.tsv`) y archivo modificado (`*_MOD`).
- GUI en PySide6 o modo CLI.
- Errores estructurados (JSON por stderr).

## Requisitos

- Python 3.9+ (probado en 3.11).
- PySide6 para GUI.
- Windows para `.exe` (CLI funciona tambien en otros SO con Python).

## Estructura

- `main.py`: entrypoint CLI/GUI.
- `sap_role_updater_core.py`: logica core de parsing/procesamiento.
- `gui_pyside6.py`: interfaz grafica con QThread, validacion y resultados.
- `SAP-Role-Updater.py`: wrapper de compatibilidad.
- `error_handler.py`: errores estructurados.
- `BUILD.md`: instrucciones de compilacion con PyInstaller.

## Reglas CSV

Columnas (case-insensitive):

`ACTION, TABLE, MANDT, AGR_NAME, OBJECT, AUTH, FIELD, LOW, HIGH`

- AGR_1251: OBJECT/AUTH requeridos; FIELD = campo auth; LOW/HIGH (40).
- AGR_1252: OBJECT/AUTH vacios; FIELD = org field (ej. `$WERKS`); LOW/HIGH (40).
- Separador autodetectado (`;`, `,` o tab); lineas vacias se omiten.
- `replace_list` elimina coincidencias y crea una linea por par LOW/HIGH.

## Uso GUI

```bash
python main.py --gui
```

Tambien abre GUI automaticamente si ejecutas sin argumentos:

```bash
python main.py
```

## Uso CLI

```bash
python main.py --in EXPORT.txt --rules RULES.csv --outdir ./salida
```

## Notas tecnicas

- Log delimitado por `\t` para evitar conflictos con comas.
- COUNTER se libera al borrar y se asigna el menor disponible.
- Tablas no objetivo se preservan 1:1.
- Errores tipicos: `SYS-500`, `VAL-*` en JSON por stderr.

## Licencia

Pending (define tu licencia preferida, ej. MIT).
