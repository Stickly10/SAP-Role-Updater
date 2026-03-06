# Changelog

## [2.0.1] - 2026-03-06

### Fixed

- icono del ejecutable regenerado como `.ico` multiresolucion para mejorar su visualizacion en Explorer

### Changed

- branding movido a `assets/branding/`
- smoke test y checks de seguridad movidos a `scripts/`
- wrappers raiz innecesarios eliminados para dejar una estructura mas limpia

### Unchanged By Design

- algoritmo funcional de reemplazo
- formato final del archivo `_MOD`
- formato funcional del `_MOD_LOG.csv`

## [2.0.0] - 2026-03-05

### Added

- soporte exclusivo para `RULES.xlsx` vía `openpyxl`
- template `templates/RULES_template.xlsx` con hoja `RULES`, autofiltro y validaciones básicas
- indexado del archivo base para `AGR_1251` y `AGR_1252`
- cobertura por regla con resumen global
- pestaña `Cobertura` en la GUI con búsqueda y exportación CSV
- visor diff visual BEFORE/AFTER en la pestaña `Cambios`
- icono de aplicación y de ejecutable con `assets/branding/SAP-Role-Updater-Logo.ico`
- release pack ZIP para preservar el nombre interno `SAP Role Updater.exe`

### Changed

- `RULES.csv` queda retirado y ya no es aceptado
- el log estándar vuelve a ser `_MOD_LOG.csv` con delimitador `;`
- el empaquetado incluye icono, template Excel y locales dentro del bundle
- la versión sube a `2.0.0` por cambio incompatible de formato de reglas

### Unchanged By Design

- algoritmo funcional de reemplazo
- formato final del archivo `_MOD`
- ejecución local sin telemetría
