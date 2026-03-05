#!/usr/bin/env python3
"""Light/Dark theme manager for PySide6 UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QApplication


class ThemeManager:
    @staticmethod
    def _resolve_app(app_or_window):
        if isinstance(app_or_window, QApplication):
            return app_or_window
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication instance not found")
        return app

    @staticmethod
    def apply_dark(app_or_window):
        app = ThemeManager._resolve_app(app_or_window)
        app.setStyle("Fusion")
        app.setFont(QFont("Segoe UI", 10))
        palette = QPalette()
        palette.setColor(QPalette.Window, Qt.black)
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, Qt.black)
        palette.setColor(QPalette.AlternateBase, Qt.black)
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, Qt.black)
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, Qt.blue)
        palette.setColor(QPalette.HighlightedText, Qt.white)
        app.setPalette(palette)
        app.setStyleSheet(
            """
            QMainWindow, QWidget { background-color: #1E1E1E; color: #E5E7EB; }
            QGroupBox { border: 1px solid #3F3F46; border-radius: 8px; margin-top: 12px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QLineEdit, QTableView { background: #111827; border: 1px solid #374151; border-radius: 6px; padding: 6px; }
            QTableView { gridline-color: #374151; selection-background-color: #1D4ED8; selection-color: #FFFFFF; }
            QPushButton { background: #374151; border: 1px solid #4B5563; border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background: #4B5563; }
            QPushButton#primaryButton { background: #2563EB; border-color: #2563EB; color: white; font-weight: 700; }
            QPushButton#primaryButton:hover { background: #1D4ED8; }
            QPushButton#cancelButton { background: #B91C1C; border-color: #B91C1C; color: white; font-weight: 700; }
            QHeaderView::section { background: #111827; border: 0; border-right: 1px solid #374151; border-bottom: 1px solid #374151; padding: 6px; }
            QTabBar::tab { background: #111827; border: 1px solid #374151; border-bottom: 0; padding: 8px 12px; margin-right: 3px; }
            QTabBar::tab:selected { background: #1F2937; }
            """
        )

    @staticmethod
    def apply_light(app_or_window):
        app = ThemeManager._resolve_app(app_or_window)
        app.setStyle("Fusion")
        app.setFont(QFont("Segoe UI", 10))
        palette = QPalette()
        palette.setColor(QPalette.Window, Qt.white)
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, Qt.white)
        palette.setColor(QPalette.AlternateBase, Qt.white)
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.Button, Qt.white)
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, Qt.blue)
        palette.setColor(QPalette.HighlightedText, Qt.white)
        app.setPalette(palette)
        app.setStyleSheet(
            """
            QMainWindow, QWidget { background-color: #F8FAFC; color: #0F172A; }
            QGroupBox { border: 1px solid #CBD5E1; border-radius: 8px; margin-top: 12px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QLineEdit, QTableView { background: #FFFFFF; border: 1px solid #94A3B8; border-radius: 6px; padding: 6px; color: #0F172A; }
            QTableView { gridline-color: #CBD5E1; selection-background-color: #2563EB; selection-color: #FFFFFF; }
            QPushButton { background: #E2E8F0; border: 1px solid #94A3B8; border-radius: 6px; padding: 6px 10px; color: #0F172A; }
            QPushButton:hover { background: #CBD5E1; }
            QPushButton#primaryButton { background: #2563EB; border-color: #1D4ED8; color: white; font-weight: 700; }
            QPushButton#primaryButton:hover { background: #1D4ED8; }
            QPushButton#cancelButton { background: #B91C1C; border-color: #991B1B; color: white; font-weight: 700; }
            QHeaderView::section { background: #F1F5F9; border: 0; border-right: 1px solid #CBD5E1; border-bottom: 1px solid #CBD5E1; padding: 6px; color: #0F172A; }
            QTabBar::tab { background: #E2E8F0; border: 1px solid #CBD5E1; border-bottom: 0; padding: 8px 12px; margin-right: 3px; color: #0F172A; }
            QTabBar::tab:selected { background: #FFFFFF; }
            """
        )

