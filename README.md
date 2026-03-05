# SAP Role Updater v1.3.9

Herramienta de escritorio para preparar cambios masivos de roles SAP antes de cargarlos en PFCG.

Toma un archivo base exportado desde Mass Download y un `RULES.csv`, valida reglas y genera:

- Archivo modificado (`_MOD`)
- Log tabulado (`_MOD_LOG.tsv`)

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
5. Selecciona:
   - Base
   - Reglas
   - Carpeta de salida
6. Pulsa **Validar**:
   - Errores (SEV1/SEV2): bloquean **Procesar**
   - Advertencias (SEV3): permiten continuar, pero deben revisarse
7. Pulsa **Procesar y generar _MOD**.
8. Revisa:
   - `<base>_MOD`
   - `<base>_MOD_LOG.tsv`
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

## Ejemplos Reales

Ejemplo AGR_1251:

```csv
replace_list,AGR_1251,100,Z:FSBP_CRM_ZSALSPRO_EXT_1004,S_RFC,T-BD08132800,RFC_NAME,0*|A*,9*|Z*
```

Ejemplo AGR_1252:

```csv
replace_list,AGR_1252,100,Z:FSBP_CRM_ZSALSPRO_EXT_1004,,,$WERKS,0*|A*,9*|Z*
```

## Errores Comunes

- Faltan columnas en header: revisa encabezados obligatorios.
- `MANDT` invalido: debe ser exactamente 3 digitos.
- VARBL sin `$` en `AGR_1252`: ejemplo correcto `$WERKS`.
- Valores `LOW/HIGH` mayores a 40 caracteres.
- Rol/campo no existe en base: aparece advertencia de no coincidencia.

## Interfaz

- **Idioma**: selector en el header (`Español` / `English`), cambio en caliente.
- **Tema**: toggle **Modo oscuro** en header, cambio en caliente y persistente.
- **Tabs de resultado**:
  - Resumen
  - Advertencias (con filtro)
  - Cambios (muestra de cambios)

## Compatibilidad CLI

La CLI se mantiene:

```bash
python main.py --in <base> --rules <rules> --outdir <outdir> --lang es
```

Modo preview:

```bash
python main.py --in <base> --rules <rules> --preview --lang en
```

## Notas De Log

El archivo log se mantiene en formato tabulado estable (`.tsv`) para compatibilidad:

- Header: `action`, `before`, `after`
- Delimitador: tab (`\t`)

