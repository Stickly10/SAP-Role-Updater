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
#   python SAP-Role-Updater.py --in EXPORT.txt --rules RULES.csv --outdir ./salida

__version__ = "1.3.8"

import csv
import os
import re
from collections import defaultdict
from typing import Callable
from error_handler import CodedError, raise_error

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


def split_sequence(raw_vals: str, keep_empty: bool = False):
    """Split on | or , preserving item positions when requested.

    keep_empty=True is used for HIGH to allow mixed rules such as:
      LOW  = *|/*|0*|A*
      HIGH = ||9*|Z*
    """
    txt = raw_vals or ""
    if not txt.strip() and "|" not in txt and "," not in txt:
        return []

    if "|" in txt:
        parts = txt.split("|")
    elif "," in txt:
        parts = txt.split(",")
    else:
        parts = [txt]

    vals = [p.strip() for p in parts]
    if keep_empty:
        return vals
    return [v for v in vals if v != ""]


def split_pairs(raw_low: str, raw_high: str, rule_ctx: dict = None):
    """Pair LOW/HIGH lists; HIGH may be shorter/empty, defaults to ''.
    If both are empty, return a single empty pair to force replace with blanks.
    If HIGH is provided without LOW, raise a clear validation error."""
    lows = split_sequence(raw_low, keep_empty=False)
    highs = split_sequence(raw_high, keep_empty=True)
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


def build_output_paths(infile, outdir):
    base = os.path.basename(infile)
    name, ext = os.path.splitext(base)
    if not ext:
        ext = ""
    outfile = os.path.join(outdir, f"{name}_MOD{ext}")
    log_path = os.path.join(outdir, f"{name}_MOD_LOG.tsv")
    return outfile, log_path


def _empty_result(status="ok"):
    return {
        "status": status,
        "counters": {"adds": 0, "deletes": 0, "replaces": 0, "warns": 0},
        "outfile": "",
        "log_path": "",
        "warns_details": [],
        "warns_struct": [],
        "sample_rows": [],
        "encoding_detected": "",
        "delimiter_detected": "",
        "base_stats": {},
        "rules_stats": {},
    }


def _build_base_stats(lines, entries):
    roles = set()
    cnt_1251 = 0
    cnt_1252 = 0
    for e in entries:
        if not e:
            continue
        role = e.get("role", "").strip()
        if role:
            roles.add(role)
        if e.get("table_type") == "AGR_1251":
            cnt_1251 += 1
        elif e.get("table_type") == "AGR_1252":
            cnt_1252 += 1
    return {
        "total_lines": len(lines),
        "target_lines": cnt_1251 + cnt_1252,
        "agr_1251_lines": cnt_1251,
        "agr_1252_lines": cnt_1252,
        "other_lines": len(lines) - (cnt_1251 + cnt_1252),
        "roles_unique": len(roles),
    }


