# Project Audit

## Scope

Audit date: 2026-03-05  
Target: `SAP Role Updater` desktop app (Python + PySide6 + Windows EXE)

## 1. Clean Code

- ✅ `src/` package structure created: `src/sap_role_updater/`
- ✅ Core / GUI / utils separated at package level
- ✅ Root files kept as compatibility wrappers only
- ✅ Central settings introduced in `src/sap_role_updater/utils/settings.py`
- ✅ Constants extracted to `src/sap_role_updater/core/constants.py`
- ⚠ Core logic is still concentrated in `src/sap_role_updater/core/processor.py`; deeper split is P1, not P0
- ✅ Ruff config added in `pyproject.toml`

Evidence:

- [src/sap_role_updater/](../../src/sap_role_updater/)
- [pyproject.toml](../../pyproject.toml)
- [legacy/README.md](../../legacy/README.md)

## 2. Documentation

- ✅ Consultant-facing guide updated in `README.md`
- ✅ Architecture documented in `docs/engineering/ARCHITECTURE.md`
- ✅ Quick help documented in `docs/user/HELP.md`
- ✅ Security, privacy, and responsible usage documented
- ✅ Changelog and release notes updated
- ✅ Secondary documentation reorganized under `docs/`

Evidence:

- [README.md](../../README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [HELP.md](../user/HELP.md)
- [SECURITY.md](../../SECURITY.md)
- [CHANGELOG.md](../../CHANGELOG.md)
- [RELEASE_NOTES.md](../releases/RELEASE_NOTES.md)
- [docs/README.md](../README.md)

## 3. Ciberseguridad

- ✅ Threat model documented
- ✅ Path normalization and output folder confinement implemented
- ✅ Atomic writes implemented
- ✅ File size and line limits enforced
- ✅ Privacy mode for logs available
- ✅ GUI hides tracebacks by default
- ✅ Optional local SHA-256 metadata available
- ✅ Security checks documented and scriptable
- ❌ Login / auth / sessions do not apply to this offline tool

Evidence:

- [path_safety.py](../../src/sap_role_updater/utils/path_safety.py)
- [processor.py](../../src/sap_role_updater/core/processor.py)
- [SECURITY.md](../../SECURITY.md)
- [SECURITY_CHECKLIST.md](../security/SECURITY_CHECKLIST.md)
- [security_checks.ps1](../../security_checks.ps1)

## 4. Arquitectura Y Escalabilidad

- ✅ Modular monolith documented and implemented
- ✅ Core has no Qt dependency
- ✅ GUI uses worker thread + cancellation
- ✅ Limits are centralized in settings
- ⚠ Base file still needs in-memory processing by design to preserve final ordering; this is documented as a tradeoff

Evidence:

- [processor.py](../../src/sap_role_updater/core/processor.py)
- [window.py](../../src/sap_role_updater/gui/window.py)
- [models.py](../../src/sap_role_updater/gui/models.py)
- [settings.py](../../src/sap_role_updater/utils/settings.py)
- [ARCHITECTURE.md](ARCHITECTURE.md)

## 5. Testing / QA

- ✅ `pytest` suite added
- ✅ Safe fixtures added under `tests/fixtures/`
- ✅ Preview no-write behavior covered
- ✅ Cancellation behavior covered
- ✅ Path output behavior covered
- ✅ Validator and BOM/delimiter behavior covered
- ✅ Manual QA checklist added

Evidence:

- [tests/](../../tests/)
- [fixtures/](../../tests/fixtures/)
- [QA_CHECKLIST.md](../user/QA_CHECKLIST.md)

## 6. DevOps / Automatizacion

- ✅ GitHub Actions workflow added
- ✅ `requirements-dev.txt` added
- ✅ Build and checks scripts added
- ✅ Semantic versioning helper added for `major.minor.patch`
- ✅ Release commands documented
- ✅ ZIP release packaging scripted
- ❌ Containerization does not apply to this Windows desktop EXE workflow

Evidence:

- [ci.yml](../../.github/workflows/ci.yml)
- [requirements-dev.txt](../../requirements-dev.txt)
- [build.ps1](../../scripts/build.ps1)
- [run_checks.ps1](../../scripts/run_checks.ps1)
- [bump_version.py](../../scripts/bump_version.py)
- [package_release.ps1](../../scripts/package_release.ps1)
- [RELEASE_COMMANDS.txt](../releases/RELEASE_COMMANDS.txt)

## 7. UX / Accesibilidad / i18n

- ✅ i18n remains JSON-based and hot-swappable
- ✅ Heuristic i18n audit script added
- ✅ Tooltips and quick help available
- ✅ Accessible names and descriptions added to main controls
- ✅ Explicit tab order added
- ✅ Theme toggle and language selector remain persistent
- ✅ Metric cards, tab counters, and keyboard shortcuts added
- ⚠ i18n audit is heuristic, not a formal proof

Evidence:

- [window.py](../../src/sap_role_updater/gui/window.py)
- [i18n.py](../../src/sap_role_updater/gui/i18n.py)
- [i18n_audit.py](../../scripts/i18n_audit.py)
- [es.json](../../locales/es.json)
- [en.json](../../locales/en.json)

## 8. Legal / Privacidad / Cumplimiento

- ✅ Privacy statement added
- ✅ Responsible usage guide added
- ✅ MIT license added for repository code
- ✅ Dependency notice added
- ✅ Local-only processing documented
- ⚠ Dependency redistribution obligations must still be reviewed by the organization before wider distribution

Evidence:

- [PRIVACY.md](../../PRIVACY.md)
- [USAGE.md](../user/USAGE.md)
- [LICENSE](../../LICENSE)
- [NOTICE.md](../legal/NOTICE.md)

## Decisions And Tradeoffs

- Kept root wrappers to preserve current entrypoints and PyInstaller behavior while moving active code into `src/`.
- Did not change the replacement algorithm or MOD format.
- Did not add online telemetry, auto-update, or remote services.
- Kept the base-file in-memory processing model because preserving untouched lines in order is more important than a risky algorithm rewrite.
- Chose `pytest` + `ruff` as the minimum sustainable QA baseline; mypy remains optional and is deferred to P1.
- Chose a ZIP release pack because GitHub normalizes asset filenames with spaces; inside the ZIP, the executable remains `SAP Role Updater.exe`.
