#!/usr/bin/env python3
# mod_agr1251 v3.0057 — Fixed‑width AGR_1251 prescriptive values modifier (ONLY AGR_1251)
#
# • Afecta exclusivamente a líneas AGR_1251 (no toca AGR_1252 en absoluto).
# • Reglas CSV con separador ; , o \t. Columnas admitidas (insensibles a may/min):
#   ACTION, TABLE(opc.), MANDT, AGR_NAME/ROLE, OBJECT/OBJCT, AUTH, FIELD,
#   LOW (o LIST), HIGH (opcional — ignorado en replace_list).
# • Acción soportada: replace_list → borra todas las líneas existentes que
#   coincidan por (MANDT, AGR_NAME, OBJECT, AUTH, FIELD) y recrea la lista
#   con los valores de LOW/LIST separados por "|" (de‑dupe conservando orden).
# • Preserva 1:1 TODAS las líneas del archivo de entrada que no sean AGR_1251.
# • Log CSV con encabezado: action,before,after.
#
# Uso:
#   python mod_agr1251_v3_0057_presc_only.py --in EXPORT.txt --rules RULES_PRESC.csv --out EXPORT_mod.txt

import argparse, csv, re
from collections import defaultdict

WIDTHS = {
    "mandt": 3, "role": 30, "seq": 6, "obj": 10, "auth": 12, "sp4": 4,
    "field": 10, "low": 40, "high": 40
}

# Regex que captura segmentos de ancho fijo preservando el gap tras AGR_1251
RX = re.compile(r'^(AGR_1251)(\s+)(\d{3})(.{30})(\d{6})(.{10})(.{12})\s{4}(.{10})(.{40})(.{40})(.*)$')


def read_text(path):
    """Lee texto con tolerancia de encoding y elimina CR/LF al final de cada línea."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return [ln.rstrip("\r\n") for ln in f.readlines()], enc
        except UnicodeDecodeError:
            continue
    # Último recurso: binario + decode con ignore
    with open(path, "rb") as f:
        data = f.read()
    return data.decode("latin-1", errors="ignore").splitlines(), "latin-1"


def detect_delimiter(header_line):
    if ";" in header_line and "," in header_line:
        return ";"  # preferir ;
    if ";" in header_line: return ";"
    if "," in header_line: return ","
    if "\t" in header_line: return "\t"
    return ";"


def parse_rules(path):
    txt, _ = read_text(path)
    if not txt:
        raise ValueError("Reglas vacías")
    delim = detect_delimiter(txt[0])
    reader = csv.DictReader(txt, delimiter=delim)
    rules = []
    for i, row in enumerate(reader, start=1):
        norm = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }
        action = (norm.get("action", "replace_list") or "replace_list").lower()
        mandt = norm.get("mandt", "")
        role  = norm.get("agr_name", "") or norm.get("role", "")
        obj   = norm.get("object", "") or norm.get("objct", "")
        auth  = norm.get("auth", "")
        field = norm.get("field", "")
        low   = norm.get("low", "")
        list_cell = norm.get("list", "")
        # Preferir LOW si viene, si no LIST
        raw_vals = low if low else list_cell
        # Aceptar separador | o ,
        parts = [p.strip() for p in re.split(r"[|,]", raw_vals) if p and p.strip()]
        # de‑dupe preservando orden
        seen = set(); dedup = []
        for v in parts:
            if v not in seen:
                seen.add(v); dedup.append(v)
        rules.append({
            "raw_index": i,
            "action": action,
            "mandt": mandt,
            "role": role,
            "obj": obj,
            "auth": auth,
            "field": field,
            "list": dedup,
        })
    return rules


def fmt_fixed(val, width):
    s = (val or "")
    if len(s) > width:
        return s[:width]
    return s.ljust(width)


def parse_entry(line):
    m = RX.match(line)
    if not m:
        return None
    return {
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


def compose_line(base, seq, field, low, high):
    parts = [
        base["prefix"],
        fmt_fixed(base["mandt"], WIDTHS["mandt"]),
        fmt_fixed(base["role"], WIDTHS["role"]),
        fmt_fixed(str(seq).rjust(WIDTHS["seq"], "0"), WIDTHS["seq"]),
        fmt_fixed(base["obj"], WIDTHS["obj"]),
        fmt_fixed(base["auth"], WIDTHS["auth"]),
        " " * WIDTHS["sp4"],
        fmt_fixed(field, WIDTHS["field"]),
        fmt_fixed(low, WIDTHS["low"]),
        fmt_fixed(high, WIDTHS["high"]),
        base["tail"],
    ]
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description="Modify AGR_1251 fixed-width exports based on rule CSV.")
    ap.add_argument("--in", dest="infile", required=True, help="Input role export file")
    ap.add_argument("--rules", dest="rules", required=True, help="Rules CSV")
    ap.add_argument("--out", dest="outfile", required=True, help="Output role export file (modified)")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    ap.add_argument("--verbose", dest="verbose", action="store_true", default=False)
    args = ap.parse_args()

    lines, enc = read_text(args.infile)
    entries = []
    for idx, ln in enumerate(lines):
        e = parse_entry(ln)
        if e:
            e["index"] = idx
            e["deleted"] = False
        entries.append(e)

    rules = parse_rules(args.rules)

    # Máximo seq por rol
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
        if r["action"] != "replace_list":
            warns += 1
            log_rows.append(["WARN-ACTION", f"Unsupported action: {r['action']}", ""])
            continue

        key = (fmt_fixed(r["mandt"], WIDTHS["mandt"]),
               fmt_fixed(r["role"], WIDTHS["role"]),
               fmt_fixed(r["obj"], WIDTHS["obj"]),
               fmt_fixed(r["auth"], WIDTHS["auth"]))
        field = fmt_fixed(r["field"], WIDTHS["field"]).strip()

        # Buscar exactamente en AGR_1251
        hits = []
        for e in entries:
            if not e or e.get("deleted"):
                continue
            if (e["mandt"], e["role"], e["obj"], e["auth"]) == key and e["field"].strip() == field:
                hits.append(e)

        if not hits:
            warns += 1
            log_rows.append(["WARN-NOBASE", f"No base lines for key={key} field={field}", ""])
            continue

        base = hits[0]

        # Marcar eliminaciones existentes
        for h in hits:
            h["deleted"] = True
            deletes += 1
            log_rows.append(["DELETE", h["raw"], ""])  # before

        # Generar nuevas líneas (una por valor)
        next_seq = role_to_maxseq[base["role"]] + 1
        for val in r["list"]:
            new_line = compose_line(base, next_seq, field, val, "")
            role_to_maxseq[base["role"]] = next_seq
            next_seq += 1
            adds += 1
            log_rows.append(["ADD", "", new_line])
            ne = parse_entry(new_line)
            ne["index"] = len(entries)
            ne["deleted"] = False
            entries.append(ne)

        replaces += 1

    # Construir salida (preserva 1:1 las líneas no-AGR_1251)
    out_lines = []
    for i, e in enumerate(entries):
        if e is None:
            out_lines.append(lines[i])  # línea original no-AGR_1251
        elif not e.get("deleted"):
            out_lines.append(e["raw"])

    if not args.dry_run:
        with open(args.outfile, "w", encoding=enc, newline="\n") as f:
            for ln in out_lines:
                f.write(ln + "\n")

    # Log CSV (3 columnas, sin CR/LF internos)
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
