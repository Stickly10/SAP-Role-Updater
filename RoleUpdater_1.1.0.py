#!/usr/bin/env python3
# RoleUpdater 1.1.0 — Combined AGR_1251/AGR_1252 modifier (fixed-width SAP role exports)
# - Single rules CSV can target AGR_1251 and/or AGR_1252 in one run.
# - Preserves 1:1 every line that is not the targeted table.
# - Only action supported: replace_list.
# - Log CSV with header: action,before,after.
# Rules columns (case-insensitive): ACTION, TABLE, MANDT, AGR_NAME, OBJECT, AUTH, FIELD, LOW, HIGH
#   * For AGR_1251: OBJECT/AUTH required; FIELD = auth field; LOW/HIGH = value or range (40 chars each).
#   * For AGR_1252: leave OBJECT/AUTH empty; FIELD = org field (e.g. $WERKS); LOW/HIGH = org values/ranges (40 chars each, padded).
# Usage example:
#   python RoleUpdater_1.1.0.py --in EXPORT.txt --rules RULES.csv --out EXPORT_mod.txt

__version__ = "1.1.0"

import argparse
import csv
import re
import sys
from collections import defaultdict
from error_handler import CodedError, emit_error, raise_error

# ---------------- widths and regex ----------------

WIDTHS_1251 = {
    "mandt": 3,
    "role": 30,
    "seq": 6,
    "obj": 10,
    "auth": 12,
    "sp4": 4,
    "field": 10,
    "low": 40,
    "high": 40,
}

WIDTHS_1252 = {
    "table": 10,
    "sp40": 40,
    "mandt": 3,
    "role": 30,
    "seq": 6,
    "org_field": 10,
    "sp30": 30,
    "org_value": 40,  # LOW width (AGR_1252-Low)
    "high": 40,       # HIGH width (AGR_1252-High)
}

# Capture fixed-width segments, preserving the gap after AGR_1251
RX_1251 = re.compile(
    r"^(AGR_1251)(\s+)(\d{3})(.{30})(\d{6})(.{10})(.{12})\s{4}(.{10})(.{40})(.{40})(.*)$"
)

