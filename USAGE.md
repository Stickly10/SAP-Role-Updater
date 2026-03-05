# Responsible Usage

## Intended Use

`SAP Role Updater` is intended to prepare SAP role import files from controlled inputs.

## Recommended Operating Model

1. Work with approved base exports only.
2. Validate rules before processing.
3. Review warnings and the generated log.
4. Import in QA before any productive environment.

## Limitation Of Responsibility

This tool automates file preparation. It does not replace SAP role design review, SoD analysis, transport governance, or QA approval.

Users remain responsible for:

- correctness of `RULES.csv`
- protecting generated files
- validating results in SAP before productive use
