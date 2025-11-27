#!/usr/bin/env python3
# mod_agr1252 v3.0053 — Fixed‑width AGR_1252 modifier (reglas fijas)
#
# FORMATO AGR_1252 (por línea)
#   TABLE(10="AGR_1252") + 40 espacios + MANDT(3) + ROLE(30) + SEQ(6)
#   + ORG_FIELD(10, p.ej. "$BUKRS") + 30 espacios + ORG_VALUE(<=4) + tail
#
# REGLAS (CSV) — columnas fijas (case‑insensitive):
#   ACTION, TABLE, MANDT, AGR_NAME, ORG_FIELD, LIST
#   - ACTION: solo "replace_list"
#   - TABLE: debe ser "AGR_1252" (si viene otra, se ignora la regla)
#   - LIST: valores separados por "|"; se deduplican conservando orden. Si LIST queda vacía,
#           el efecto es borrar todos los valores del ORG_FIELD indicado.
#
# LÓGICA
#   - Selección por clave (TABLE, MANDT, ROLE, ORG_FIELD)
#   - Para cada regla, borra todas las líneas actuales de ese ORG_FIELD y agrega las de LIST.
#   - El SEQ nuevo continúa desde el máximo SEQ existente del ROL (no renumera el resto del rol).
#   - Preserva 1:1 todas las líneas que no son AGR_1252.
#   - Log CSV (action,before,after) sin CR/LF internos.

import argparse, csv, re
from collections import defaultdict

WIDTHS = {
    "table": 10, "sp40": 40, "mandt": 3, "role": 30, "seq": 6,
    "org_field": 10, "sp30": 30, "org_value": 4
}

RX_1252 = re.compile(
    r'^(?P<table>.{10})(?P<sp40>\s{40})(?P<mandt>\d{3})(?P<role>.{30})(?P<seq>\d{6})'
    r'(?P<org_field>.{10})(?P<sp30>\s{30})(?P<org_value>.{0,4})(?P<tail>.*)$'
)

# ---------------- utils ----------------

def read_text(path):
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
    hl = header_line or ""
    if ";" in hl and "," in hl: return ";"
    if ";" in hl: return ";"
    if "," in hl: return ","
    if "\t" in hl: return "\t"
    return ";"


def fmt_fixed(val: str, width: int) -> str:
    s = (val or "")
    return s[:width] if len(s) > width else s.ljust(width)

# -------------- parse lines --------------

def parse_entry_1252(line):
    m = RX_1252.match(line)
    if not m: return None
    if m.group("table").strip() != "AGR_1252":
        return None
    return {
        "raw": line,
        "table": m.group("table"),
        "sp40": m.group("sp40"),
        "mandt": m.group("mandt"),
        "role": m.group("role"),
        "seq": m.group("seq"),
        "org_field": m.group("org_field"),
        "sp30": m.group("sp30"),
        "org_value": m.group("org_value"),
        "tail": m.group("tail"),
    }


def compose_line_1252(base, seq, org_field, org_value):
    return "".join([
        fmt_fixed("AGR_1252", WIDTHS["table"]),
        " " * WIDTHS["sp40"],
        fmt_fixed(base["mandt"], WIDTHS["mandt"]),
        fmt_fixed(base["role"], WIDTHS["role"]),
        fmt_fixed(str(seq).rjust(WIDTHS["seq"], "0"), WIDTHS["seq"]),
        fmt_fixed(org_field, WIDTHS["org_field"]),
        " " * WIDTHS["sp30"],
        fmt_fixed(org_value, WIDTHS["org_value"]),
        base.get("tail", ""),
    ])

# -------------- parse rules --------------

def parse_rules(path):
    txt, _ = read_text(path)
    if not txt: raise ValueError("Reglas vacías")
    delim = detect_delimiter(txt[0])
    reader = csv.DictReader(txt, delimiter=delim)

    # normalizar encabezados
    fieldmap = { (h or "").strip().lower(): h for h in reader.fieldnames or [] }
    required = ["action","table","mandt","agr_name","org_field","list"]
    for r in required:
        if r not in fieldmap:
            raise ValueError(f"Falta columna obligatoria en reglas: {r}")

    rules = []
    for i, row in enumerate(reader, start=2):  # desde fila 2 (tras encabezado)
        norm = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }
        action = norm.get("action","" ).lower()
        table  = norm.get("table" ,"" ).upper()
        mandt  = norm.get("mandt" ,"" )
        role   = norm.get("agr_name","" )
        org_f  = norm.get("org_field","" )
        list_vals = [x for x in (norm.get("list","" ) or "").split("|") if x != ""]
        # de-dupe preservando orden
        seen = set(); dedup = []
        for v in list_vals:
            if v not in seen:
                seen.add(v); dedup.append(v)
        rules.append({
            "row": i,
            "action": action,
            "table": table,
            "mandt": mandt,
            "role": role,
            "org_field": org_f,
            "list": dedup,
        })
    return rules

