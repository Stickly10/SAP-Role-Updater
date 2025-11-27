#!/usr/bin/env python3
# SAP-Role-Updater 1.2.1 – Combined AGR_1251/AGR_1252 modifier (fixed-width SAP role exports)
# - Single rules CSV can target AGR_1251 and/or AGR_1252 in one run.
# - Preserves 1:1 every line that is not the targeted table.
# - Only action supported: replace_list.
# - Log CSV with header: action,before,after.
# Rules columns (case-insensitive): ACTION, TABLE, MANDT, AGR_NAME, OBJECT, AUTH, FIELD, LOW, HIGH
#   * For AGR_1251: OBJECT/AUTH required; FIELD = auth field; LOW/HIGH = value or range (40 chars each).
#   * For AGR_1252: leave OBJECT/AUTH empty; FIELD = org field (e.g. $WERKS); LOW/HIGH = org values/ranges (40 chars each, padded).
# Usage example:
#   python SAP-Role-Updater.py --in EXPORT.txt --rules RULES.csv --out EXPORT_mod.txt

__version__ = "1.2.6"

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
    "seq": 6,
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
    rf"(?P<seq>\d{{{PREFIX_WIDTHS['seq']}}})(?P<object>.{{{W1251['object']}}})(?P<auth>.{{{W1251['auth']}}})"
    rf"(?P<variant_pad>.{{{W1251['variant_pad']}}})(?P<field>.{{{W1251['field']}}})(?P<low>.{{{W1251['low']}}})"
    rf"(?P<high>.{{{W1251['high']}}})(?P<modified>.{{{W1251['modified']}}})(?P<deleted>.{{{W1251['deleted']}}})"
    rf"(?P<copied>.{{{W1251['copied']}}})(?P<neu>.{{{W1251['neu']}}})(?P<node>.{{{W1251['node']}}})(?P<tail>.*)$"
)

RX_1252 = re.compile(
    rf"^(?P<table>.{{{PREFIX_WIDTHS['table']}}})(?P<sp40>\s{{{PREFIX_WIDTHS['sp40']}}})"
    rf"(?P<mandt>\d{{{PREFIX_WIDTHS['mandt']}}})(?P<role>.{{{PREFIX_WIDTHS['role']}}})"
    rf"(?P<seq>\d{{{PREFIX_WIDTHS['seq']}}})(?P<varbl>.{{{W1252['varbl']}}})(?P<sp30>\s{{{W1252['sp30']}}})"
    rf"(?P<low>.{{0,{W1252['low']}}})(?P<high>.{{0,{W1252['high']}}})(?P<tail>.*)$"
)
# Legacy format (VARBL width 10 + LOW up to 4, no HIGH)
RX_1252_LEGACY = re.compile(
    rf"^(?P<table>.{{{PREFIX_WIDTHS['table']}}})(?P<sp40>\s{{{PREFIX_WIDTHS['sp40']}}})"
    rf"(?P<mandt>\d{{{PREFIX_WIDTHS['mandt']}}})(?P<role>.{{{PREFIX_WIDTHS['role']}}})"
    rf"(?P<seq>\d{{{PREFIX_WIDTHS['seq']}}})(?P<varbl>.{{{W1252['varbl']}}})(?P<sp30>\s{{{W1252['sp30']}}})"
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
        "seq": m.group("seq"),
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
        "seq": m.group("seq"),
        "varbl": m.group("varbl"),
        "sp30": m.group("sp30"),
        "low": m.group("low"),
        "high": high_val,
        "tail": m.group("tail"),
        "marked_deleted": False,
    }


