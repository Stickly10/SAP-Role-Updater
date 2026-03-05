from __future__ import annotations

import pytest
from openpyxl import Workbook

from sap_role_updater.core.processor import parse_rules, split_pairs
from sap_role_updater.utils.error_handler import CodedError


def _write_rules(path, rows, *, sheet_name="RULES"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    sheet.append(["ACTION", "TABLE", "MANDT", "AGR_NAME", "OBJECT", "AUTH", "FIELD", "LOW", "HIGH"])
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def test_split_pairs_preserves_mixed_ranges():
    assert split_pairs("*|/*|0*|A*", "||9*|Z*") == [("*", ""), ("/*", ""), ("0*", "9*"), ("A*", "Z*")]


def test_split_pairs_rejects_high_without_low():
    with pytest.raises(CodedError) as exc:
        split_pairs("", "9*", {"row": 2, "table": "AGR_1252", "role": "ZROLE", "field": "$WERKS"})
    assert exc.value.code == "VAL-002"


def test_parse_rules_supports_rules_sheet(tmp_path):
    rules_path = tmp_path / "RULES.xlsx"
    _write_rules(
        rules_path,
        [["replace_list", "AGR_1252", "100", "ZROLE_FIXTURE_01", "", "", "$WERKS", "0*", "9*"]],
    )
    rules, meta = parse_rules(str(rules_path), return_meta=True)
    assert len(rules) == 1
    assert meta["rules_sheet_detected"] == "RULES"
    assert not meta["has_validation_errors"]


def test_parse_rules_reports_invalid_mandt(tmp_path):
    rules_path = tmp_path / "RULES.xlsx"
    _write_rules(rules_path, [["replace_list", "AGR_1252", "90", "ZROLE_FIXTURE_01", "", "", "$WERKS", "0*", "9*"]])
    _, meta = parse_rules(str(rules_path), return_meta=True)
    codes = {issue["code"] for issue in meta["validation_issues"]}
    assert "VAL-MANDT-FORMAT" in codes
    assert meta["has_validation_errors"]


def test_parse_rules_uses_first_sheet_when_rules_missing(tmp_path):
    rules_path = tmp_path / "RULES.xlsx"
    _write_rules(
        rules_path,
        [["replace_list", "AGR_1251", "100", "ZROLE_FIXTURE_01", "S_RFC", "T-BD08132800", "RFC_NAME", "*", ""]],
        sheet_name="INPUT",
    )
    rules, meta = parse_rules(str(rules_path), return_meta=True)
    assert len(rules) == 1
    assert meta["rules_sheet_detected"] == "INPUT"
