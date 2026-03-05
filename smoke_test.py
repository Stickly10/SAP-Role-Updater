#!/usr/bin/env python3
"""Smoke tests for strict RULES.csv validation in preview mode."""

from __future__ import annotations

import csv
import os
import tempfile

from sap_role_updater_core import run_job_ex

HEADERS = ["ACTION", "TABLE", "MANDT", "AGR_NAME", "OBJECT", "AUTH", "FIELD", "LOW", "HIGH"]


def write_rules(path: str, row: dict):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerow(row)


def run_case(
    name: str,
    row: dict,
    expect_validation_error: bool,
    expected_codes: list[str] | None = None,
    *,
    redact_log: bool = False,
    write_meta: bool = False,
):
    with tempfile.TemporaryDirectory() as tmp:
        base_path = os.path.join(tmp, "Roles_EXT_BASE")
        rules_path = os.path.join(tmp, "RULES.csv")
        with open(base_path, "w", encoding="utf-8", newline="") as fh:
            fh.write("HEADER_LINE_NOT_TARGET_TABLE\n")
        write_rules(rules_path, row)

        res = run_job_ex(
            infile=base_path,
            rules_path=rules_path,
            preview=True,
            ui_sample_limit=20,
            redact_log=redact_log,
            write_meta=write_meta,
        )
        codes = {w.get("code", "") for w in res.get("warns_struct", [])}

        assert res["status"] == "ok", f"{name}: status inesperado {res['status']}"
        assert res["outfile"] == "", f"{name}: preview no debe generar outfile"
        assert res["log_path"] == "", f"{name}: preview no debe generar log_path"
        assert res.get("meta_path", "") == "", f"{name}: preview no debe generar meta_path"
        assert bool(res.get("has_validation_errors", False)) == expect_validation_error, (
            f"{name}: has_validation_errors esperado={expect_validation_error} actual={res.get('has_validation_errors')}"
        )
        if write_meta:
            assert res.get("checksums", {}).get("base_sha256"), f"{name}: falta checksum base"
            assert res.get("checksums", {}).get("rules_sha256"), f"{name}: falta checksum rules"
        if expected_codes:
            missing = [c for c in expected_codes if c not in codes]
            assert not missing, f"{name}: faltan codigos esperados {missing}, encontrados={sorted(codes)}"

        allowed = {"Roles_EXT_BASE", "RULES.csv"}
        generated = [f for f in os.listdir(tmp) if f not in allowed]
        assert not generated, f"{name}: preview genero archivos inesperados {generated}"
        print(f"[ok] {name}: has_validation_errors={res.get('has_validation_errors')} codes={sorted(codes)}")


def main():
    run_case(
        "valid_mandt_varbl",
        {
            "ACTION": "replace_list",
            "TABLE": "AGR_1252",
            "MANDT": "100",
            "AGR_NAME": "ZROLE_TEST_01",
            "OBJECT": "",
            "AUTH": "",
            "FIELD": "$WERKS",
            "LOW": "0*|A*",
            "HIGH": "9*|Z*",
        },
        expect_validation_error=False,
        redact_log=True,
        write_meta=True,
    )
    run_case(
        "invalid_mandt",
        {
            "ACTION": "replace_list",
            "TABLE": "AGR_1252",
            "MANDT": "90",
            "AGR_NAME": "ZROLE_TEST_01",
            "OBJECT": "",
            "AUTH": "",
            "FIELD": "$WERKS",
            "LOW": "0*",
            "HIGH": "9*",
        },
        expect_validation_error=True,
        expected_codes=["VAL-MANDT-FORMAT"],
    )
    run_case(
        "agr_name_with_space",
        {
            "ACTION": "replace_list",
            "TABLE": "AGR_1251",
            "MANDT": "100",
            "AGR_NAME": "Z ROLE TEST",
            "OBJECT": "S_RFC",
            "AUTH": "T-BD08132800",
            "FIELD": "RFC_NAME",
            "LOW": "*",
            "HIGH": "",
        },
        expect_validation_error=True,
        expected_codes=["VAL-AGRNAME-FORMAT"],
    )
    run_case(
        "varbl_without_dollar",
        {
            "ACTION": "replace_list",
            "TABLE": "AGR_1252",
            "MANDT": "100",
            "AGR_NAME": "ZROLE_TEST_01",
            "OBJECT": "",
            "AUTH": "",
            "FIELD": "WERKS",
            "LOW": "0*",
            "HIGH": "9*",
        },
        expect_validation_error=True,
        expected_codes=["VAL-1252-VARBL-FORMAT"],
    )
    run_case(
        "low_token_too_long",
        {
            "ACTION": "replace_list",
            "TABLE": "AGR_1252",
            "MANDT": "100",
            "AGR_NAME": "ZROLE_TEST_01",
            "OBJECT": "",
            "AUTH": "",
            "FIELD": "$WERKS",
            "LOW": "A" * 41,
            "HIGH": "",
        },
        expect_validation_error=True,
        expected_codes=["VAL-LOWHIGH-LEN"],
    )
    print("Smoke tests passed.")


if __name__ == "__main__":
    main()
