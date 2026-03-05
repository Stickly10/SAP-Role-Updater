# SAP Role Updater v1.3.11

## Release Summary

This release focuses on release-readiness, engineering quality, and maintainability without changing the functional role-update algorithm.

## Added

- `src/sap_role_updater/` package structure
- `pytest` suite and safe fixtures
- CI workflow for lint, tests, i18n audit, and Windows build
- Accessibility improvements in the PySide6 GUI
- Documentation pack:
  - `ARCHITECTURE.md`
  - `HELP.md`
  - `PRIVACY.md`
  - `USAGE.md`
  - `PROJECT_AUDIT.md`
  - `ROADMAP.md`
  - `DEFINITION_OF_DONE.md`
  - `QA_CHECKLIST.md`
- Release helper scripts and commands

## Improved

- Central settings and resource path handling
- Cleaner package boundaries: core, gui, utils
- Reproducible build and dev workflow documentation
- Security checklist aligned with the actual offline threat model

## Compatibility Notes

- Core replacement algorithm remains unchanged
- Final MOD format remains unchanged
- Standard outputs remain:
  - `<base>_MOD`
  - `<base>_MOD_LOG.txt`
- Optional output remains:
  - `<base>_MOD_META.json`
