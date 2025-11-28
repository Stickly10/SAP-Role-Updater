# SAP Role Updater

Herramienta para actualizar exportes de roles SAP (tablas AGR_1251 y AGR_1252) a partir de un archivo de reglas CSV. Permite usar interfaz gráfica o CLI, preserva todas las líneas no objetivo y registra un log tabulado de los cambios realizados.

## Características
- Soporta AGR_1251 y AGR_1252 en un solo run y un único archivo de reglas.
- Acción soportada: `replace_list` (borra coincidencias y recrea con LOW/HIGH).
- Reutiliza números de COUNTER libres (rellena huecos antes de incrementar).
- Genera log en TSV (`*_MOD_LOG.csv`) y archivo modificado (`*_MOD.ext`).
- Interfaz gráfica moderna (tkinter + ttk) o uso por CLI.
- Manejo centralizado de errores con códigos/JSON (stdout/err).

## Requisitos
- Python 3.9+ (probado en 3.11).
- Tkinter (incluido en instalaciones estándar de Python para Windows).
- Windows (para el .exe propuesto) o cualquier SO con Python+tcl/tk para CLI/GUI.

## Estructura del proyecto
- `SAP-Role-Updater.py`: entrada principal (CLI/GUI), lógica de procesamiento.
- `gui_app.py`: interfaz gráfica, tema oscuro, progresos y accesos rápidos a carpeta/log.
- `error_handler.py`: errores estructurados y logging JSON.
- `RULES.csv`: ejemplo de reglas.

## Formato de reglas CSV
Columnas (insensibles a mayúsculas): `ACTION, TABLE, MANDT, AGR_NAME, OBJECT, AUTH, FIELD, LOW, HIGH`
- AGR_1251: OBJECT y AUTH requeridos; FIELD = campo de autorización; LOW/HIGH (40).  
- AGR_1252: OBJECT/AUTH vacíos; FIELD = org field (ej. `$WERKS`); LOW/HIGH (40).  
- Separador autodetectado (; , o tab). Líneas vacías se ignoran.  
- `replace_list` elimina coincidencias y crea una línea por par LOW/HIGH.

## Uso rápido (GUI)
```bash
python SAP-Role-Updater.py --gui
```
- Selecciona archivo base (export SAP), archivo de reglas y carpeta de salida.  
- La app generará `<base>_MOD.ext` y `<base>_MOD_LOG.csv` en la carpeta seleccionada.  
- Botones "Abrir carpeta salida" y "Abrir log" al terminar.

## Uso por CLI
```bash
python SAP-Role-Updater.py --in EXPORT.txt --rules RULES.csv --outdir ./salida
```
- `--in`: export fijo SAP (contiene AGR_1251/AGR_1252).  
- `--rules`: CSV de reglas.  
- `--outdir`: carpeta donde se escriben `<base>_MOD.ext` y `<base>_MOD_LOG.csv` (TSV).  

## Salida
- Archivo modificado: `<nombre_base>_MOD.ext` (mismo encoding que entrada).
- Log TSV: `<nombre_base>_MOD_LOG.csv` con columnas `action, before, after`.
- Resumen en consola/GUI: adds, deletes, replaces, warns.

## Construir un ejecutable (.exe) en Windows
1) Instala PyInstaller (sin red aqui, pero normalmente):  
   ```bash
   pip install pyinstaller
   ```
2) Empaqueta (sin consola):  
   ```bash
   pyinstaller --noconsole --onefile --name SAP-Role-Updater SAP-Role-Updater.py
   ```
3) El binario quedará en `dist/SAP-Role-Updater.exe`.  
   Incluye `gui_app.py` y `error_handler.py` automáticamente al ser importados.  
4) Firma opcional (requiere certificado):  
   ```bash
   "C:\Users\Andres Medina\OneDrive - Txool Evolucion\Documentos\Txool\Interno\Programas\SignTool-10.0.22621.6-x64\signtool.exe" sign ^
     /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 ^
     /f ruta\tu_certificado.pfx /p TU_PASSWORD ^
     dist\SAP-Role-Updater.exe
   ```
5) Metadatos opcionales: crea `version_info.txt` con CompanyName, ProductName, FileDescription, FileVersion, etc., y ejecuta:
   ```bash
   pyinstaller --noconsole --onefile --name SAP-Role-Updater --version-file version_info.txt SAP-Role-Updater.py
   ```
6) SmartScreen: puede advertir; verifica hash y origen oficial (este repo).  
   - SHA256 del .exe publicado: **(pendiente; agregar cuando se publique el release)**.

## Sobre el repositorio (sugerencia para GitHub “About”)
- Description: `Modifier para exportes SAP de roles (AGR_1251/1252) con GUI/CLI y reglas CSV.`
- Topics: `sap`, `roles`, `authorization`, `agr_1251`, `agr_1252`, `python`, `tkinter`, `cli`, `gui`

## Notas técnicas
- Log tabulado (delimitador `\t`) para evitar conflictos con comas en valores.
- COUNTER: se libera al borrar y se asigna el menor disponible antes de incrementar.
- Los campos no objetivo y tablas distintas de AGR_1251/1252 se preservan 1:1.
- Manejo de errores: `SYS-500`, `VAL-*` se emiten en stderr como JSON estructurado.

## Contribuir
1) Haz fork/branch.  
2) Cambios en código + pruebas con `--gui` y CLI.  
3) Crea PR con descripción de cambios y casos probados.

## Licencia
Pending (define tu licencia preferida, por ej. MIT).
