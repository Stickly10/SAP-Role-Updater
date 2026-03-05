# Architecture

## Overview

`SAP Role Updater` is a modular desktop monolith for Windows.

It is intentionally split into pure core logic, GUI presentation, and utility/infra helpers:

```text
Base export + RULES.csv
        |
        v
  core.processor
  - parse_rules
  - run_job_ex
  - fixed-width compose/parse
        |
        +--> warns_struct / counters / sample_rows
        |
        +--> _MOD / _MOD_LOG.txt / optional _MOD_META.json
        |
        v
   gui.window + gui.models
   - validate / process flow
   - progress / cancellation
   - i18n / theme / accessibility
```

## Source Layout

```text
src/
  sap_role_updater/
    core/
      constants.py
      processor.py
      validators.py
    gui/
      i18n.py
      models.py
      theme.py
      window.py
    utils/
      error_handler.py
      path_safety.py
      settings.py
    version.py
    main.py
```

Root files remain as compatibility wrappers for older scripts and the existing PyInstaller entrypoint.

## Data Flow

1. User selects base export, rules file, and output folder.
2. GUI or CLI calls `run_job_ex(...)`.
3. Core validates:
   - paths and file limits
   - RULES.csv structure and SAP-specific formats
4. Core parses the fixed-width base file into entries.
5. Core applies `replace_list` without changing the algorithm.
6. Core writes `_MOD` and `_MOD_LOG.txt` atomically.
7. Optional `_MOD_META.json` stores local SHA-256 metadata.
8. GUI renders summary, warnings, and sample changes.

## Key Design Decisions

- Pure-core first: `core.processor` has no Qt dependency.
- Offline by design: no network calls, no telemetry.
- Streaming where it matters: the log is written incrementally.
- Safe I/O: output paths are constrained to the selected output folder and use temp-file replacement.
- Legacy-safe: root wrappers keep existing entrypoints stable while the maintained code lives in `src/`.

## Scalability Notes

- The algorithm still requires the base export in memory because replacement preserves non-target lines in order.
- Safe limits are enforced before processing:
  - base: 300 MB / 10,000,000 lines
  - rules: 50 MB / 1,000,000 lines
- Cancellation happens before each rule and prevents partial final outputs.
