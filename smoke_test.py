#!/usr/bin/env python3
"""Simple smoke test for preview mode."""

import os

from sap_role_updater_core import run_job_ex


def main():
    base = os.environ.get("SAP_ROLE_BASE", "ZT_TEST_TXOOL_11")
    rules = os.environ.get("SAP_ROLE_RULES", "dist/RULES.csv")

    if not os.path.isfile(base) or not os.path.isfile(rules):
        print("Smoke test skipped.")
        print("Set env SAP_ROLE_BASE and SAP_ROLE_RULES to existing files, for example:")
        print("  SAP_ROLE_BASE=ZT_TEST_TXOOL_11")
        print("  SAP_ROLE_RULES=dist/RULES.csv")
        return

    res = run_job_ex(
        infile=base,
        rules_path=rules,
        preview=True,
        ui_sample_limit=20,
    )
    print(f"status={res['status']}")
    print(f"counters={res['counters']}")
    print(f"warns={len(res['warns_struct'])}")
    if res["sample_rows"]:
        print("sample first row:", res["sample_rows"][0])


if __name__ == "__main__":
    main()
