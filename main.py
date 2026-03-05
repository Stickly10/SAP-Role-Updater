#!/usr/bin/env python3
"""Entry point for CLI + PySide6 GUI."""

import argparse
import sys

from error_handler import CodedError, emit_error
from sap_role_updater_core import __version__, run_job


def main():
    ap = argparse.ArgumentParser(
        description="Modify AGR_1251 and AGR_1252 fixed-width exports based on a single rules CSV (replace_list)."
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--in", dest="infile", help="Input role export file")
    ap.add_argument("--rules", dest="rules", help="Rules CSV")
    ap.add_argument("--outdir", dest="outdir", help="Output directory for files")
    ap.add_argument("--verbose", dest="verbose", action="store_true", default=False)
    ap.add_argument("--gui", dest="gui", action="store_true", help="Launch GUI and ignore CLI paths")
    ap.add_argument("--preview", dest="preview", action="store_true", help="Preview counts without writing output")
    args = ap.parse_args()

    auto_gui = len(sys.argv) == 1
    if auto_gui or args.gui:
        from gui_pyside6 import launch_gui

        launch_gui(__version__)
        return

    if args.preview:
        if not (args.infile and args.rules):
            ap.error("Preview requires --in and --rules.")
    else:
        if not (args.infile and args.rules and args.outdir):
            ap.error("When not using --gui, --in, --rules, and --outdir are required.")

    try:
        counters, _, log_path, warns = run_job(
            infile=args.infile,
            rules_path=args.rules,
            outdir=args.outdir,
            preview=args.preview,
            verbose=args.verbose,
        )
        if args.verbose:
            print("[rules] processed")
        if args.preview:
            print("[end] Preview only, no files written.")
        else:
            print(f"[end] Written to {args.outdir}")
            print(f"[log] {log_path}")
        print(f"[summary] adds={counters['adds']} deletes={counters['deletes']} replaces={counters['replaces']} warns={counters['warns']}")
        if warns:
            print("[warns] " + " | ".join(warns))
    except CodedError as ce:
        emit_error(ce)
        sys.exit(1)
    except Exception as ex:  # noqa: BLE001
        wrapped = CodedError(
            "SYS-500",
            "SEV1",
            "Unhandled exception",
            details=str(ex),
            err_type="System",
            origin="main",
        )
        emit_error(wrapped)
        sys.exit(1)


if __name__ == "__main__":
    main()
