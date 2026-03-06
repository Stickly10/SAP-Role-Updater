# QA Checklist

## GUI

- abrir la GUI sin argumentos
- cambiar idioma ES/EN
- cambiar tema claro/oscuro
- seleccionar base
- seleccionar `RULES.xlsx`
- seleccionar carpeta de salida
- validar reglas correctas
- bloquear procesamiento con reglas inválidas
- abrir pestaña `Cobertura`
- abrir pestaña `Cambios` y revisar diff visual
- exportar cobertura a CSV
- probar cancelación
- abrir carpeta de salida y log

## CLI

- `python main.py --gui`
- `python main.py --in <base> --rules <RULES.xlsx> --preview`
- `python main.py --in <base> --rules <RULES.xlsx> --outdir <outdir>`
- `python main.py --in <base> --rules <RULES.xlsx> --outdir <outdir> --redact-log --write-meta`

## Release Pack

- `dist/SAP Role Updater.exe`
- `dist/SAP Role Updater v2.0.1.zip`
- `templates/RULES_template.xlsx`
