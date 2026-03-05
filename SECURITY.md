# Security

## Threat Model

Trusted-but-risky local inputs:

- SAP base export file
- `RULES.csv`
- output folder selected by the user

Main risks for this offline desktop tool:

- path traversal or writes outside the intended output folder
- corrupt or partial outputs if the process stops mid-write
- denial of service via very large files
- sensitive LOW/HIGH values exposed in logs
- too much technical detail shown to end users by default
- use of untrusted network shares

## Controls Implemented

### Path Safety

- `pathlib`-based normalization and resolution
- input files must be regular files
- output folder must already exist and be writable
- final output targets are validated to remain inside the chosen output folder
- control characters in paths are rejected
- suspiciously long Windows paths are blocked
- UNC/network paths generate SEV3 warnings and require confirmation in GUI before processing

### Safe Writes

- `_MOD`, `_MOD_LOG.txt`, and optional `_MOD_META.json` use temp file + atomic replace
- cancellation does not leave final partial outputs behind

### Limits / DoS Protection

- base export default limit: `300 MB`, `10,000,000` lines
- rules file default limit: `50 MB`, `1,000,000` lines
- limits are centralized in `src/sap_role_updater/utils/settings.py`

### Input Validation

- strict `RULES.csv` header validation
- strict SAP field length and format validation
- no heuristics or silent inference for missing fields

### Logging / Privacy

- optional privacy mode redacts LOW/HIGH values in the GUI sample and log
- no network logging or telemetry
- GUI hides tracebacks by default and shows technical details only on demand

### Dependency Checks

- `ruff`, `pytest`, `bandit`, and `pip-audit` are documented and scriptable

## Offline Data Handling

The tool does not transmit data to the internet.

Generated files remain local:

- `<base>_MOD`
- `<base>_MOD_LOG.txt`
- optional `<base>_MOD_META.json`

## Secure Usage Recommendations

- Work from QA-approved input files only
- Prefer local folders over network shares
- Use privacy mode if logs may expose sensitive values
- Review `_MOD_LOG.txt` before importing into SAP
- Test in QA before productive use

## Security Review Commands

See:

- `SECURITY_CHECKLIST.md`
- `security_checks.ps1`

## Reporting

When reporting a security issue internally, include:

- app version
- exact error code
- minimal reproduction steps
- sanitized sample files if needed
