# Changelog

## [1.3.11] - 2026-03-05

### Added

- `src/sap_role_updater/` package structure with legacy compatibility wrappers at repo root
- `pytest` suite with fixtures and coverage for validators, preview mode, cancellation, and output paths
- GitHub Actions workflow for lint, tests, i18n audit, and Windows build dry-run
- Accessibility improvements in the GUI: accessible names/descriptions and explicit tab order
- Documentation pack: `ARCHITECTURE.md`, `HELP.md`, `PRIVACY.md`, `USAGE.md`, `PROJECT_AUDIT.md`, `ROADMAP.md`, `DEFINITION_OF_DONE.md`, `QA_CHECKLIST.md`
- Release helper scripts: `scripts/build.ps1`, `scripts/run_checks.ps1`, `scripts/i18n_audit.py`, `RELEASE_COMMANDS.txt`

### Changed

- Version source of truth moved to `src/sap_role_updater/version.py`
- Build, security, and QA workflows documented as repeatable steps
- Release notes and consultant-facing README updated for the release-ready workflow

### Unchanged By Design

- Core replacement algorithm
- Final MOD file format
- Standard log output format (`_MOD_LOG.txt`, tab-delimited)
