# Quick Help

## Quick Start

1. Export the role base file from PFCG Mass Download.
2. Prepare `RULES.csv` using `templates/RULES_template.csv`.
3. Open `SAP Role Updater.exe`.
4. Select Base, Rules, and Output folder.
5. Run **Validar**.
6. Fix blocking errors (`SEV1/SEV2`) if any.
7. Run **Procesar**.
8. Review `_MOD_LOG.txt` before importing into SAP.

## How To Read Results

- `Errores (SEV1/SEV2)`: blocking issues. Processing stays disabled.
- `Advertencias (SEV3)`: processing is allowed, but user confirmation is required.
- `Cambios`: only a sample view of the tabulated log, not the full file.

## SAP Glossary

- `AGR_1251`: fixed-width table for authorization object values in the role export.
- `AGR_1252`: fixed-width table for organizational values (`VARBL`, e.g. `$WERKS`).
- `PFCG Mass Download`: SAP export used as the base input file.
- `VARBL`: organization field identifier for `AGR_1252`, e.g. `$WERKS`, `$BUKRS`.
- `LOW/HIGH`: value or range boundaries in the rule file.
- `replace_list`: supported action that deletes the matched original lines and appends the new target lines.

## Security Tips

- Use **Log privado** if LOW/HIGH values should not appear in plain text in the log.
- Use **Meta SHA-256** when you need local audit evidence of the exact base and rules files used.
- Prefer local folders over network shares unless you trust the permissions and integrity of the share.
