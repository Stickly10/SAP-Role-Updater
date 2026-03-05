"""Core parsing, validation, and processing helpers."""

from sap_role_updater.core.processor import (
    build_entries,
    build_meta_path,
    build_output_paths,
    parse_entry_1251,
    parse_entry_1252,
    parse_rules,
    read_text,
    run_job,
    run_job_ex,
    split_pairs,
)

__all__ = [
    "build_entries",
    "build_meta_path",
    "build_output_paths",
    "parse_entry_1251",
    "parse_entry_1252",
    "parse_rules",
    "read_text",
    "run_job",
    "run_job_ex",
    "split_pairs",
]
