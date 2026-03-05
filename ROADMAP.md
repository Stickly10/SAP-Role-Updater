# Roadmap

## P0 - Required For Release

- Keep `ruff`, `pytest`, and `i18n_audit.py` green
- Build `SAP Role Updater.exe` from the current tagged source
- Keep consultant docs, security docs, and release notes synchronized with the shipped version
- Keep semantic versioning (`major.minor.patch`) explicit and consistent across release artifacts
- Preserve compatibility of CLI, GUI, and final MOD output

## P1 - Next Engineering Iteration

- Deeper split of `core.processor` into smaller modules (`validators`, `parsers`, `writers`)
- Add more integration fixtures for `AGR_1251`
- Add optional mypy type-checking in CI
- Add signed-build guidance for the Windows executable

## P2 - Future Improvements

- Broader accessibility pass with keyboard shortcut review
- Richer QA matrix with packaged EXE smoke tests
- More granular redaction modes for logs and UI previews
