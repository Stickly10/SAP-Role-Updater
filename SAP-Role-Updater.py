#!/usr/bin/env python3
# SAP-Role-Updater – Combined AGR_1251/AGR_1252 modifier (fixed-width SAP role exports)
# - Single rules CSV can target AGR_1251 and/or AGR_1252 in one run.
# - Preserves 1:1 every line that is not the targeted table.
# - Only action supported: replace_list.
# - Log CSV with header: action,before,after.
# Rules columns (case-insensitive): ACTION, TABLE, MANDT, AGR_NAME, OBJECT, AUTH, FIELD, LOW, HIGH
#   * For AGR_1251: OBJECT/AUTH required; FIELD = auth field; LOW/HIGH = value or range (40 chars each).
#   * For AGR_1252: leave OBJECT/AUTH empty; FIELD = org field (e.g. $WERKS); LOW/HIGH = org values/ranges (40 chars each, padded).
# Usage example:
#   python SAP-Role-Updater.py --in EXPORT.txt --rules RULES.csv --out EXPORT_mod.txt

__version__ = "1.3.0"

import argparse
import csv
import re
import sys
from collections import defaultdict
from error_handler import CodedError, emit_error, raise_error

# ---------------- widths and regex ----------------

# Prefix shared by all tables
PREFIX_WIDTHS = {
    "table": 10,
    "sp40": 40,
    "mandt": 3,
    "role": 30,
    "counter": 6,
}

# AGR_1251 specifics
W1251 = {
    "object": 10,
    "auth": 12,
    "variant_pad": 4,  # spaces after AUTH
    "field": 10,
    "low": 40,
    "high": 40,
    "modified": 1,
    "deleted": 1,
    "copied": 1,
    "neu": 1,
    "node": 6,
}

# AGR_1252 specifics
W1252 = {
    "varbl": 10,  # $ + field name (10 chars)
    "sp30": 30,
    "low": 40,
    "high": 40,
}

# Regex builders
RX_1251 = re.compile(
    rf"^(?P<table>.{{{PREFIX_WIDTHS['table']}}})(?P<sp40>\s{{{PREFIX_WIDTHS['sp40']}}})"
    rf"(?P<mandt>\d{{{PREFIX_WIDTHS['mandt']}}})(?P<role>.{{{PREFIX_WIDTHS['role']}}})"
    rf"(?P<counter>\d{{{PREFIX_WIDTHS['counter']}}})(?P<object>.{{{W1251['object']}}})(?P<auth>.{{{W1251['auth']}}})"
    rf"(?P<variant_pad>.{{{W1251['variant_pad']}}})(?P<field>.{{{W1251['field']}}})(?P<low>.{{{W1251['low']}}})"
    rf"(?P<high>.{{{W1251['high']}}})(?P<modified>.{{{W1251['modified']}}})(?P<deleted>.{{{W1251['deleted']}}})"
    rf"(?P<copied>.{{{W1251['copied']}}})(?P<neu>.{{{W1251['neu']}}})(?P<node>.{{{W1251['node']}}})(?P<tail>.*)$"
)

RX_1252 = re.compile(
    rf"^(?P<table>.{{{PREFIX_WIDTHS['table']}}})(?P<sp40>\s{{{PREFIX_WIDTHS['sp40']}}})"
    rf"(?P<mandt>\d{{{PREFIX_WIDTHS['mandt']}}})(?P<role>.{{{PREFIX_WIDTHS['role']}}})"
    rf"(?P<counter>\d{{{PREFIX_WIDTHS['counter']}}})(?P<varbl>.{{{W1252['varbl']}}})(?P<sp30>\s{{{W1252['sp30']}}})"
    rf"(?P<low>.{{0,{W1252['low']}}})(?P<high>.{{0,{W1252['high']}}})(?P<tail>.*)$"
)
# Legacy format (VARBL width 10 + LOW up to 4, no HIGH)
RX_1252_LEGACY = re.compile(
    rf"^(?P<table>.{{{PREFIX_WIDTHS['table']}}})(?P<sp40>\s{{{PREFIX_WIDTHS['sp40']}}})"
    rf"(?P<mandt>\d{{{PREFIX_WIDTHS['mandt']}}})(?P<role>.{{{PREFIX_WIDTHS['role']}}})"
    rf"(?P<counter>\d{{{PREFIX_WIDTHS['counter']}}})(?P<varbl>.{{{W1252['varbl']}}})(?P<sp30>\s{{{W1252['sp30']}}})"
    rf"(?P<low>.{{0,4}})(?P<tail>.*)$"
)


# ---------------- utils ----------------