# --------------- main ----------------

def main():
    ap = argparse.ArgumentParser(description="Modify AGR_1252 fixed-width exports based on fixed rule CSV (replace_list).")
    ap.add_argument("--in", dest="infile", required=True, help="Input role export file")
    ap.add_argument("--rules", dest="rules", required=True, help="Rules CSV (ACTION,TABLE,MANDT,AGR_NAME,ORG_FIELD,LIST)")
    ap.add_argument("--out", dest="outfile", required=True, help="Output role export file (modified)")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    ap.add_argument("--verbose", dest="verbose", action="store_true", default=False)
    args = ap.parse_args()

    lines, enc = read_text(args.infile)
    entries = []
    for idx, ln in enumerate(lines):
        e = parse_entry_1252(ln)
        if e:
            e["index"] = idx
            e["deleted"] = False
        entries.append(e)  # None indica línea no-AGR_1252

    rules = parse_rules(args.rules)

    # máximo seq por rol
    role_to_maxseq = defaultdict(lambda: 0)
    for e in entries:
        if e:
            try:
                role_to_maxseq[e["role"]] = max(role_to_maxseq[e["role"]], int(e["seq"]))
            except ValueError:
                pass

    adds = deletes = replaces = warns = 0
    log_rows = []

    for r in rules:
        if r["table"] != "AGR_1252":
            warns += 1
            log_rows.append(["WARN-TABLE", f"Ignored table={r['table']}", ""])
            continue
        if r["action"] != "replace_list":
            warns += 1
            log_rows.append(["WARN-ACTION", f"Unsupported action: {r['action']}", ""])
            continue
        if not (r["mandt"] and r["role"] and r["org_field"]):
            warns += 1
            log_rows.append(["WARN-RULE", f"Missing mandt/agr_name/org_field at row {r['row']}", ""])
            continue

        key = (
            fmt_fixed("AGR_1252", WIDTHS["table"]),
            fmt_fixed(r["mandt"], WIDTHS["mandt"]),
            fmt_fixed(r["role"], WIDTHS["role"]),
            fmt_fixed(r["org_field"], WIDTHS["org_field"]) )

        # encontrar actuales a borrar
        hits = []
        for e in entries:
            if not e or e.get("deleted"): continue
            if (
                e["table"] == key[0] and e["mandt"] == key[1]
                and e["role"] == key[2] and e["org_field"] == key[3]
            ):
                hits.append(e)

        if not hits:
            warns += 1
            log_rows.append(["WARN-NOBASE", f"No base lines for key={key}", ""])
            continue

        base = hits[0]

        for h in hits:
            h["deleted"] = True
            deletes += 1
            log_rows.append(["DELETE", h["raw"], ""])  # before

        # agregar nuevas líneas
        next_seq = role_to_maxseq[base["role"]] + 1
        for val in r["list"]:
            new_line = compose_line_1252(base, next_seq, key[3], val)
            role_to_maxseq[base["role"]] = next_seq
            next_seq += 1
            adds += 1
            log_rows.append(["ADD", "", new_line])  # after
            ne = parse_entry_1252(new_line)
            ne["index"] = len(entries)
            ne["deleted"] = False
            entries.append(ne)

        replaces += 1

    # salida: preservar 1:1 líneas no AGR_1252
    out_lines = []
    for i, e in enumerate(entries):
        if e is None:
            out_lines.append(lines[i])
        elif not e.get("deleted"):
            out_lines.append(e["raw"])

    if not args.dry_run:
        with open(args.outfile, "w", encoding=enc, newline="\n") as f:
            for ln in out_lines:
                f.write(ln + "\n")

    # log CSV
    log_path = args.outfile + "_log.csv"
    with open(log_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["action","before","after"])
        for a,b,c in log_rows:
            w.writerow([
                a,
                (b or "").replace("\r"," ").replace("\n"," "),
                (c or "").replace("\r"," ").replace("\n"," ")
            ])

    print(f"[end] {'Dry-run, no file written.' if args.dry_run else 'Written: ' + args.outfile}")
    print(f"[summary] adds={adds} deletes={deletes} replaces={replaces} warns={warns}")
    print(f"[log] {log_path}")

if __name__ == "__main__":
    main()
