# SAP Role Updater v1.3.12

## Release Summary

This release fixes the release asset naming workflow and formalizes semantic versioning without changing the functional role-update algorithm.

## Added

- Semantic version parser and bump helpers in `src/sap_role_updater/version.py`
- `scripts/bump_version.py` for `major`, `minor`, `patch`, and `set x.y.z`

## Improved

- Release commands now upload the executable with explicit display label `SAP Role Updater.exe`
- Versioning workflow now follows documented semantic versioning instead of ad-hoc patch bumps

## Compatibility Notes

- Core replacement algorithm remains unchanged
- Final MOD format remains unchanged
- Standard outputs remain:
  - `<base>_MOD`
  - `<base>_MOD_LOG.txt`
- Optional output remains:
  - `<base>_MOD_META.json`
