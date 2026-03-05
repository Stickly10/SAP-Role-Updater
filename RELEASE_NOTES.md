# SAP Role Updater v1.3.10

## Added

- Security hardening for path validation, file size limits, and line count limits.
- Optional privacy mode for logs (`--redact-log` / `Log privado`).
- Optional local metadata file with SHA-256 checksums (`--write-meta` / `Meta SHA-256`).
- `SECURITY.md`, `SECURITY_CHECKLIST.md`, and `security_checks.ps1`.

## Improved

- Atomic writes for `_MOD`, `_MOD_LOG.txt`, and optional `_MOD_META.json`.
- Cleaner CLI error handling with optional `--debug`.
- GUI error dialogs now hide technical details by default and expose them only on demand.
- README and build instructions updated for secure usage and reproducible builds.
- Dependencies pinned in `requirements.txt`.

## Compatibility Notes

- Core replacement algorithm is unchanged.
- Standard outputs remain:
  - `<base>_MOD`
  - `<base>_MOD_LOG.txt`
- Optional extra output:
  - `<base>_MOD_META.json`
