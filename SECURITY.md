# Security Notes

## Threat Model

Entradas confiadas parcialmente:

- Archivo base exportado desde SAP
- Archivo `RULES.csv` preparado por usuario
- Carpeta de salida elegida por usuario

Riesgos principales:

- Escritura fuera de la carpeta de salida
- Corrupcion de `_MOD` o del log por cortes a mitad de proceso
- Denegacion de servicio por archivos muy grandes
- Exposicion de valores sensibles en logs
- Errores con demasiados detalles tecnicos visibles por defecto
- Procesamiento desde shares de red no confiables

## Controles Implementados

- Validacion de rutas con `pathlib` y resolucion explicita
- Verificacion de que base y reglas sean archivos regulares
- Verificacion de que salida sea carpeta existente y escribible
- Bloqueo de path traversal en archivos finales (`_MOD`, `_MOD_LOG.txt`, `_MOD_META.json`)
- Rechazo de rutas con caracteres de control y rutas demasiado largas en Windows
- Escritura atomica usando archivos temporales + `os.replace`
- Limites por tamano y lineas:
  - base: 300 MB / 10,000,000 lineas
  - reglas: 50 MB / 1,000,000 lineas
- Warning SEV3 para rutas UNC/red, con confirmacion extra antes de procesar en GUI
- Modo privacidad opcional para redactar LOW/HIGH en log y muestra GUI
- Metadata local opcional con checksums SHA-256
- GUI sin traceback completo por defecto; detalles tecnicos solo bajo demanda
- CLI con mensajes limpios y opcion `--debug` para detalles

## Uso Seguro Recomendado

- Validar siempre antes de procesar
- Probar primero en QA
- Activar `--redact-log` si LOW/HIGH contienen valores sensibles
- Activar `--write-meta` cuando necesites trazabilidad local
- No compartir logs fuera del equipo sin revisar su contenido
- Evitar shares de red si no controlas permisos y procedencia de los archivos

## Revisiones Recomendadas

- Ejecutar `.\security_checks.ps1`
- Ejecutar `python smoke_test.py`
- Revisar cambios con `git diff --stat`
- Escanear secretos antes de publicar:

```powershell
rg -n "password|token|apikey|secret" .
```

## Reporte De Issues

Si encuentras un problema de seguridad:

1. Reproduce con un caso minimo.
2. Guarda el codigo de error y el mensaje.
3. Adjunta solo el detalle tecnico necesario, evitando compartir LOW/HIGH sensibles.
