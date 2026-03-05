# SAP Role Updater v1.3.9

## Added

- Theme toggle (dark/light) with persistence.
- Language selector (ES/EN) with JSON locale files in `locales/`.
- i18n pipeline for GUI text and structured warning messages (`msg_id`, `msg_params`).
- Consultant-oriented README in Spanish.
- Rules template for releases: `templates/RULES_template.csv`.

## Improved

- UI icons for file/folder actions now use Qt standard icons.
- Version centralized in `version.py`.
- CLI now supports `--lang` for translated output.
- Strict validation warnings remain blocking for process (SEV1/SEV2).

## Compatibility Notes

- Core replacement algorithm is unchanged.
- Output files remain:
  - `<base>_MOD`
  - `<base>_MOD_LOG.txt`