def run_job_ex(
    infile: str,
    rules_path: str,
    outdir: str | None = None,
    *,
    preview: bool = False,
    verbose: bool = False,
    ui_sample_limit: int = 300,
    progress_cb: Callable[[int, int, str], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> dict:
    del verbose  # reserved for future hooks; legacy signature compatibility.
    res = _empty_result(status="ok")
    log_fh = None
    log_writer = None
    temp_log_path = ""
    temp_out_path = ""
    final_out_path = ""
    final_log_path = ""

    def progress(current, total, message):
        if progress_cb:
            progress_cb(current, total, message)

    def clean_text(val):
        return (val or "").replace("\r", " ").replace("\n", " ")

    def log_emit(action, before, after):
        row = [action, clean_text(before), clean_text(after)]
        if len(res["sample_rows"]) < ui_sample_limit:
            res["sample_rows"].append(row)
        if log_writer:
            log_writer.writerow(row)

    def warn_emit(code, detail, severity="SEV3", rule=None, legacy=False):
        info = {
            "code": code,
            "severity": severity,
            "row": (rule or {}).get("row"),
            "table": (rule or {}).get("table", ""),
            "role": (rule or {}).get("role", ""),
            "field": (rule or {}).get("field", ""),
            "detail": detail,
        }
        res["warns_struct"].append(info)
        if legacy:
            res["warns_details"].append(detail)

    try:
        if not preview and not outdir:
            raise_error("VAL-004", "SEV2", "Output directory is required unless preview", origin="run_job_ex", err_type="Validation")

        progress(0, 5, "Leyendo archivo base...")
        lines, enc = read_text(infile)
        res["encoding_detected"] = enc
        entries = build_entries(lines)
        res["base_stats"] = _build_base_stats(lines, entries)

        progress(1, 5, "Parseando reglas...")
        rules, rules_meta = parse_rules(rules_path, return_meta=True)
        res["delimiter_detected"] = rules_meta["delimiter_detected"]
        res["rules_stats"] = rules_meta["rules_stats"]
        counters_used = build_counters_state(entries)

        if not preview:
            final_out_path, final_log_path = build_output_paths(infile, outdir)
            temp_out_path = final_out_path + ".tmp"
            temp_log_path = final_log_path + ".tmp"
            log_fh = open(temp_log_path, "w", encoding="utf-8", newline="")
            log_writer = csv.writer(log_fh, delimiter="\t")
            log_writer.writerow(["action", "before", "after"])

        total_rules = max(len(rules), 1)
        for idx, r in enumerate(rules, start=1):
            if is_cancelled and is_cancelled():
                res["status"] = "cancelled"
                return res
            progress(idx, total_rules, f"Procesando regla {idx}/{total_rules} ...")

            rule_log_rows = []
            if r["action"] != "replace_list":
                res["counters"]["warns"] += 1
                warn_emit("WARN-ACTION", f"Unsupported action: {r['action']} (row={r['row']})", severity="SEV3", rule=r, legacy=True)
                rule_log_rows.append(["WARN-ACTION", f"Unsupported action: {r['action']}", ""])
            elif r["table"] == "AGR_1251":
                handle_rule_1251(r, entries, counters_used, rule_log_rows, res["counters"])
            elif r["table"] == "AGR_1252":
                handle_rule_1252(r, entries, counters_used, rule_log_rows, res["counters"])
            else:
                res["counters"]["warns"] += 1
                warn_emit("WARN-TABLE", f"Ignored table={r['table']} (row={r['row']})", severity="SEV3", rule=r, legacy=True)
                rule_log_rows.append(["WARN-TABLE", f"Ignored table={r['table']}", ""])

            for action, before, after in rule_log_rows:
                log_emit(action, before, after)
                if action in ("WARN-RULE", "WARN-NOBASE"):
                    warn_emit(action, before, severity="SEV3", rule=r)

        if is_cancelled and is_cancelled():
            res["status"] = "cancelled"
            return res

        out_lines = []
        for i, e in enumerate(entries):
            if e is None:
                out_lines.append(lines[i])  # original non-target line
            elif not e.get("marked_deleted"):
                out_lines.append(e["raw"])

        if not preview:
            progress(total_rules, total_rules, "Escribiendo archivo MOD...")
            with open(temp_out_path, "w", encoding=enc, newline="\n") as f:
                for ln in out_lines:
                    f.write(ln + "\n")

            if log_fh:
                log_fh.flush()
                log_fh.close()
                log_fh = None
            os.replace(temp_out_path, final_out_path)
            os.replace(temp_log_path, final_log_path)
            res["outfile"] = final_out_path
            res["log_path"] = final_log_path

        progress(total_rules, total_rules, "Finalizado.")
        return res
    except CodedError as ce:
        res["status"] = "error"
        res["error"] = ce
        return res
    except Exception as ex:  # noqa: BLE001
        wrapped = CodedError(
            "SYS-500",
            "SEV1",
            "Unhandled exception",
            details=str(ex),
            err_type="System",
            origin="run_job_ex",
        )
        res["status"] = "error"
        res["error"] = wrapped
        return res
    finally:
        if log_fh:
            log_fh.close()
        if res["status"] != "ok":
            for p in (temp_out_path, temp_log_path):
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass


def run_job(infile, rules_path, outdir=None, verbose=False, preview=False):
    res = run_job_ex(
        infile=infile,
        rules_path=rules_path,
        outdir=outdir,
        preview=preview,
        verbose=verbose,
    )
    if res["status"] == "cancelled":
        raise_error("USR-001", "SEV3", "Operation cancelled by user", origin="run_job", err_type="User")
    if res["status"] == "error":
        err = res.get("error")
        if isinstance(err, CodedError):
            raise err
        raise_error("SYS-500", "SEV1", "Unhandled exception", details=str(err), origin="run_job", err_type="System")
    return res["counters"], res["outfile"], res["log_path"], res["warns_details"]


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

def parse_rules(path, return_meta=False):
    txt, _ = read_text(path)
    if not txt:
        raise_error("VAL-001", "SEV3", "Rules file is empty", origin="parse_rules", err_type="Validation")
    delim = detect_delimiter(txt[0])
    reader = csv.DictReader(txt, delimiter=delim)
    # Validar encabezados requeridos
    required_headers = {"action", "table", "mandt", "agr_name", "field"}
    present = {(h or "").strip().lstrip("\ufeff").lower() for h in (reader.fieldnames or [])}
    missing = sorted(required_headers - present)
    if missing:
        raise_error("VAL-003", "SEV2", f"Missing required columns: {', '.join(missing)}", origin="parse_rules", err_type="Validation")
    rules = []
    roles_touched = set()
    tables_touched = set()
    for i, row in enumerate(reader, start=2):  # start at data row
        norm = {(k or "").strip().lstrip("\ufeff").lower(): (v or "").strip() for k, v in row.items()}
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
        if role:
            roles_touched.add(role.strip())
        if table:
            tables_touched.add(table.strip())
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
    meta = {
        "delimiter_detected": delim,
        "rules_stats": {
            "rows_total_including_header": len(txt),
            "rules_loaded": len(rules),
            "roles_unique": len(roles_touched),
            "tables_touched": sorted(tables_touched),
            "required_columns_ok": True,
        },
    }
    if return_meta:
        return rules, meta
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


