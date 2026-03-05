from __future__ import annotations

from pathlib import Path

from sap_role_updater.core.processor import build_output_paths, run_job_ex

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_build_output_paths_handles_base_without_extension(tmp_path):
    outfile, log_path = build_output_paths("Roles_EXT_BASE", str(tmp_path))
    assert outfile.endswith("Roles_EXT_BASE_MOD")
    assert log_path.endswith("Roles_EXT_BASE_MOD_LOG.txt")


def test_build_output_paths_handles_sap_extension(tmp_path):
    outfile, log_path = build_output_paths("Roles_EXT_BASE.sap", str(tmp_path))
    assert outfile.endswith("Roles_EXT_BASE_MOD.sap")
    assert log_path.endswith("Roles_EXT_BASE_MOD_LOG.txt")


def test_preview_does_not_write_files(tmp_path):
    base = FIXTURES / "base_agr1252.txt"
    rules = FIXTURES / "rules_agr1252.csv"
    res = run_job_ex(str(base), str(rules), str(tmp_path), preview=True)
    assert res["status"] == "ok"
    assert res["outfile"] == ""
    assert res["log_path"] == ""
    assert res["meta_path"] == ""
    assert list(tmp_path.iterdir()) == []


def test_cancellation_returns_without_outputs(tmp_path):
    base = FIXTURES / "base_agr1252.txt"
    rules_path = tmp_path / "RULES.csv"
    rules_path.write_text(
        (
            "ACTION,TABLE,MANDT,AGR_NAME,OBJECT,AUTH,FIELD,LOW,HIGH\n"
            "replace_list,AGR_1252,100,ZROLE_FIXTURE_01,,,$WERKS,0*,9*\n"
            "replace_list,AGR_1252,100,ZROLE_FIXTURE_01,,,$WERKS,A*,Z*\n"
        ),
        encoding="utf-8",
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
    rules = FIXTURES / "rules_agr1252.csv"
    res = run_job_ex(str(base), str(rules), str(tmp_path), preview=False)
    assert res["status"] == "ok"
    mod_lines = Path(res["outfile"]).read_text(encoding="utf-8").splitlines()
    assert len(mod_lines) == 2
    assert any("0*" in line for line in mod_lines)
    assert any("A*" in line for line in mod_lines)
    log_text = Path(res["log_path"]).read_text(encoding="utf-8")
    assert "REPLACE" in log_text