def read_text(path):
    """Read text tolerating common encodings; strip CR/LF endings."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return [ln.rstrip("\r\n") for ln in f.readlines()], enc
        except UnicodeDecodeError:
            continue
    with open(path, "rb") as f:
        data = f.read()
    return data.decode("latin-1", errors="ignore").splitlines(), "latin-1"


def detect_delimiter(header_line: str) -> str:
    if ";" in header_line and "," in header_line:
        return ";"
    if ";" in header_line:
        return ";"
    if "," in header_line:
        return ","
    if "\t" in header_line:
        return "\t"
    return ";"


def fmt_fixed(val: str, width: int) -> str:
    s = val or ""
    return s[:width] if len(s) > width else s.ljust(width)


def split_list(raw_vals: str):
    """Split LOW/LIST values on | or , and dedupe preserving order."""
    parts = [p.strip() for p in re.split(r"[|,]", raw_vals or "") if p.strip()]
    seen = set()
    dedup = []
    for v in parts:
        if v not in seen:
            seen.add(v)
            dedup.append(v)
    return dedup


def split_pairs(raw_low: str, raw_high: str, rule_ctx: dict = None):
    """Pair LOW/HIGH lists; HIGH may be shorter/empty, defaults to ''.
    If both are empty, return a single empty pair to force replace with blanks.
    If HIGH is provided without LOW, raise a clear validation error."""
    lows = split_list(raw_low)
    highs = split_list(raw_high)
    if not lows and any(h != "" for h in highs):
        ctx = rule_ctx or {}
        raise_error(
            "VAL-002",
            "SEV2",
            "HIGH provided but LOW is empty",
            err_type="Validation",
            origin="split_pairs",
            details=f"row={ctx.get('row','?')}, table={ctx.get('table','?')}, role={ctx.get('role','?')}, field={ctx.get('field','?')}",
        )
    pairs = []
    if not lows and not highs:
        pairs.append(("", ""))
    else:
        for idx, low_val in enumerate(lows):
            high_val = highs[idx] if idx < len(highs) else ""
            pairs.append((low_val, high_val))
    # de-dupe by (low, high) preserving order
    seen = set()
    dedup = []
    for low_val, high_val in pairs:
        key = (low_val, high_val)
        if key not in seen:
            seen.add(key)
            dedup.append(key)
    return dedup


def append_replace_logs(befores, afters, log_rows):
    """Align before/after lists and log REPLACE rows duplicating the shorter side."""
    if not befores and not afters:
        return
    n = max(len(befores), len(afters))
    for i in range(n):
        b = befores[min(i, len(befores) - 1)] if befores else ""
        a = afters[min(i, len(afters) - 1)] if afters else ""
        log_rows.append(["REPLACE", b, a])


def run_job(infile, rules_path, outfile, dry_run=False, verbose=False):
    lines, enc = read_text(infile)
    entries = build_entries(lines)
    rules = parse_rules(rules_path)
    counters_used = build_counters_state(entries)

    counters = {"adds": 0, "deletes": 0, "replaces": 0, "warns": 0}
    log_rows = []

    for r in rules:
        if r["action"] != "replace_list":
            counters["warns"] += 1
            log_rows.append(["WARN-ACTION", f"Unsupported action: {r['action']}", ""])
            continue
        if r["table"] == "AGR_1251":
            handle_rule_1251(r, entries, counters_used, log_rows, counters)
        elif r["table"] == "AGR_1252":
            handle_rule_1252(r, entries, counters_used, log_rows, counters)
        else:
            counters["warns"] += 1
            log_rows.append(["WARN-TABLE", f"Ignored table={r['table']}", ""])

    out_lines = []
    for i, e in enumerate(entries):
        if e is None:
            out_lines.append(lines[i])  # original non-target line
        elif not e.get("marked_deleted"):
            out_lines.append(e["raw"])

    if not dry_run:
        with open(outfile, "w", encoding=enc, newline="\n") as f:
            for ln in out_lines:
                f.write(ln + "\n")

    log_path = outfile + "_log.csv"
    with open(log_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["action", "before", "after"])
        for a, b, c in log_rows:
            w.writerow(
                [
                    a,
                    (b or "").replace("\r", " ").replace("\n", " "),
                    (c or "").replace("\r", " ").replace("\n", " "),
                ]
            )

    return counters, log_path


def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title(f"SAP Role Updater {__version__}")
    root.resizable(False, False)

    state = {"in": tk.StringVar(), "rules": tk.StringVar(), "out": tk.StringVar(), "dry": tk.BooleanVar(value=False)}

    def browse(target, save=False):
        if save:
            path = filedialog.asksaveasfilename(title="Select output file", initialfile="EXPORT_mod.txt")
        else:
            path = filedialog.askopenfilename(title="Select file")
        if path:
            state[target].set(path)
            if target == "in" and not state["out"].get():
                state["out"].set(path + "_MOD")

    def run():
        infile = state["in"].get()
        rules_path = state["rules"].get()
        outfile = state["out"].get()
        if not (infile and rules_path and outfile):
            messagebox.showerror("Error", "Selecciona archivo base, reglas y salida.")
            return
        try:
            counters, log_path = run_job(infile, rules_path, outfile, dry_run=state["dry"].get(), verbose=False)
            msg = f"Listo.\nAdds={counters['adds']} Deletes={counters['deletes']} Replaces={counters['replaces']} Warns={counters['warns']}\nLog: {log_path}"
            messagebox.showinfo("Éxito", msg)
        except CodedError as ce:
            emit_error(ce)
            messagebox.showerror("Error", f"{ce.code}: {ce.message}\n{ce.details or ''}")
        except Exception as ex:
            wrapped = CodedError("SYS-500", "SEV1", "Unhandled exception", details=str(ex), err_type="System", origin="gui")
            emit_error(wrapped)
            messagebox.showerror("Error", f"{wrapped.code}: {wrapped.message}\n{wrapped.details}")

    pad = {"padx": 8, "pady": 4}
    tk.Label(root, text="Archivo base").grid(row=0, column=0, sticky="w", **pad)
    tk.Entry(root, textvariable=state["in"], width=60).grid(row=0, column=1, **pad)
    tk.Button(root, text="Buscar", command=lambda: browse("in")).grid(row=0, column=2, **pad)

    tk.Label(root, text="Archivo reglas").grid(row=1, column=0, sticky="w", **pad)
    tk.Entry(root, textvariable=state["rules"], width=60).grid(row=1, column=1, **pad)
    tk.Button(root, text="Buscar", command=lambda: browse("rules")).grid(row=1, column=2, **pad)

    tk.Label(root, text="Archivo salida").grid(row=2, column=0, sticky="w", **pad)
    tk.Entry(root, textvariable=state["out"], width=60).grid(row=2, column=1, **pad)
    tk.Button(root, text="Guardar como", command=lambda: browse("out", save=True)).grid(row=2, column=2, **pad)

    tk.Checkbutton(root, text="Dry-run (no escribe archivo)", variable=state["dry"]).grid(row=3, column=1, sticky="w", **pad)

    tk.Button(root, text="Procesar", command=run, width=15).grid(row=4, column=1, pady=10)

    root.mainloop()


# ---------------- parse entries ----------------

def parse_entry_1251(line):
    m = RX_1251.match(line)
    if not m:
        return None
    return {
        "table_type": "AGR_1251",
        "raw": line,
        "table": m.group("table"),
        "sp40": m.group("sp40"),
        "mandt": m.group("mandt"),
        "role": m.group("role"),
        "counter": m.group("counter"),
        "object": m.group("object"),
        "auth": m.group("auth"),
        "variant_pad": m.group("variant_pad"),
        "field": m.group("field"),
        "low": m.group("low"),
        "high": m.group("high"),
        "modified": m.group("modified"),
        "deleted": m.group("deleted"),
        "copied": m.group("copied"),
        "neu": m.group("neu"),
        "node": m.group("node"),
        "tail": m.group("tail"),
        "marked_deleted": False,
    }


def parse_entry_1252(line):
    m = RX_1252.match(line)
    if not m:
        # Try legacy without HIGH and 4-char LOW
        m2 = RX_1252_LEGACY.match(line)
        if not m2:
            return None
        m = m2
        high_val = ""
    else:
        high_val = m.group("high")
    if m.group("table").strip() != "AGR_1252":
        return None
    return {
        "table_type": "AGR_1252",
        "raw": line,
        "table": m.group("table"),
        "sp40": m.group("sp40"),
        "mandt": m.group("mandt"),
        "role": m.group("role"),
        "counter": m.group("counter"),
        "varbl": m.group("varbl"),
        "sp30": m.group("sp30"),
        "low": m.group("low"),
        "high": high_val,
        "tail": m.group("tail"),
        "marked_deleted": False,
    }


def compose_line_1251(base, counter, field, low, high):
    parts = [
        fmt_fixed(base["table"], PREFIX_WIDTHS["table"]),
        base["sp40"],
        fmt_fixed(base["mandt"], PREFIX_WIDTHS["mandt"]),
        fmt_fixed(base["role"], PREFIX_WIDTHS["role"]),
        fmt_fixed(str(counter).rjust(PREFIX_WIDTHS["counter"], "0"), PREFIX_WIDTHS["counter"]),
        fmt_fixed(base["object"], W1251["object"]),
        fmt_fixed(base["auth"], W1251["auth"]),
        fmt_fixed(base.get("variant_pad", ""), W1251["variant_pad"]),
        fmt_fixed(field, W1251["field"]),
        fmt_fixed(low, W1251["low"]),
        fmt_fixed(high, W1251["high"]),
        base.get("modified", " "),
        base.get("deleted", " "),
        base.get("copied", " "),
        base.get("neu", " "),
        fmt_fixed(base.get("node", ""), W1251["node"]),
        base.get("tail", ""),
    ]
    return "".join(parts)


def compose_line_1252(base, counter, varbl, org_value, high):
    return "".join(
        [
            fmt_fixed("AGR_1252", PREFIX_WIDTHS["table"]),
            " " * PREFIX_WIDTHS["sp40"],
            fmt_fixed(base["mandt"], PREFIX_WIDTHS["mandt"]),
            fmt_fixed(base["role"], PREFIX_WIDTHS["role"]),
            fmt_fixed(str(counter).rjust(PREFIX_WIDTHS["counter"], "0"), PREFIX_WIDTHS["counter"]),
            fmt_fixed(varbl, W1252["varbl"]),
            " " * W1252["sp30"],
            fmt_fixed(org_value, W1252["low"]),
            fmt_fixed(high, W1252["high"]),
            base.get("tail", ""),
        ]
    )


# ---------------- rules ----------------

def parse_rules(path):
    txt, _ = read_text(path)
    if not txt:
        raise_error("VAL-001", "SEV3", "Rules file is empty", origin="parse_rules", err_type="Validation")
    delim = detect_delimiter(txt[0])
    reader = csv.DictReader(txt, delimiter=delim)
    rules = []
    for i, row in enumerate(reader, start=2):  # start at data row
        norm = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }
        # skip fully empty rows
        if all(v == "" for v in norm.values()):
            continue
        action = (norm.get("action", "replace_list") or "replace_list").lower()
        table = (norm.get("table", "") or "").upper()
        mandt = norm.get("mandt", "")
        role = norm.get("agr_name", "") or norm.get("role", "")
        obj = norm.get("object", "") or norm.get("objct", "")
        auth = norm.get("auth", "")
        field = norm.get("field", "") or norm.get("org_field", "") or norm.get("varbl", "")
        raw_low = norm.get("low", "") or norm.get("list", "")
        raw_high = norm.get("high", "")
        rules.append(
            {
                "row": i,
                "action": action,
                "table": table,
                "mandt": mandt,
                "role": role,
                "object": obj,
                "auth": auth,
                "field": field,
                "pairs": split_pairs(
                    raw_low,
                    raw_high,
                    {"row": i, "table": table, "role": role, "field": field},
                ),
            }
        )
    return rules


# ---------------- processing ----------------

def build_entries(lines):
    entries = []
    for idx, ln in enumerate(lines):
        e = parse_entry_1251(ln)
        if not e:
            e = parse_entry_1252(ln)
        if e:
            e["index"] = idx
            e["marked_deleted"] = False
        entries.append(e)  # None means non-target line
    return entries


def build_counters_state(entries):
    """Track used counters per (table_type, role)."""
    used = defaultdict(set)
    for e in entries:
        if e and "counter" in e:
            try:
                key = (e["table_type"], e["role"])
                used[key].add(int(e["counter"]))
            except ValueError:
                continue
    return used


def next_counter(key, used):
    """Return the smallest available counter for the role/table and mark it used."""
    n = 1
    s = used[key]
    while n in s:
        n += 1
    s.add(n)
    return n


def handle_rule_1251(r, entries, counters_used, log_rows, counters):
    required = ["mandt", "role", "object", "auth", "field"]
    if not all(r.get(k) for k in required):
        counters["warns"] += 1
        log_rows.append(
            [
                "WARN-RULE",
                f"Missing mandt/role/object/auth/field at row {r['row']}",
                "",
            ]
        )
        return

    key = (
        fmt_fixed(r["mandt"], PREFIX_WIDTHS["mandt"]),
        fmt_fixed(r["role"], PREFIX_WIDTHS["role"]),
        fmt_fixed(r["object"], W1251["object"]),
        fmt_fixed(r["auth"], W1251["auth"]),
    )
    field = fmt_fixed(r["field"], W1251["field"]).strip()

    hits = []
    for e in entries:
        if not e or e.get("marked_deleted") or e["table_type"] != "AGR_1251":
            continue
        if (e["mandt"], e["role"], e["object"], e["auth"]) == key and e["field"].strip() == field:
            hits.append(e)

    if not hits:
        counters["warns"] += 1
        log_rows.append(["WARN-NOBASE", f"No base lines for AGR_1251 key={key} field={field}", ""])
        return

    base = hits[0]
    befores = []
    for h in hits:
        h["marked_deleted"] = True
        try:
            counters_used[("AGR_1251", h["role"])].discard(int(h["counter"]))
        except ValueError:
            pass
        befores.append(h["raw"])
        counters["deletes"] += 1

    role_key = ("AGR_1251", base["role"])
    afters = []
    for low_val, high_val in r["pairs"]:
        counter_val = next_counter(role_key, counters_used)
        new_line = compose_line_1251(base, counter_val, field, low_val, high_val)
        counters["adds"] += 1
        afters.append(new_line)
        ne = parse_entry_1251(new_line)
        ne["index"] = len(entries)
        ne["marked_deleted"] = False
        entries.append(ne)

    counters["replaces"] += 1
    append_replace_logs(befores, afters, log_rows)


def handle_rule_1252(r, entries, counters_used, log_rows, counters):
    required = ["mandt", "role", "field"]
    if not all(r.get(k) for k in required):
        counters["warns"] += 1
        log_rows.append(["WARN-RULE", f"Missing mandt/role/field at row {r['row']}", ""])
        return

    mandt_clean = r["mandt"].strip()
    role_clean = r["role"].strip()
    varbl_clean = r["field"].strip()
    key = (
        fmt_fixed("AGR_1252", PREFIX_WIDTHS["table"]),
        fmt_fixed(mandt_clean, PREFIX_WIDTHS["mandt"]),
        fmt_fixed(role_clean, PREFIX_WIDTHS["role"]),
        fmt_fixed(varbl_clean, W1252["varbl"]),
    )

    hits = []
    for e in entries:
        if not e or e.get("marked_deleted") or e["table_type"] != "AGR_1252":
            continue
        if (
            e["table"].strip() == "AGR_1252"
            and e["mandt"].strip() == mandt_clean
            and e["role"].strip() == role_clean
            and e["varbl"].strip() == varbl_clean
        ):
            hits.append(e)

    if not hits:
        counters["warns"] += 1
        log_rows.append(["WARN-NOBASE", f"No base lines for AGR_1252 key={key}", ""])
        return

    base = hits[0]
    befores = []
    for h in hits:
        h["marked_deleted"] = True
        try:
            counters_used[("AGR_1252", h["role"])].discard(int(h["counter"]))
        except ValueError:
            pass
        befores.append(h["raw"])
        counters["deletes"] += 1

    role_key = ("AGR_1252", base["role"])
    afters = []
    for low_val, high_val in r["pairs"]:
        counter_val = next_counter(role_key, counters_used)
        new_line = compose_line_1252(base, counter_val, key[3], low_val, high_val)
        counters["adds"] += 1
        afters.append(new_line)
        ne = parse_entry_1252(new_line)
        ne["index"] = len(entries)
        ne["marked_deleted"] = False
        entries.append(ne)

    counters["replaces"] += 1
    append_replace_logs(befores, afters, log_rows)


# ---------------- main ----------------

def main():
    ap = argparse.ArgumentParser(
        description="Modify AGR_1251 and AGR_1252 fixed-width exports based on a single rules CSV (replace_list)."
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--in", dest="infile", help="Input role export file")
    ap.add_argument("--rules", dest="rules", help="Rules CSV")
    ap.add_argument("--out", dest="outfile", help="Output role export file (modified)")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    ap.add_argument("--verbose", dest="verbose", action="store_true", default=False)
    ap.add_argument("--gui", dest="gui", action="store_true", help="Launch simple GUI and ignore CLI paths")
    args = ap.parse_args()

    if args.gui:
        launch_gui()
        return
    if not (args.infile and args.rules and args.outfile):
        ap.error("When not using --gui, --in, --rules, and --out are required.")

    try:
        counters, log_path = run_job(
            infile=args.infile,
            rules_path=args.rules,
            outfile=args.outfile,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        if args.verbose:
            print(f"[rules] processed")
        print(f"[end] {'Dry-run, no file written.' if args.dry_run else 'Written: ' + args.outfile}")
        print(
            f"[summary] adds={counters['adds']} deletes={counters['deletes']} "
            f"replaces={counters['replaces']} warns={counters['warns']}"
        )
        print(f"[log] {log_path}")
    except CodedError as ce:
        emit_error(ce)
        sys.exit(1)
    except Exception as ex:
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