# New 40/40 width (LOW/HIGH) format
RX_1252 = re.compile(
    r"^(?P<table>.{10})(?P<sp40>\s{40})(?P<mandt>\d{3})(?P<role>.{30})(?P<seq>\d{6})"
    r"(?P<org_field>.{10})(?P<sp30>\s{30})(?P<org_value>.{40})(?P<high>.{40})(?P<tail>.*)$"
)
# Legacy format (LOW up to 4 chars, no HIGH)
RX_1252_LEGACY = re.compile(
    r"^(?P<table>.{10})(?P<sp40>\s{40})(?P<mandt>\d{3})(?P<role>.{30})(?P<seq>\d{6})"
    r"(?P<org_field>.{10})(?P<sp30>\s{30})(?P<org_value>.{0,4})(?P<tail>.*)$"
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


# ---------------- parse entries ----------------

def parse_entry_1251(line):
    m = RX_1251.match(line)
    if not m:
        return None
    return {
        "table_type": "AGR_1251",
        "raw": line,
        "prefix": m.group(1) + m.group(2),
        "mandt": m.group(3),
        "role": m.group(4),
        "seq": m.group(5),
        "obj": m.group(6),
        "auth": m.group(7),
        "field": m.group(8),
        "low": m.group(9),
        "high": m.group(10),
        "tail": m.group(11),
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
        "org_field": m.group("org_field"),
        "sp30": m.group("sp30"),
        "org_value": m.group("org_value"),
        "high": high_val,
        "tail": m.group("tail"),
    }


def compose_line_1251(base, seq, field, low, high):
    parts = [
        base["prefix"],
        fmt_fixed(base["mandt"], WIDTHS_1251["mandt"]),
        fmt_fixed(base["role"], WIDTHS_1251["role"]),
        fmt_fixed(str(seq).rjust(WIDTHS_1251["seq"], "0"), WIDTHS_1251["seq"]),
        fmt_fixed(base["obj"], WIDTHS_1251["obj"]),
        fmt_fixed(base["auth"], WIDTHS_1251["auth"]),
        " " * WIDTHS_1251["sp4"],
        fmt_fixed(field, WIDTHS_1251["field"]),
        fmt_fixed(low, WIDTHS_1251["low"]),
        fmt_fixed(high, WIDTHS_1251["high"]),
        base["tail"],
    ]
    return "".join(parts)


def compose_line_1252(base, seq, org_field, org_value, high):
    # Do not propagate legacy tail content (could contain old HIGH); rebuild clean line.
    return "".join(
        [
            fmt_fixed("AGR_1252", WIDTHS_1252["table"]),
            " " * WIDTHS_1252["sp40"],
            fmt_fixed(base["mandt"], WIDTHS_1252["mandt"]),
            fmt_fixed(base["role"], WIDTHS_1252["role"]),
            fmt_fixed(str(seq).rjust(WIDTHS_1252["seq"], "0"), WIDTHS_1252["seq"]),
            fmt_fixed(org_field, WIDTHS_1252["org_field"]),
            " " * WIDTHS_1252["sp30"],
            fmt_fixed(org_value, WIDTHS_1252["org_value"]),
            fmt_fixed(high, WIDTHS_1252["high"]),
            "",
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
        action = (norm.get("action", "replace_list") or "replace_list").lower()
        table = (norm.get("table", "") or "").upper()
        mandt = norm.get("mandt", "")
        role = norm.get("agr_name", "") or norm.get("role", "")
        obj = norm.get("object", "") or norm.get("objct", "")
        auth = norm.get("auth", "")
        field = norm.get("field", "") or norm.get("org_field", "")
        raw_low = norm.get("low", "") or norm.get("list", "")
        raw_high = norm.get("high", "")
        rules.append(
            {
                "row": i,
                "action": action,
                "table": table,
                "mandt": mandt,
                "role": role,
                "obj": obj,
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
            e["deleted"] = False
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
    required = ["mandt", "role", "obj", "auth", "field"]
    if not all(r.get(k) for k in required):
        counters["warns"] += 1
        log_rows.append(
            [
                "WARN-RULE",
                f"Missing mandt/role/obj/auth/field at row {r['row']}",
                "",
            ]
        )
        return

    key = (
        fmt_fixed(r["mandt"], WIDTHS_1251["mandt"]),
        fmt_fixed(r["role"], WIDTHS_1251["role"]),
        fmt_fixed(r["obj"], WIDTHS_1251["obj"]),
        fmt_fixed(r["auth"], WIDTHS_1251["auth"]),
    )
    field = fmt_fixed(r["field"], WIDTHS_1251["field"]).strip()

    hits = []
    for e in entries:
        if not e or e.get("deleted") or e["table_type"] != "AGR_1251":
            continue
        if (e["mandt"], e["role"], e["obj"], e["auth"]) == key and e["field"].strip() == field:
            hits.append(e)

    if not hits:
        counters["warns"] += 1
        log_rows.append(["WARN-NOBASE", f"No base lines for AGR_1251 key={key} field={field}", ""])
        return

    base = hits[0]
    for h in hits:
        h["deleted"] = True
        counters["deletes"] += 1
        log_rows.append(["DELETE", h["raw"], ""])

    next_seq = role_to_maxseq[("AGR_1251", base["role"])] + 1
    for low_val, high_val in r["pairs"]:
        new_line = compose_line_1251(base, next_seq, field, low_val, high_val)
        role_to_maxseq[("AGR_1251", base["role"])] = next_seq
        next_seq += 1
        counters["adds"] += 1
        log_rows.append(["ADD", "", new_line])
        ne = parse_entry_1251(new_line)
        ne["index"] = len(entries)
        ne["deleted"] = False
        entries.append(ne)

    counters["replaces"] += 1


def handle_rule_1252(r, entries, role_to_maxseq, log_rows, counters):
    required = ["mandt", "role", "field"]
    if not all(r.get(k) for k in required):
        counters["warns"] += 1
        log_rows.append(["WARN-RULE", f"Missing mandt/role/field at row {r['row']}", ""])
        return

    org_field = r["field"]
    key = (
        fmt_fixed("AGR_1252", WIDTHS_1252["table"]),
        fmt_fixed(r["mandt"], WIDTHS_1252["mandt"]),
        fmt_fixed(r["role"], WIDTHS_1252["role"]),
        fmt_fixed(org_field, WIDTHS_1252["org_field"]),
    )

    hits = []
    for e in entries:
        if not e or e.get("deleted") or e["table_type"] != "AGR_1252":
            continue
        if (
            e["table"] == key[0]
            and e["mandt"] == key[1]
            and e["role"] == key[2]
            and e["org_field"] == key[3]
        ):
            hits.append(e)

    if not hits:
        counters["warns"] += 1
        log_rows.append(["WARN-NOBASE", f"No base lines for AGR_1252 key={key}", ""])
        return

    base = hits[0]
    for h in hits:
        h["deleted"] = True
        counters["deletes"] += 1
        log_rows.append(["DELETE", h["raw"], ""])

    next_seq = role_to_maxseq[("AGR_1252", base["role"])] + 1
    for low_val, high_val in r["pairs"]:
        new_line = compose_line_1252(base, next_seq, key[3], low_val, high_val)
        role_to_maxseq[("AGR_1252", base["role"])] = next_seq
        next_seq += 1
        counters["adds"] += 1
        log_rows.append(["ADD", "", new_line])
        ne = parse_entry_1252(new_line)
        ne["index"] = len(entries)
        ne["deleted"] = False
        entries.append(ne)

    counters["replaces"] += 1


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
            elif not e.get("deleted"):
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