def compose_line_1251(base, seq, field, low, high):
    parts = [
        fmt_fixed(base["table"], PREFIX_WIDTHS["table"]),
        base["sp40"],
        fmt_fixed(base["mandt"], PREFIX_WIDTHS["mandt"]),
        fmt_fixed(base["role"], PREFIX_WIDTHS["role"]),
        fmt_fixed(str(seq).rjust(PREFIX_WIDTHS["seq"], "0"), PREFIX_WIDTHS["seq"]),
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


def compose_line_1252(base, seq, varbl, org_value, high):
    return "".join(
        [
            fmt_fixed("AGR_1252", PREFIX_WIDTHS["table"]),
            " " * PREFIX_WIDTHS["sp40"],
            fmt_fixed(base["mandt"], PREFIX_WIDTHS["mandt"]),
            fmt_fixed(base["role"], PREFIX_WIDTHS["role"]),
            fmt_fixed(str(seq).rjust(PREFIX_WIDTHS["seq"], "0"), PREFIX_WIDTHS["seq"]),
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


def compute_max_seq(entries):
    """Track max seq per (table_type, role)."""
    maxseq = defaultdict(lambda: 0)
    for e in entries:
        if e and "seq" in e:
            try:
                key = (e["table_type"], e["role"])
                maxseq[key] = max(maxseq[key], int(e["seq"]))
            except ValueError:
                continue
    return maxseq


def handle_rule_1251(r, entries, role_to_maxseq, log_rows, counters):
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
        befores.append(h["raw"])
        counters["deletes"] += 1

    next_seq = role_to_maxseq[("AGR_1251", base["role"])] + 1
    afters = []
    for low_val, high_val in r["pairs"]:
        new_line = compose_line_1251(base, next_seq, field, low_val, high_val)
        role_to_maxseq[("AGR_1251", base["role"])] = next_seq
        next_seq += 1
        counters["adds"] += 1
        afters.append(new_line)
        ne = parse_entry_1251(new_line)
        ne["index"] = len(entries)
        ne["marked_deleted"] = False
        entries.append(ne)

    counters["replaces"] += 1
    append_replace_logs(befores, afters, log_rows)


def handle_rule_1252(r, entries, role_to_maxseq, log_rows, counters):
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
        befores.append(h["raw"])
        counters["deletes"] += 1

    next_seq = role_to_maxseq[("AGR_1252", base["role"])] + 1
    afters = []
    for low_val, high_val in r["pairs"]:
        new_line = compose_line_1252(base, next_seq, key[3], low_val, high_val)
        role_to_maxseq[("AGR_1252", base["role"])] = next_seq
        next_seq += 1
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
    ap.add_argument("--in", dest="infile", required=True, help="Input role export file")
    ap.add_argument("--rules", dest="rules", required=True, help="Rules CSV")
    ap.add_argument("--out", dest="outfile", required=True, help="Output role export file (modified)")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    ap.add_argument("--verbose", dest="verbose", action="store_true", default=False)
    args = ap.parse_args()

    try:
        lines, enc = read_text(args.infile)
        entries = build_entries(lines)
        rules = parse_rules(args.rules)
        role_to_maxseq = compute_max_seq(entries)

        counters = {"adds": 0, "deletes": 0, "replaces": 0, "warns": 0}
        log_rows = []

        for r in rules:
            if r["action"] != "replace_list":
                counters["warns"] += 1
                log_rows.append(["WARN-ACTION", f"Unsupported action: {r['action']}", ""])
                continue
            if r["table"] == "AGR_1251":
                handle_rule_1251(r, entries, role_to_maxseq, log_rows, counters)
            elif r["table"] == "AGR_1252":
                handle_rule_1252(r, entries, role_to_maxseq, log_rows, counters)
            else:
                counters["warns"] += 1
                log_rows.append(["WARN-TABLE", f"Ignored table={r['table']}", ""])

        out_lines = []
        for i, e in enumerate(entries):
            if e is None:
                out_lines.append(lines[i])  # original non-target line
            elif not e.get("marked_deleted"):
                out_lines.append(e["raw"])

        if not args.dry_run:
            with open(args.outfile, "w", encoding=enc, newline="\n") as f:
                for ln in out_lines:
                    f.write(ln + "\n")

        log_path = args.outfile + "_log.csv"
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

        if args.verbose:
            print(f"[rules] {len(rules)} processed")
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
