# QA Checklist

## Functional

- Open GUI with `python main.py`
- Open GUI with `python main.py --gui`
- Validate a correct `RULES.csv`
- Confirm `Procesar` stays disabled when validation errors exist
- Process a valid file set and verify `_MOD` and `_MOD_LOG.txt`
- Enable `Meta SHA-256` and verify `_MOD_META.json`
- Enable `Log privado` and verify LOW/HIGH are redacted in the log
- Cancel a running job and verify no final outputs are created

## UX / i18n

- Change language from ES to EN and back
- Toggle dark/light theme
- Open quick help dialog
- Filter rows in `Advertencias` and `Cambios`
- Resize the window and verify tables remain usable

## File Actions

- Open output folder from footer button
- Open log from footer button
- Try a network path and verify the warning confirmation appears

## CLI

- Run preview mode
- Run process mode
- Run with `--redact-log`
- Run with `--write-meta`
- Run with `--debug` and confirm technical details appear only then
