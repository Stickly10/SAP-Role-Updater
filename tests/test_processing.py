from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from sap_role_updater.core.processor import build_output_paths, run_job_ex

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _write_rules_xlsx(path: Path, rows: list[list[str]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "RULES"
    sheet.append(["ACTION", "TABLE", "MANDT", "AGR_NAME", "OBJECT", "AUTH", "FIELD", "LOW", "HIGH"])
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def test_build_output_paths_handles_base_without_extension(tmp_path):
    outfile, log_path = build_output_paths("Roles_EXT_BASE", str(tmp_path))
    assert outfile.endswith("Roles_EXT_BASE_MOD")
    assert log_path.endswith("Roles_EXT_BASE_MOD_LOG.csv")


def test_build_output_paths_handles_sap_extension(tmp_path):
    outfile, log_path = build_output_paths("Roles_EXT_BASE.sap", str(tmp_path))
    assert outfile.endswith("Roles_EXT_BASE_MOD.sap")
    assert log_path.endswith("Roles_EXT_BASE_MOD_LOG.csv")


def test_preview_does_not_write_files(tmp_path):
    base = FIXTURES / "base_agr1252.txt"
    rules = tmp_path / "RULES.xlsx"
    _write_rules_xlsx(
        rules,
        [["replace_list", "AGR_1252", "100", "ZROLE_FIXTURE_01", "", "", "$WERKS", "0*|A*", "9*|Z*"]],
    )
    res = run_job_ex(str(base), str(rules), str(tmp_path), preview=True)
    assert res["status"] == "ok"
    assert res["outfile"] == ""
    assert res["log_path"] == ""
    assert res["meta_path"] == ""
    assert sorted(path.name for path in tmp_path.iterdir()) == ["RULES.xlsx"]


def test_cancellation_returns_without_outputs(tmp_path):
    base = FIXTURES / "base_agr1252.txt"
    rules_path = tmp_path / "RULES.xlsx"
    _write_rules_xlsx(
        rules_path,
        [
            ["replace_list", "AGR_1252", "100", "ZROLE_FIXTURE_01", "", "", "$WERKS", "0*", "9*"],
            ["replace_list", "AGR_1252", "100", "ZROLE_FIXTURE_01", "", "", "$WERKS", "A*", "Z*"],
        ],
    )
    calls = {"count": 0}

    def cancel_after_first_rule():
        calls["count"] += 1
        return calls["count"] > 1

    res = run_job_ex(str(base), str(rules_path), str(tmp_path), preview=False, is_cancelled=cancel_after_first_rule)
    assert res["status"] == "cancelled"
    assert res["outfile"] == ""
    assert res["log_path"] == ""


def test_process_generates_expected_mod_and_log(tmp_path):
    base = FIXTURES / "base_agr1252.txt"
    rules = tmp_path / "RULES.xlsx"
    _write_rules_xlsx(
        rules,
        [["replace_list", "AGR_1252", "100", "ZROLE_FIXTURE_01", "", "", "$WERKS", "0*|A*", "9*|Z*"]],
    )
    res = run_job_ex(str(base), str(rules), str(tmp_path), preview=False)
    assert res["status"] == "ok"
    mod_lines = Path(res["outfile"]).read_text(encoding="utf-8").splitlines()
    assert len(mod_lines) == 2
    assert any("0*" in line for line in mod_lines)
    assert any("A*" in line for line in mod_lines)
    log_text = Path(res["log_path"]).read_text(encoding="utf-8")
    assert "action;before;after" in log_text
    assert "REPLACE" in log_text


def test_coverage_summary_marks_no_base(tmp_path):
    base = FIXTURES / "base_agr1252.txt"
    rules = tmp_path / "RULES.xlsx"
    _write_rules_xlsx(
        rules,
        [["replace_list", "AGR_1252", "100", "ZROLE_FIXTURE_01", "", "", "$VKORG", "0*", "9*"]],
    )
    res = run_job_ex(str(base), str(rules), str(tmp_path), preview=True)
    assert res["status"] == "ok"
    assert res["coverage_summary"]["total_rules"] == 1
    assert res["coverage_summary"]["no_base"] == 1
