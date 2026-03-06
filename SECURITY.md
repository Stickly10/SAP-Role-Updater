# Security

## Threat Model

Entradas locales de riesgo controlado:

- archivo base SAP exportado desde PFCG
- archivo `RULES.xlsx`
- carpeta de salida seleccionada por el usuario

Riesgos relevantes para esta aplicación offline:

- escritura fuera de la carpeta de salida
- corrupción de outputs por fallos o cancelación
- DoS por archivos excesivamente grandes
- exposición de valores sensibles en logs
- apertura desde shares de red no confiables
- errores técnicos mostrados con demasiado detalle al usuario final

## Controls Implemented

### Path Safety

- normalización con `pathlib`
- validación de archivos regulares para base y reglas
- validación de carpeta de salida existente y escribible
- bloqueo de outputs fuera del `outdir`
- rechazo de caracteres de control y rutas Windows inseguras
- advertencia `SEV3` para rutas UNC/red con confirmación explícita en GUI

### Safe Writes

- escritura atómica para `_MOD`, `_MOD_LOG.csv` y `_MOD_META.json`
- cancelación sin dejar archivos finales incompletos

### Limits / DoS Protection

- base: `300 MB` y `10,000,000` líneas por defecto
- reglas: `50 MB` y `1,000,000` líneas por defecto
- límites centralizados en `src/sap_role_updater/utils/settings.py`

### Input Validation

- validación estricta de headers y filas de `RULES.xlsx`
- validación de formato y longitud para campos SAP
- sin heurísticas ni inferencias automáticas

### Logging / Privacy

- `Log privado` redacta `LOW/HIGH` en la muestra GUI y en `_MOD_LOG.csv`
- sin telemetría online
- checksums SHA-256 opcionales para auditoría local

## Offline Data Handling

La herramienta no transmite datos a internet.

Archivos generados localmente:

- `<base>_MOD`
- `<base>_MOD_LOG.csv`
- opcional `<base>_MOD_META.json`

## Secure Usage Recommendations

- procesa siempre primero en QA
- evita compartir logs si contienen valores sensibles
- usa `Log privado` cuando el contenido del rol sea sensible
- prefiere carpetas locales sobre rutas de red
- revisa cobertura y log antes de importar a SAP

## Security Review Commands

Ver:

- `docs/security/SECURITY_CHECKLIST.md`
- `scripts/security_checks.ps1`
