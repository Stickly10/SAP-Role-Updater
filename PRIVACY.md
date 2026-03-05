# Privacy

## Declaración

SAP Role Updater no envía información a internet ni a terceros.

## Archivos Procesados Localmente

Entradas:

- archivo base exportado desde PFCG
- archivo `RULES.xlsx`

Salidas:

- `<base>_MOD`
- `<base>_MOD_LOG.csv`
- opcional `<base>_MOD_META.json`

## Recomendaciones

- no compartas `_MOD_LOG.csv` si contiene valores sensibles
- usa `Log privado` cuando aplique
- conserva `SHA-256` local si necesitas trazabilidad
- valida en QA antes de PRD
