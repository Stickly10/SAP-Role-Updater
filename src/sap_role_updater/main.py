#!/usr/bin/env python3
"""Entry point for CLI + PySide6 GUI."""

import argparse
import sys
import traceback

from sap_role_updater.core.processor import build_meta_path, run_job
from sap_role_updater.gui.i18n import detect_system_language, load_locales, set_language, t
from sap_role_updater.utils.error_handler import CodedError
from sap_role_updater.utils.settings import APP_SETTINGS_NAME, APP_SETTINGS_ORG
from sap_role_updater.version import APP_VERSION


def _get_saved_language():
    try:
        from PySide6.QtCore import QSettings

        val = QSettings(APP_SETTINGS_ORG, APP_SETTINGS_NAME).value("language", "", type=str)
        return (val or "").strip().lower()
    except Exception:  # noqa: BLE001
        return ""


def main():
    load_locales()
    ap = argparse.ArgumentParser(
        description=t("cli.desc")
    )
    default_lang = _get_saved_language() or detect_system_language(default="es")
    ap.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    ap.add_argument("--in", dest="infile", help=t("cli.arg_in"))
    ap.add_argument("--rules", dest="rules", help=t("cli.arg_rules"))
    ap.add_argument("--outdir", dest="outdir", help=t("cli.arg_outdir"))
    ap.add_argument("--verbose", dest="verbose", action="store_true", default=False)
    ap.add_argument("--gui", dest="gui", action="store_true", help=t("cli.arg_gui"))
    ap.add_argument("--preview", dest="preview", action="store_true", help=t("cli.arg_preview"))
    ap.add_argument("--lang", dest="lang", default=default_lang, choices=["es", "en"], help=t("cli.arg_lang"))
    ap.add_argument("--redact-log", dest="redact_log", action="store_true", help=t("cli.arg_redact_log"))
    ap.add_argument("--write-meta", dest="write_meta", action="store_true", help=t("cli.arg_write_meta"))
    ap.add_argument("--debug", dest="debug", action="store_true", help=t("cli.arg_debug"))
    args = ap.parse_args()
    set_language(args.lang)

    auto_gui = len(sys.argv) == 1
    if auto_gui or args.gui:
        from sap_role_updater.gui.window import launch_gui

        launch_gui(APP_VERSION, args.lang)
        return

    if args.preview:
        if not (args.infile and args.rules):
            ap.error(t("cli.preview_requires"))
    else:
        if not (args.infile and args.rules and args.outdir):
            ap.error(t("cli.process_requires"))

    try:
        counters, _, log_path, warns = run_job(
            infile=args.infile,
            rules_path=args.rules,
            outdir=args.outdir,
            preview=args.preview,
            verbose=args.verbose,
            redact_log=args.redact_log,
            write_meta=args.write_meta,
        )
        if args.verbose:
            print(t("cli.rules_processed"))
        if args.preview:
            print(t("cli.end_preview"))
        else:
            print(t("cli.end_written", outdir=args.outdir))
            print(t("cli.log", log=log_path))
            if args.write_meta:
                print(t("cli.meta", meta=build_meta_path(args.infile, args.outdir)))
        print(
            t(
                "cli.summary",
                adds=counters["adds"],
                deletes=counters["deletes"],
                replaces=counters["replaces"],
                warns=counters["warns"],
            )
        )
        if warns:
            print(t("cli.warns", warns=" | ".join(warns)))
    except CodedError as ce:
        print(t("cli.error", code=ce.code, message=ce.message), file=sys.stderr)
        if args.debug and ce.details:
            print(t("cli.details", details=ce.details), file=sys.stderr)
        sys.exit(1)
    except Exception:  # noqa: BLE001
        print(t("cli.error", code="SYS-500", message=t("sys.unhandled")), file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
