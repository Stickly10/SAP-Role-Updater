# SAP Role Updater v2.0.0

Herramienta de escritorio para preparar cambios masivos de roles SAP antes de cargarlos en PFCG.

La aplicación toma:

- un archivo base exportado desde `PFCG Mass Download`
- un archivo `RULES.xlsx` con hoja `RULES`

Y genera localmente:

- `<base>_MOD`
- `<base>_MOD_LOG.csv`
- opcional `<base>_MOD_META.json`

El algoritmo funcional del MOD no cambia. Las mejoras de esta versión están en validación, performance, cobertura, diff visual, UX y empaquetado.

## Qué Cambió En La v2.0.0

- `RULES.csv` se reemplazó por `RULES.xlsx` de forma exclusiva.
- El log vuelve a ser `CSV` real con separador `;` para compatibilidad con Excel regional.
- Se agregó indexado del archivo base para acelerar búsquedas por regla.
- Se agregó reporte de cobertura por regla y visor diff visual en la GUI.
- El release se distribuye en `ZIP` para preservar el nombre interno `SAP Role Updater.exe`.

## Requisitos

- Windows 10/11
- Para uso funcional: no necesitas Python si usas el release empaquetado
- Para desarrollo: Python 3.11 y dependencias de `requirements.txt`

## Versionado

El proyecto usa versionado semántico `MAJOR.MINOR.PATCH`.

- `MAJOR`: cambios incompatibles con el flujo anterior
- `MINOR`: funcionalidades nuevas compatibles
- `PATCH`: correcciones y mejoras sin romper compatibilidad

La v2.0.0 es `MAJOR` porque elimina soporte para reglas en CSV y exige `RULES.xlsx`.

## Flujo Paso A Paso Para Consultor SAP

1. Exporta el rol o conjunto de roles desde `PFCG Mass Download`.
2. Guarda el archivo base. Puede venir sin extensión o como `.sap`.
3. Abre `templates/RULES_template.xlsx`.
4. Llena la hoja `RULES` con tus reglas.
5. Abre `SAP Role Updater.exe`.
6. Selecciona:
   - Base
   - Reglas (`RULES.xlsx`)
   - Carpeta de salida
7. Ejecuta **Validar**.
8. Revisa:
   - **Advertencias**: mensajes estructurados
   - **Cobertura**: qué regla aplicó, qué no encontró base y qué quedó bloqueado por error
   - **Cambios**: muestra de cambios con visor diff BEFORE/AFTER
9. Si no hay errores `SEV1/SEV2`, ejecuta **Procesar**.
10. Revisa `_MOD_LOG.csv`.
11. Carga el `_MOD` primero en QA antes de usarlo en PRD.

## Estructura De RULES.xlsx

Hoja esperada:

- nombre preferido: `RULES`
- si no existe, se usa la primera hoja solo si los encabezados son válidos

Encabezados obligatorios:

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
- `MANDT`: exactamente 3 dígitos
- `AGR_NAME`: sin espacios, máximo 30 caracteres
- `LOW` y `HIGH`: opcionales, máximo 40 caracteres por valor
- listas: usar `|` o `,`

Dependencias por tabla:

- `AGR_1251`: requiere `OBJECT`, `AUTH`, `FIELD`
- `AGR_1252`: requiere `FIELD` tipo `VARBL`, por ejemplo `$WERKS`

Ejemplo `AGR_1251`:

```text
replace_list | AGR_1251 | 100 | Z:FSBP_CRM_ZSALSPRO_EXT_1004 | S_RFC | T-BD08132800 | RFC_NAME | 0*|A* | 9*|Z*
```

Ejemplo `AGR_1252`:

```text
replace_list | AGR_1252 | 100 | Z:FSBP_CRM_ZSALSPRO_EXT_1004 |  |  | $WERKS | 0*|A* | 9*|Z*
```

## Interfaz

- **Idioma**: cambia entre `Español (ES)` y `English (EN)` sin reiniciar
- **Modo oscuro**: toggle animado y persistente
- **Cobertura**: muestra estado por regla (`APLICADA`, `SIN BASE`, `OMITIDA POR ERROR`, `CANCELADA`)
- **Diff visual**: resalta diferencias entre BEFORE y AFTER
- **Ayuda**: botón `?` con quick start y atajos (`F1`, `F5`, `F6`, `Esc`)
- **Log privado**: redacta `LOW/HIGH` en el log y en la muestra GUI
- **Meta SHA-256**: genera `_MOD_META.json` opcional para auditoría local

## Errores Comunes

- faltan columnas obligatorias en la hoja `RULES`
- `MANDT` no tiene 3 dígitos
- `AGR_NAME` tiene espacios o supera 30 caracteres
- `FIELD` de `AGR_1252` no empieza por `$`
- algún valor de `LOW/HIGH` supera 40 caracteres
- la regla no encuentra líneas base coincidentes

## Seguridad Y Buenas Prácticas

- La herramienta no envía información a internet.
- Si el log puede contener valores sensibles, activa `Log privado`.
- Si necesitas trazabilidad local, activa `Meta SHA-256`.
- Evita shares de red si no controlas permisos e integridad.
- La aplicación rechaza rutas inseguras, archivos demasiado grandes y salidas fuera de la carpeta elegida.

## CLI

Proceso normal:

```bash
python main.py --in <base> --rules <RULES.xlsx> --outdir <outdir> --lang es
```

Preview:

```bash
python main.py --in <base> --rules <RULES.xlsx> --preview --lang en
```

Opciones de seguridad:

```bash
python main.py --in <base> --rules <RULES.xlsx> --outdir <outdir> --redact-log --write-meta --debug
```

## Documentos Relacionados

- `docs/README.md`
- `docs/user/HELP.md`
- `docs/user/USAGE.md`
- `SECURITY.md`
- `PRIVACY.md`
- `BUILD.md`
- `CHANGELOG.md`
