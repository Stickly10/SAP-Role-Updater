# Responsible Use

## Reglas Básicas

- trabaja con exportes de QA o entornos controlados
- usa `RULES_template.xlsx` como punto de partida
- revisa advertencias y cobertura antes de procesar
- no cargues directamente en PRD sin validar el `_MOD`

## Logs

- `_MOD_LOG.csv` usa separador `;`
- si el contenido puede ser sensible, activa `Log privado`

## Auditoría

- si necesitas trazabilidad local, activa `Meta SHA-256`
- conserva el template y el log junto con el `_MOD` del cambio aprobado
