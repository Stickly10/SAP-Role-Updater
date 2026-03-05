# Privacy

## Local-Only Processing

This tool does not send information to the internet.

- No telemetry
- No analytics
- No cloud upload
- No background sync

## Files Processed Locally

Inputs:

- Base export from SAP PFCG Mass Download
- `RULES.csv`

Outputs:

- `<base>_MOD`
- `<base>_MOD_LOG.txt`
- Optional `<base>_MOD_META.json`

## Sensitive Information Considerations

Although the tool is offline, role values and organizational values may be sensitive for information security purposes.

Recommendations:

- Do not share `_MOD_LOG.txt` unless it is strictly necessary.
- If the log may expose sensitive LOW/HIGH values, enable privacy mode (`Log privado` / `--redact-log`).
- Store generated files only in approved internal folders.

## Compliance Note

The tool may process authorization or organizational data that can be operationally sensitive. Processing is local, which reduces transfer risk, but secure handling remains the responsibility of the user and the organization.
