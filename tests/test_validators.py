from __future__ import annotations

import csv

import pytest

from sap_role_updater.core.processor import parse_rules, split_pairs
from sap_role_updater.utils.error_handler import CodedError


def _write_rules(path, rows, *, delimiter=",", bom=False):
    text_prefix = "\ufeff" if bom else ""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text_prefix)
        writer = csv.writer(fh, delimiter=delimiter)
        writer.writerow(["ACTION", "TABLE", "MANDT", "AGR_NAME", "OBJECT", "AUTH", "FIELD", "LOW", "HIGH"])
        writer.writerows(rows)


def test_split_pairs_preserves_mixed_ranges():
    assert split_pairs("*|/*|0*|A*", "||9*|Z*") == [("*", ""), ("/*", ""), ("0*", "9*"), ("A*", "Z*")]


def test_split_pairs_rejects_high_without_low():
    with pytest.raises(CodedError) as exc:
        split_pairs("", "9*", {"row": 2, "table": "AGR_1252", "role": "ZROLE", "field": "$WERKS"})
    assert exc.value.code == "VAL-002"


def test_parse_rules_supports_bom_and_semicolon(tmp_path):
    rules_path = tmp_path / "RULES.csv"
    _write_rules(
        rules_path,
        [["replace_list", "AGR_1252", "100", "ZROLE_FIXTURE_01", "", "", "$WERKS", "0*", "9*"]],
        delimiter=";",
        bom=True,
    )
    rules, meta = parse_rules(str(rules_path), return_meta=True)
    assert len(rules) == 1
    assert meta["delimiter_detected"] == ";"
    assert not meta["has_validation_errors"]


def test_parse_rules_reports_invalid_mandt(tmp_path):
    rules_path = tmp_path / "RULES.csv"
    _write_rules(rules_path, [["replace_list", "AGR_1252", "90", "ZROLE_FIXTURE_01", "", "", "$WERKS", "0*", "9*"]])
    _, meta = parse_rules(str(rules_path), return_meta=True)
    codes = {issue["code"] for issue in meta["validation_issues"]}
    assert "VAL-MANDT-FORMAT" in codes
    assert meta["has_validation_errors"]
