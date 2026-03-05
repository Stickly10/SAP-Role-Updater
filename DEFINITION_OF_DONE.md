# Definition Of Done

Any future change is done only when all items below are satisfied.

## Code Quality

- Code lives under `src/sap_role_updater/` unless it is a compatibility wrapper
- No unnecessary duplication
- New complex logic includes focused docstrings
- `python -m ruff check .` passes

## Functional Safety

- Core replacement algorithm is unchanged unless explicitly approved
- Final MOD format remains compatible
- Preview mode does not write files
- Processing writes atomically

## Security

- New I/O paths are validated and constrained
- No external telemetry or data transfer
- Sensitive outputs are documented if introduced
- `SECURITY.md` and `SECURITY_CHECKLIST.md` stay current

## Tests

- `python -m pytest` passes
- Relevant unit/integration tests are added for new behavior
- Manual QA checklist updated if the UI changes

## UX / i18n

- User-facing strings go through i18n
- Tooltips/help are updated if the flow changes
- Accessibility names/descriptions remain valid

## Release

- Version bumped once in the single source of truth
- `CHANGELOG.md`, `RELEASE_NOTES.md`, and `RELEASE_COMMANDS.txt` updated
- EXE builds successfully
- Commit, push, tag, and release completed or commands documented
