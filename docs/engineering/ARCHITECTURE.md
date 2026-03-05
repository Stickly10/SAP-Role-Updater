# Architecture

## Componentes

- `src/sap_role_updater/core/`
  - parsing de base fixed-width
  - parsing y validación estricta de `RULES.xlsx`
  - procesamiento de reglas
  - indexado para `AGR_1251` y `AGR_1252`
  - cobertura por regla
- `src/sap_role_updater/gui/`
  - ventana principal PySide6
  - modelos de tabla
  - diff visual
  - i18n y theming
- `src/sap_role_updater/utils/`
  - path safety
  - settings y recursos
  - hashing y errores

## Flujo De Datos

1. Base exportada desde PFCG
2. `RULES.xlsx`
3. Validación estricta de reglas
4. Construcción de índices del base
5. Procesamiento por regla
6. Generación de:
   - `_MOD`
   - `_MOD_LOG.csv`
   - opcional `_MOD_META.json`

## Decisiones Técnicas

- monolito modular: sin dependencias GUI dentro del algoritmo funcional del MOD
- `openpyxl` en `read_only=True` para workbook de reglas
- índice por clave para evitar búsquedas lineales repetidas
- cobertura por regla separada del log de cambios
- diff visual solo en GUI; no altera outputs

## Compatibilidad

- el archivo `_MOD` conserva el comportamiento funcional previo
- el cambio incompatible de esta versión es el reemplazo de `RULES.csv` por `RULES.xlsx`
