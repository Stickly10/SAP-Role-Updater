# Legacy Compatibility

Este directorio documenta compatibilidad hacia atras.

- Los wrappers en la raiz (`main.py`, `sap_role_updater_core.py`, `gui_pyside6.py`, etc.) existen para no romper scripts antiguos ni el entrypoint de PyInstaller.
- La GUI Tkinter anterior ya no forma parte del flujo activo del proyecto.
- El codigo mantenido y soportado vive en `src/sap_role_updater/`.
