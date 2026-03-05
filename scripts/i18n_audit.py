#!/usr/bin/env python3
"""Heuristic audit to find GUI string literals that may bypass i18n."""

from __future__ import annotations

import ast
from pathlib import Path

GUI_ROOT = Path(__file__).resolve().parents[1] / "src" / "sap_role_updater" / "gui"
IGNORED_LITERALS = {"", "...", "?", "✅", "⚠", "⏳", "🌙", "☀"}


class LiteralVisitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.findings: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "t":
            return
        visible_text_targets = {
            "setText",
            "setTitle",
            "setPlaceholderText",
            "setToolTip",
            "setAccessibleName",
            "setAccessibleDescription",
            "addItem",
        }
        func_name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
        if func_name not in visible_text_targets:
            self.generic_visit(node)
            return
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                text = arg.value.strip()
                if text and text not in IGNORED_LITERALS and len(text) > 3:
                    self.findings.append((node.lineno, text))
        self.generic_visit(node)


def main():
    findings: list[tuple[str, int, str]] = []
    for py_file in sorted(GUI_ROOT.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8-sig"))
        visitor = LiteralVisitor(py_file)
        visitor.visit(tree)
        for line_no, text in visitor.findings:
            findings.append((str(py_file.relative_to(GUI_ROOT.parents[1])), line_no, text))

    filtered = []
    for file_name, line_no, text in findings:
        if text.startswith("#") or text.startswith("Q"):
            continue
        filtered.append((file_name, line_no, text))

    if not filtered:
        print("i18n-audit: no suspicious GUI string literals found")
        return

    print("i18n-audit: review these literals")
    for file_name, line_no, text in filtered:
        print(f"{file_name}:{line_no}: {text}")


if __name__ == "__main__":
    main()
