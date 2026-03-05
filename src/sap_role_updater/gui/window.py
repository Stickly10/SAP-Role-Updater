#!/usr/bin/env python3
"""PySide6 GUI for SAP Role Updater."""

from __future__ import annotations

import csv
import difflib
import html
import os
import sys
from pathlib import Path

from PySide6.QtCore import (
    QRegularExpression,
    QSettings,
    QSize,
    Qt,
    QThread,
    QUrl,
)
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStyle,
    QTableView,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sap_role_updater.core.processor import (
    build_entries,
    build_entry_indexes,
    build_output_paths,
    parse_entry_1251,
    parse_entry_1252,
    parse_rules,
    read_text,
)
from sap_role_updater.gui.i18n import detect_system_language, load_locales, set_language, t
from sap_role_updater.gui.models import AnimatedToggle, DictTableModel, JobWorker, MultiColumnFilterProxy
from sap_role_updater.gui.theme import ThemeManager
from sap_role_updater.utils.error_handler import CodedError
from sap_role_updater.utils.path_safety import is_unc_path, resolve_output_dir, resolve_regular_file
from sap_role_updater.utils.settings import APP_SETTINGS_NAME, APP_SETTINGS_ORG, DEFAULT_LIMITS, resource_path


class MainWindow(QMainWindow):
    def __init__(self, version, initial_language=None):
        super().__init__()
        load_locales()
        self.settings = QSettings(APP_SETTINGS_ORG, APP_SETTINGS_NAME)
        saved_lang = (self.settings.value("language", "", type=str) or "").strip().lower()
        lang = initial_language or saved_lang or detect_system_language(default="es")
        set_language(lang)
        self.version = version
        self.base_path = ""
        self.rules_path = ""
        self.outdir_path = ""
        self.current_outfile = ""
        self.current_log_path = ""
        self.current_meta_path = ""
        self.last_result = None
        self._thread = None
        self._worker = None
        self._running_preview = False
        self.base_ok = False
        self.rules_ok = False
        self.rules_has_validation_errors = False
        self.last_result_has_validation_errors = False
        self._suppress_result_dialog = False
        self._last_diff_pair = ("", "")
        self.setWindowTitle(t("app.window_title", version=version))
        self._apply_window_icon()
        self.resize(1300, 860)
        self._build_ui()
        saved_theme = (self.settings.value("theme", "dark", type=str) or "dark").strip().lower()
        self.toggle_dark.blockSignals(True)
        self.toggle_dark.setChecked(saved_theme != "light")
        self.toggle_dark.blockSignals(False)
        self.toggle_dark.sync_position()
        self._apply_theme(save=False)
        self._set_language_combo(lang)
        self.retranslate_ui()
        self._refresh_stepper()
        self._refresh_guardrails()

    def _apply_window_icon(self):
        icon_path = resource_path("SAP-Role-Updater-Logo.ico")
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            self.setWindowIcon(icon)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(icon)

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        header = QFrame()
        header_layout = QVBoxLayout(header)
        top = QHBoxLayout()
        self.title = QLabel()
        self.title.setStyleSheet("font-size: 20px; font-weight: 700;")
        self.lbl_language = QLabel()
        self.cmb_language = QComboBox()
        self.cmb_language.addItem("", "es")
        self.cmb_language.addItem("", "en")
        self.cmb_language.currentIndexChanged.connect(self._on_language_changed)
        self.lbl_theme_icon = QLabel()
        self.toggle_dark = AnimatedToggle()
        self.toggle_dark.toggled.connect(self._on_theme_toggled)
        self.lbl_theme = QLabel()
        self.btn_help = QPushButton("?")
        self.btn_help.setFixedWidth(30)
        self.btn_help.clicked.connect(self._show_help)
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.lbl_language)
        top.addWidget(self.cmb_language)
        top.addSpacing(12)
        top.addWidget(self.lbl_theme_icon)
        top.addWidget(self.toggle_dark)
        top.addWidget(self.lbl_theme)
        top.addSpacing(8)
        top.addWidget(self.btn_help)
        header_layout.addLayout(top)
        steps = QHBoxLayout()
        self.step_base = QLabel("1")
        self.step_rules = QLabel("2")
        self.step_out = QLabel("3")
        self.step_validate = QLabel("4")
        self.step_process = QLabel("5")
        for w in (self.step_base, self.step_rules, self.step_out, self.step_validate, self.step_process):
            w.setStyleSheet("padding: 4px 10px; border: 1px solid #374151; border-radius: 8px;")
            steps.addWidget(w)
        steps.addStretch(1)
        header_layout.addLayout(steps)
        layout.addWidget(header)

        self.base_group, self.base_edit, self.base_detail, self.base_indicator, self.base_btn = self._add_path_group(
            layout,
            self._pick_base,
            QStyle.SP_DialogOpenButton,
        )
        (
            self.rules_group,
            self.rules_edit,
            self.rules_detail,
            self.rules_indicator,
            self.rules_btn,
        ) = self._add_path_group(layout, self._pick_rules, QStyle.SP_DialogOpenButton)
        self.out_group, self.out_edit, self.out_detail, self.out_indicator, self.out_btn = self._add_path_group(
            layout,
            self._pick_outdir,
            QStyle.SP_DirOpenIcon,
        )

        actions = QHBoxLayout()
        self.btn_validate = QPushButton()
        self.btn_validate.clicked.connect(lambda: self._start_job(preview=True))
        self.btn_process = QPushButton()
        self.btn_process.setObjectName("primaryButton")
        self.btn_process.clicked.connect(lambda: self._start_job(preview=False))
        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("cancelButton")
        self.btn_cancel.clicked.connect(self._cancel_job)
        self.btn_cancel.setVisible(False)
        self.chk_redact_log = QCheckBox()
        self.chk_redact_log.setChecked(self.settings.value("redact_log", False, type=bool))
        self.chk_redact_log.toggled.connect(lambda val: self.settings.setValue("redact_log", bool(val)))
        self.chk_write_meta = QCheckBox()
        self.chk_write_meta.setChecked(self.settings.value("write_meta", False, type=bool))
        self.chk_write_meta.toggled.connect(lambda val: self.settings.setValue("write_meta", bool(val)))
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.status_label = QLabel()
        actions.addWidget(self.btn_validate)
        actions.addWidget(self.btn_process)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.chk_redact_log)
        actions.addWidget(self.chk_write_meta)
        actions.addWidget(self.progress, 1)
        actions.addWidget(self.status_label, 2)
        layout.addLayout(actions)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._build_summary_tab()
        self._build_warns_tab()
        self._build_changes_tab()
        self._build_coverage_tab()
        self._configure_tables()

        footer = QHBoxLayout()
        self.btn_open_outdir = QPushButton()
        self.btn_open_outdir.clicked.connect(lambda: self._open_local(self.outdir_path))
        self.btn_open_log = QPushButton()
        self.btn_open_log.clicked.connect(lambda: self._open_local(self.current_log_path))
        self.btn_open_outdir.setEnabled(False)
        self.btn_open_log.setEnabled(False)
        footer.addStretch(1)
        footer.addWidget(self.btn_open_outdir)
        footer.addWidget(self.btn_open_log)
        layout.addLayout(footer)
        self._configure_accessibility()
        self._configure_tab_order()

    def _add_path_group(self, parent_layout, browse_fn, icon_kind):
        box = QGroupBox()
        lay = QGridLayout(box)
        edit = QLineEdit()
        edit.setReadOnly(True)
        btn = QPushButton()
        btn.setFixedWidth(42)
        btn.setIconSize(QSize(18, 18))
        icon = self.style().standardIcon(icon_kind)
        btn.setIcon(icon)
        if icon.isNull():
            btn.setText("...")
        btn.clicked.connect(browse_fn)
        detail = QLabel(t("detail.not_selected"))
        detail.setStyleSheet("color: #9CA3AF;")
        detail.setWordWrap(True)
        indicator = QLabel("⚠")
        indicator.setStyleSheet("font-size: 18px;")
        lay.addWidget(edit, 0, 0)
        lay.addWidget(btn, 0, 1)
        lay.addWidget(indicator, 0, 2)
        lay.addWidget(detail, 1, 0, 1, 3)
        parent_layout.addWidget(box)
        return box, edit, detail, indicator, btn

    def _make_metric_card(self, parent_layout, object_name):
        card = QFrame()
        card.setObjectName("metricCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        value = QLabel("0")
        value.setObjectName("metricValue")
        caption = QLabel("")
        caption.setObjectName("metricCaption")
        caption.setWordWrap(True)
        card_layout.addWidget(value)
        card_layout.addWidget(caption)
        parent_layout.addWidget(card)
        setattr(self, f"{object_name}_value", value)
        setattr(self, f"{object_name}_caption", caption)

    def _build_summary_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        for object_name in ("adds", "deletes", "replaces"):
            self._make_metric_card(row1, object_name)
        for object_name in ("warns", "errors", "warnings"):
            self._make_metric_card(row2, object_name)
        lay.addLayout(row1)
        lay.addLayout(row2)
        self.summary_banner = QFrame()
        self.summary_banner.setObjectName("stateBanner")
        banner_layout = QHBoxLayout(self.summary_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        self.lbl_summary_state = QLabel()
        self.lbl_summary_state.setObjectName("stateBannerLabel")
        banner_layout.addWidget(self.lbl_summary_state)
        banner_layout.addStretch(1)
        lay.addWidget(self.summary_banner)
        self.lbl_base_stats = QLabel()
        self.lbl_rules_stats = QLabel()
        self.lbl_coverage_stats = QLabel()
        self.lbl_hashes = QLabel()
        self.lbl_meta = QLabel()
        self.lbl_base_stats.setWordWrap(True)
        self.lbl_rules_stats.setWordWrap(True)
        self.lbl_coverage_stats.setWordWrap(True)
        self.lbl_hashes.setWordWrap(True)
        self.lbl_meta.setWordWrap(True)
        lay.addWidget(self.lbl_base_stats)
        lay.addWidget(self.lbl_rules_stats)
        lay.addWidget(self.lbl_coverage_stats)
        lay.addWidget(self.lbl_hashes)
        lay.addWidget(self.lbl_meta)
        lay.addStretch(1)
        self.tabs.addTab(tab, "")

    def _build_warns_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        search_row = QHBoxLayout()
        self.warn_search = QLineEdit()
        self.warn_search.setClearButtonEnabled(True)
        self.warn_search.setPlaceholderText(t("search.placeholder"))
        self.warn_count = QLabel()
        self.warn_count.setObjectName("subtleLabel")
        search_row.addWidget(self.warn_search, 1)
        search_row.addWidget(self.warn_count)
        self.warn_model = DictTableModel(
            [
                ("code", "col.code"),
                ("severity", "col.severity"),
                ("row", "col.row"),
                ("table", "col.table"),
                ("role", "col.role"),
                ("field", "col.field"),
                ("detail", "col.detail"),
            ]
        )
        self.warn_proxy = MultiColumnFilterProxy(self)
        self.warn_proxy.setSourceModel(self.warn_model)
        self.warn_search.textChanged.connect(self._filter_warns)
        self.warn_table = QTableView()
        self.warn_table.setModel(self.warn_proxy)
        self.warn_table.setSortingEnabled(True)
        self.warn_table.horizontalHeader().setStretchLastSection(True)
        self.warn_table.setWordWrap(True)
        self.warn_empty = QLabel()
        self.warn_empty.setObjectName("subtleLabel")
        self.warn_empty.setWordWrap(True)
        lay.addLayout(search_row)
        lay.addWidget(self.warn_empty)
        lay.addWidget(self.warn_table)
        self.tabs.addTab(tab, "")

    def _build_changes_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        search_row = QHBoxLayout()
        self.change_search = QLineEdit()
        self.change_search.setClearButtonEnabled(True)
        self.change_search.setPlaceholderText(t("search.placeholder"))
        self.change_count = QLabel()
        self.change_count.setObjectName("subtleLabel")
        search_row.addWidget(self.change_search, 1)
        search_row.addWidget(self.change_count)
        self.change_model = DictTableModel(
            [
                ("action", "col.action"),
                ("table", "col.table"),
                ("role", "col.role"),
                ("field_key", "col.field_key"),
                ("before", "col.before"),
                ("after", "col.after"),
            ]
        )
        self.change_proxy = MultiColumnFilterProxy(self)
        self.change_proxy.setSourceModel(self.change_model)
        self.change_search.textChanged.connect(self._filter_changes)
        self.change_table = QTableView()
        self.change_table.setModel(self.change_proxy)
        self.change_table.setSortingEnabled(True)
        self.change_table.horizontalHeader().setStretchLastSection(True)
        self.change_table.setWordWrap(True)
        self.change_table.selectionModel().selectionChanged.connect(self._on_change_selection_changed)
        self.change_empty = QLabel()
        self.change_empty.setObjectName("subtleLabel")
        self.change_empty.setWordWrap(True)
        diff_splitter = QSplitter(Qt.Vertical)
        diff_top = QWidget()
        diff_top_layout = QVBoxLayout(diff_top)
        diff_top_layout.setContentsMargins(0, 0, 0, 0)
        diff_top_layout.addWidget(self.change_table)
        diff_bottom = QWidget()
        diff_bottom_layout = QVBoxLayout(diff_bottom)
        diff_bottom_layout.setContentsMargins(0, 0, 0, 0)
        diff_toolbar = QHBoxLayout()
        self.lbl_diff_title = QLabel()
        self.btn_copy_before = QPushButton()
        self.btn_copy_after = QPushButton()
        self.btn_copy_before.clicked.connect(
            lambda: QApplication.clipboard().setText(self.change_before_text.toPlainText())
        )
        self.btn_copy_after.clicked.connect(
            lambda: QApplication.clipboard().setText(self.change_after_text.toPlainText())
        )
        diff_toolbar.addWidget(self.lbl_diff_title)
        diff_toolbar.addStretch(1)
        diff_toolbar.addWidget(self.btn_copy_before)
        diff_toolbar.addWidget(self.btn_copy_after)
        self.diff_split = QSplitter(Qt.Horizontal)
        before_panel = QWidget()
        before_layout = QVBoxLayout(before_panel)
        before_layout.setContentsMargins(0, 0, 0, 0)
        self.change_before_label = QLabel()
        self.change_before_text = QTextEdit()
        self.change_before_text.setReadOnly(True)
        before_layout.addWidget(self.change_before_label)
        before_layout.addWidget(self.change_before_text)
        after_panel = QWidget()
        after_layout = QVBoxLayout(after_panel)
        after_layout.setContentsMargins(0, 0, 0, 0)
        self.change_after_label = QLabel()
        self.change_after_text = QTextEdit()
        self.change_after_text.setReadOnly(True)
        after_layout.addWidget(self.change_after_label)
        after_layout.addWidget(self.change_after_text)
        self.diff_split.addWidget(before_panel)
        self.diff_split.addWidget(after_panel)
        self.diff_split.setStretchFactor(0, 1)
        self.diff_split.setStretchFactor(1, 1)
        diff_bottom_layout.addLayout(diff_toolbar)
        diff_bottom_layout.addWidget(self.diff_split)
        diff_splitter.addWidget(diff_top)
        diff_splitter.addWidget(diff_bottom)
        diff_splitter.setStretchFactor(0, 2)
        diff_splitter.setStretchFactor(1, 1)
        lay.addLayout(search_row)
        lay.addWidget(self.change_empty)
        lay.addWidget(diff_splitter)
        self._clear_diff_view()
        self.tabs.addTab(tab, "")

    def _build_coverage_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        top = QHBoxLayout()
        self.coverage_search = QLineEdit()
        self.coverage_search.setClearButtonEnabled(True)
        self.coverage_search.setPlaceholderText(t("search.placeholder"))
        self.coverage_count = QLabel()
        self.coverage_count.setObjectName("subtleLabel")
        self.btn_export_coverage = QPushButton()
        self.btn_export_coverage.clicked.connect(self._export_coverage_csv)
        top.addWidget(self.coverage_search, 1)
        top.addWidget(self.coverage_count)
        top.addWidget(self.btn_export_coverage)
        self.coverage_model = DictTableModel(
            [
                ("row", "col.row"),
                ("status", "col.status"),
                ("table", "col.table"),
                ("role", "col.role"),
                ("field", "col.field"),
                ("object", "col.object"),
                ("auth", "col.auth"),
                ("matched", "col.matched"),
                ("deleted", "col.deleted"),
                ("added", "col.added"),
                ("reason", "col.reason"),
            ]
        )
        self.coverage_proxy = MultiColumnFilterProxy(self)
        self.coverage_proxy.setSourceModel(self.coverage_model)
        self.coverage_search.textChanged.connect(self._filter_coverage)
        self.coverage_table = QTableView()
        self.coverage_table.setModel(self.coverage_proxy)
        self.coverage_table.setSortingEnabled(True)
        self.coverage_empty = QLabel()
        self.coverage_empty.setObjectName("subtleLabel")
        self.coverage_empty.setWordWrap(True)
        lay.addLayout(top)
        lay.addWidget(self.coverage_empty)
        lay.addWidget(self.coverage_table)
        self.tabs.addTab(tab, "")

    def _configure_tables(self):
        for table in (self.warn_table, self.change_table, self.coverage_table):
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QTableView.SelectRows)
            table.setSelectionMode(QTableView.SingleSelection)
            table.setShowGrid(False)
            table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        warn_header = self.warn_table.horizontalHeader()
        for col in range(6):
            warn_header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        warn_header.setSectionResizeMode(6, QHeaderView.Stretch)
        change_header = self.change_table.horizontalHeader()
        for col in range(4):
            change_header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        change_header.setSectionResizeMode(4, QHeaderView.Stretch)
        change_header.setSectionResizeMode(5, QHeaderView.Stretch)
        coverage_header = self.coverage_table.horizontalHeader()
        for col in range(10):
            coverage_header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        coverage_header.setSectionResizeMode(10, QHeaderView.Stretch)

    def _configure_accessibility(self):
        widgets = [
            (self.base_edit, "group.base", "tt.pick_base"),
            (self.base_btn, "group.base", "tt.pick_base"),
            (self.rules_edit, "group.rules", "tt.pick_rules"),
            (self.rules_btn, "group.rules", "tt.pick_rules"),
            (self.out_edit, "group.output", "tt.pick_output"),
            (self.out_btn, "group.output", "tt.pick_output"),
            (self.cmb_language, "header.language", "tt.language"),
            (self.toggle_dark, "theme.dark_mode", "tt.theme_toggle"),
            (self.btn_help, "help.title", "tt.help"),
            (self.btn_validate, "btn.validate", "tt.validate"),
            (self.btn_process, "btn.process", "tt.process"),
            (self.btn_cancel, "btn.cancel", "tt.cancel"),
            (self.chk_redact_log, "opt.redact_log", "tt.redact_log"),
            (self.chk_write_meta, "opt.write_meta", "tt.write_meta"),
            (self.warn_search, "tab.warns", "search.placeholder"),
            (self.change_search, "tab.changes", "search.placeholder"),
            (self.coverage_search, "tab.coverage", "search.placeholder"),
            (self.warn_table, "tab.warns", "tab.warns"),
            (self.change_table, "tab.changes", "tab.changes"),
            (self.coverage_table, "tab.coverage", "tab.coverage"),
            (self.btn_export_coverage, "btn.export_csv", "tt.export_coverage"),
            (self.btn_copy_before, "btn.copy_before", "tt.copy_before"),
            (self.btn_copy_after, "btn.copy_after", "tt.copy_after"),
        ]
        for widget, name_key, desc_key in widgets:
            widget.setAccessibleName(t(name_key))
            widget.setAccessibleDescription(t(desc_key))

    def _configure_tab_order(self):
        tab_sequence = [
            self.cmb_language,
            self.toggle_dark,
            self.btn_help,
            self.base_btn,
            self.rules_btn,
            self.out_btn,
            self.btn_validate,
            self.btn_process,
            self.chk_redact_log,
            self.chk_write_meta,
            self.warn_search,
            self.change_search,
            self.coverage_search,
            self.btn_export_coverage,
            self.btn_copy_before,
            self.btn_copy_after,
            self.btn_open_outdir,
            self.btn_open_log,
        ]
        for current, nxt in zip(tab_sequence, tab_sequence[1:], strict=False):
            self.setTabOrder(current, nxt)
        QShortcut(QKeySequence("F1"), self, activated=self._show_help)
        QShortcut(QKeySequence("F5"), self, activated=lambda: self._start_job(preview=True))
        QShortcut(QKeySequence("F6"), self, activated=lambda: self._start_job(preview=False))
        QShortcut(QKeySequence("Escape"), self, activated=self._cancel_job)

    def _set_language_combo(self, lang_code):
        idx = self.cmb_language.findData(lang_code)
        if idx < 0:
            idx = self.cmb_language.findData("es")
        self.cmb_language.blockSignals(True)
        self.cmb_language.setCurrentIndex(max(idx, 0))
        self.cmb_language.blockSignals(False)

    def _refresh_theme_toggle(self):
        dark = self.toggle_dark.isChecked()
        self.lbl_theme_icon.setText("🌙" if dark else "☀")
        self.lbl_theme.setText(t("theme.dark_mode"))
        self.toggle_dark.setToolTip(t("theme.dark_icon") if dark else t("theme.light_icon"))
        self.lbl_theme_icon.setToolTip(self.toggle_dark.toolTip())

    def _apply_theme(self, save=True):
        if self.toggle_dark.isChecked():
            ThemeManager.apply_dark(QApplication.instance())
            if save:
                self.settings.setValue("theme", "dark")
        else:
            ThemeManager.apply_light(QApplication.instance())
            if save:
                self.settings.setValue("theme", "light")
        self._refresh_theme_toggle()

    def _on_theme_toggled(self, _checked=None):
        self._apply_theme(save=True)

    def _show_help(self):
        QMessageBox.information(self, t("help.title"), t("help.body"))

    def _on_language_changed(self):
        code = self.cmb_language.currentData()
        set_language(code)
        self.settings.setValue("language", code)
        self.retranslate_ui()
        self._refresh_guardrails()

    def retranslate_ui(self):
        self.setWindowTitle(t("app.window_title", version=self.version))
        self.title.setText(t("app.window_title", version=self.version))
        self.lbl_language.setText(t("header.language"))
        self.lbl_theme.setText(t("theme.dark_mode"))
        self.cmb_language.setItemText(0, t("header.lang.es"))
        self.cmb_language.setItemText(1, t("header.lang.en"))
        self.base_group.setTitle(t("group.base"))
        self.rules_group.setTitle(t("group.rules"))
        self.out_group.setTitle(t("group.output"))
        self.btn_validate.setText(t("btn.validate"))
        self.btn_process.setText(t("btn.process"))
        self.btn_cancel.setText(t("btn.cancel"))
        self.chk_redact_log.setText(t("opt.redact_log"))
        self.chk_write_meta.setText(t("opt.write_meta"))
        self.btn_open_outdir.setText(t("btn.open_output"))
        self.btn_open_log.setText(t("btn.open_log"))
        self.warn_search.setPlaceholderText(t("search.placeholder"))
        self.change_search.setPlaceholderText(t("search.placeholder"))
        self.coverage_search.setPlaceholderText(t("search.placeholder"))
        self.tabs.setTabText(0, t("tab.summary"))
        self.adds_caption.setText(t("metric.adds"))
        self.deletes_caption.setText(t("metric.deletes"))
        self.replaces_caption.setText(t("metric.replaces"))
        self.warns_caption.setText(t("metric.warns"))
        self.errors_caption.setText(t("metric.errors"))
        self.warnings_caption.setText(t("metric.warnings"))
        self.warn_empty.setText(t("empty.warns"))
        self.change_empty.setText(t("empty.changes"))
        self.coverage_empty.setText(t("empty.coverage"))
        self.btn_export_coverage.setText(t("btn.export_csv"))
        self.lbl_diff_title.setText(t("diff.title"))
        self.change_before_label.setText(t("diff.before"))
        self.change_after_label.setText(t("diff.after"))
        self.btn_copy_before.setText(t("btn.copy_before"))
        self.btn_copy_after.setText(t("btn.copy_after"))
        self.warn_model.refresh_headers()
        self.change_model.refresh_headers()
        self.coverage_model.refresh_headers()
        self._refresh_theme_toggle()
        self._refresh_stepper()
        self._apply_tooltips()
        self._configure_accessibility()
        if not self.base_path:
            self.base_detail.setText(t("detail.not_selected"))
        if not self.rules_path:
            self.rules_detail.setText(t("detail.not_selected"))
        if self.last_result is None:
            self.status_label.setText(t("status.ready"))
            self._set_summary_defaults()
        else:
            self._suppress_result_dialog = True
            self._on_worker_finished(self.last_result)
            self._suppress_result_dialog = False
        self._refresh_result_counts()

    def _apply_tooltips(self):
        self.cmb_language.setToolTip(t("tt.language"))
        self.toggle_dark.setToolTip(t("tt.theme_toggle"))
        self.btn_help.setToolTip(t("tt.help"))
        self.base_btn.setToolTip(t("tt.pick_base"))
        self.rules_btn.setToolTip(t("tt.pick_rules"))
        self.out_btn.setToolTip(t("tt.pick_output"))
        self.btn_validate.setToolTip(t("tt.validate"))
        self.btn_process.setToolTip(t("tt.process"))
        self.btn_cancel.setToolTip(t("tt.cancel"))
        self.btn_open_outdir.setToolTip(t("tt.open_output"))
        self.btn_open_log.setToolTip(t("tt.open_log"))
        self.chk_redact_log.setToolTip(t("tt.redact_log"))
        self.chk_write_meta.setToolTip(t("tt.write_meta"))
        self.warn_search.setToolTip(t("tt.search_warns"))
        self.change_search.setToolTip(t("tt.search_changes"))
        self.coverage_search.setToolTip(t("tt.search_coverage"))
        self.btn_export_coverage.setToolTip(t("tt.export_coverage"))
        self.btn_copy_before.setToolTip(t("tt.copy_before"))
        self.btn_copy_after.setToolTip(t("tt.copy_after"))
        self.base_edit.setToolTip(self.base_path)
        self.rules_edit.setToolTip(self.rules_path)
        self.out_edit.setToolTip(self.outdir_path)

    def _set_summary_defaults(self):
        self.adds_value.setText("0")
        self.deletes_value.setText("0")
        self.replaces_value.setText("0")
        self.warns_value.setText("0")
        self.errors_value.setText("0")
        self.warnings_value.setText("0")
        self.lbl_summary_state.setText(t("summary.state.idle"))
        self.lbl_base_stats.setText(t("summary.base", enc="-", lines=0, roles=0, c1=0, c2=0))
        self.lbl_rules_stats.setText(t("summary.rules", sheet="-", rules=0, roles=0, tables="-"))
        self.lbl_coverage_stats.setText(t("summary.coverage", total=0, applied=0, no_base=0, skipped=0, cancelled=0))
        self.lbl_hashes.clear()
        self.lbl_meta.clear()
        self._refresh_result_counts()

    def _filter_warns(self, text):
        self.warn_proxy.setFilterRegularExpression(QRegularExpression(text, QRegularExpression.CaseInsensitiveOption))
        self._refresh_result_counts()

    def _filter_changes(self, text):
        self.change_proxy.setFilterRegularExpression(QRegularExpression(text, QRegularExpression.CaseInsensitiveOption))
        self._refresh_result_counts()

    def _filter_coverage(self, text):
        self.coverage_proxy.setFilterRegularExpression(
            QRegularExpression(text, QRegularExpression.CaseInsensitiveOption)
        )
        self._refresh_result_counts()

    def _refresh_result_counts(self):
        warns_total = self.warn_model.rowCount()
        changes_total = self.change_model.rowCount()
        coverage_total = self.coverage_model.rowCount()
        warns_visible = self.warn_proxy.rowCount()
        changes_visible = self.change_proxy.rowCount()
        coverage_visible = self.coverage_proxy.rowCount()
        self.warn_count.setText(t("list.count", visible=warns_visible, total=warns_total))
        self.change_count.setText(t("list.count", visible=changes_visible, total=changes_total))
        self.coverage_count.setText(t("list.count", visible=coverage_visible, total=coverage_total))
        self.tabs.setTabText(1, t("tab.with_count", name=t("tab.warns"), count=warns_total))
        self.tabs.setTabText(2, t("tab.with_count", name=t("tab.changes"), count=changes_total))
        self.tabs.setTabText(3, t("tab.with_count", name=t("tab.coverage"), count=coverage_total))
        self.warn_empty.setVisible(warns_total == 0)
        self.change_empty.setVisible(changes_total == 0)
        self.coverage_empty.setVisible(coverage_total == 0)
        self.btn_export_coverage.setEnabled(coverage_total > 0)

    def _clear_diff_view(self):
        self._last_diff_pair = ("", "")
        empty_html = self._render_side_html("", [], before_side=True)
        self.change_before_text.setHtml(empty_html)
        self.change_after_text.setHtml(self._render_side_html("", [], before_side=False))

    def _diff_colors(self):
        if self.toggle_dark.isChecked():
            return {
                "bg": "#0F172A",
                "text": "#E5E7EB",
                "before": "#7F1D1D",
                "after": "#14532D",
                "replace": "#78350F",
            }
        return {
            "bg": "#FFFFFF",
            "text": "#0F172A",
            "before": "#FEE2E2",
            "after": "#DCFCE7",
            "replace": "#FEF3C7",
        }

    def _render_side_html(self, text, opcodes, *, before_side):
        colors = self._diff_colors()
        pieces = []
        for tag, a0, a1, b0, b1 in opcodes:
            if before_side:
                segment = text[a0:a1]
                if tag == "equal":
                    color = "transparent"
                elif tag == "delete":
                    color = colors["before"]
                elif tag == "replace":
                    color = colors["replace"]
                else:
                    continue
            else:
                segment = text[b0:b1]
                if tag == "equal":
                    color = "transparent"
                elif tag == "insert":
                    color = colors["after"]
                elif tag == "replace":
                    color = colors["replace"]
                else:
                    continue
            if not segment:
                continue
            pieces.append(f"<span style='background:{color};'>{html.escape(segment)}</span>")
        body = "".join(pieces) if pieces else html.escape(text)
        return (
            "<html><body style='background:{bg}; color:{text}; font-family:Consolas, monospace; "
            "font-size:12px; white-space:pre-wrap;'>"
            "{body}</body></html>"
        ).format(bg=colors["bg"], text=colors["text"], body=body)

    def _show_change_diff(self, before, after):
        pair = (before or "", after or "")
        if pair == self._last_diff_pair:
            return
        self._last_diff_pair = pair
        matcher = difflib.SequenceMatcher(a=pair[0], b=pair[1])
        opcodes = matcher.get_opcodes()
        self.change_before_text.setHtml(self._render_side_html(pair[0], opcodes, before_side=True))
        self.change_after_text.setHtml(self._render_side_html(pair[1], opcodes, before_side=False))

    def _on_change_selection_changed(self, *_args):
        index = self.change_table.currentIndex()
        if not index.isValid():
            self._clear_diff_view()
            return
        proxy_row = index.row()
        before = self.change_proxy.index(proxy_row, 4).data() or ""
        after = self.change_proxy.index(proxy_row, 5).data() or ""
        self._show_change_diff(before, after)

    def _export_proxy_to_csv(self, proxy, model, columns, path):
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow([t(header_key) for _, header_key in columns])
            for row_idx in range(proxy.rowCount()):
                source_row = proxy.mapToSource(proxy.index(row_idx, 0)).row()
                source_data = model.rows[source_row]
                values = []
                for col_idx, (key, _header_key) in enumerate(columns):
                    visible_value = proxy.index(row_idx, col_idx).data()
                    values.append(str(visible_value or source_data.get(key, "")))
                writer.writerow(values)

    def _export_coverage_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("dialog.export_coverage"),
            str(Path(self.outdir_path or os.getcwd()) / "coverage_report.csv"),
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            self._export_proxy_to_csv(self.coverage_proxy, self.coverage_model, self.coverage_model.columns, path)
            QMessageBox.information(self, t("dialog.export_title"), t("dialog.export_saved", path=Path(path).name))
        except Exception as ex:  # noqa: BLE001
            self._show_error_dialog(t("dialog.export_failed", error=str(ex)))

    def _pick_base(self):
        path, _ = QFileDialog.getOpenFileName(self, t("dialog.pick_base"), "", "All files (*)")
        if not path:
            return
        self.base_path = path
        self.base_edit.setText(path)
        self.base_edit.setToolTip(path)
        self.current_outfile = ""
        self.current_log_path = ""
        self.current_meta_path = ""
        if not self.outdir_path:
            self.outdir_path = os.path.dirname(path)
            self.out_edit.setText(self.outdir_path)
            self.out_edit.setToolTip(self.outdir_path)
        self._analyze_base()
        self._refresh_guardrails()

    def _pick_rules(self):
        path, _ = QFileDialog.getOpenFileName(self, t("dialog.pick_rules"), "", "Excel Rules (*.xlsx)")
        if not path:
            return
        self.rules_path = path
        self.rules_edit.setText(path)
        self.rules_edit.setToolTip(path)
        self.current_outfile = ""
        self.current_log_path = ""
        self.current_meta_path = ""
        self.last_result = None
        self.last_result_has_validation_errors = False
        self._analyze_rules()
        self._refresh_guardrails()

    def _pick_outdir(self):
        path = QFileDialog.getExistingDirectory(self, t("dialog.pick_outdir"))
        if not path:
            return
        self.outdir_path = path
        self.out_edit.setText(path)
        self.out_edit.setToolTip(path)
        self._refresh_output_details()
        self._refresh_guardrails()

    def _analyze_base(self):
        try:
            resolve_regular_file(
                self.base_path,
                label=t("sec.label.base"),
                max_size_mb=DEFAULT_LIMITS["base_size_mb"],
                max_lines=DEFAULT_LIMITS["base_lines"],
            )
            lines, enc = read_text(self.base_path)
            entries = build_entries(lines)
            indexes = build_entry_indexes(entries)
            roles = set()
            c1251 = 0
            c1252 = 0
            for e in entries:
                if not e:
                    continue
                if e.get("role", "").strip():
                    roles.add(e["role"].strip())
                if e["table_type"] == "AGR_1251":
                    c1251 += 1
                elif e["table_type"] == "AGR_1252":
                    c1252 += 1
            self.base_detail.setText(
                t(
                    "detail.base_stats",
                    enc=enc,
                    lines=len(lines),
                    roles=len(roles),
                    c1251=c1251,
                    c1252=c1252,
                    i1251=indexes["stats"]["agr_1251_keys"],
                    i1252=indexes["stats"]["agr_1252_keys"],
                )
            )
            self.base_ok = True
            self.base_indicator.setText("✅")
        except Exception as ex:  # noqa: BLE001
            self.base_ok = False
            self.base_indicator.setText("⚠")
            self.base_detail.setText(f"{t('dialog.error_title')}: {ex}")
        self._refresh_stepper()

    def _analyze_rules(self):
        try:
            resolve_regular_file(
                self.rules_path,
                label=t("sec.label.rules"),
                max_size_mb=DEFAULT_LIMITS["rules_size_mb"],
                max_lines=DEFAULT_LIMITS["rules_lines"],
            )
            _, meta = parse_rules(self.rules_path, return_meta=True)
            rs = meta.get("rules_stats", {})
            val_errs = int(rs.get("validation_errors", 0))
            self.rules_has_validation_errors = bool(meta.get("has_validation_errors", False))
            tables = ", ".join(rs.get("tables_touched", [])) or "-"
            self.rules_detail.setText(
                t(
                    "detail.rules_stats",
                    sheet=meta.get("rules_sheet_detected", "") or rs.get("sheet_name", ""),
                    rows=rs.get("rules_loaded", 0),
                    roles=rs.get("roles_unique", 0),
                    tables=tables,
                    cols=rs.get("required_columns_ok", False),
                    errs=val_errs,
                )
            )
            self.rules_ok = True
            self.rules_indicator.setText("⚠" if self.rules_has_validation_errors else "✅")
        except CodedError as ce:
            self.rules_ok = False
            self.rules_has_validation_errors = True
            self.rules_indicator.setText("⚠")
            self.rules_detail.setText(f"{ce.code}: {ce.message}")
        except Exception as ex:  # noqa: BLE001
            self.rules_ok = False
            self.rules_has_validation_errors = True
            self.rules_indicator.setText("⚠")
            self.rules_detail.setText(f"{t('dialog.error_title')}: {ex}")
        self._refresh_stepper()

    def _refresh_output_details(self):
        if not self.base_path or not self.outdir_path:
            self.out_detail.setText(t("detail.output_hint"))
            self.out_indicator.setText("⚠")
            return
        try:
            resolve_output_dir(self.outdir_path, label=t("sec.label.output"))
            out_file, log_file = build_output_paths(self.base_path, self.outdir_path)
            self.out_detail.setText(
                t("detail.output_expected", outfile=os.path.basename(out_file), logfile=os.path.basename(log_file))
            )
            self.out_indicator.setText("✅")
        except CodedError as ce:
            self.out_detail.setText(f"{ce.code}: {ce.message}")
            self.out_indicator.setText("⚠")

    def _refresh_guardrails(self):
        self._refresh_output_details()
        can_validate = self._can_validate()
        can_process = self._can_process()
        self.btn_validate.setEnabled(can_validate and self._thread is None)
        self.btn_process.setEnabled(can_process and self._thread is None)
        self.btn_open_outdir.setEnabled(bool(self.current_outfile))
        self.btn_open_log.setEnabled(bool(self.current_log_path))
        self._refresh_stepper()

    def _refresh_stepper(self):
        base_ok = self.base_ok and os.path.isfile(self.base_path)
        rules_ok = self.rules_ok and os.path.isfile(self.rules_path) and not self.rules_has_validation_errors
        out_ok = os.path.isdir(self.outdir_path) and os.access(self.outdir_path, os.W_OK)
        validate_ok = self.last_result is not None
        process_ok = bool(self.current_outfile) and os.path.isfile(self.current_outfile)
        self.step_base.setText(f"1 {t('header.step.base')} {'✅' if base_ok else '⚠'}")
        self.step_rules.setText(f"2 {t('header.step.rules')} {'✅' if rules_ok else '⚠'}")
        self.step_out.setText(f"3 {t('header.step.output')} {'✅' if out_ok else '⚠'}")
        self.step_validate.setText(f"4 {t('header.step.validate')} {'✅' if validate_ok else '⏳'}")
        self.step_process.setText(f"5 {t('header.step.process')} {'✅' if process_ok else '⏳'}")

    def _can_validate(self):
        return os.path.isfile(self.base_path) and os.path.isfile(self.rules_path) and self.base_ok and self.rules_ok

    def _can_process(self):
        return (
            self._can_validate()
            and os.path.isdir(self.outdir_path)
            and os.access(self.outdir_path, os.W_OK)
            and not self.rules_has_validation_errors
            and not self.last_result_has_validation_errors
        )

    def _confirm_warns_before_process(self):
        if not self.last_result:
            return True
        warns = int(self.last_result.get("counters", {}).get("warns", 0))
        if warns <= 0:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(t("dialog.warns_title"))
        box.setText(t("dialog.warns_text", warns=warns))
        box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Yes)
        box.setDefaultButton(QMessageBox.Cancel)
        cancel_btn = box.button(QMessageBox.Cancel)
        yes_btn = box.button(QMessageBox.Yes)
        if cancel_btn:
            cancel_btn.setText(t("dialog.cancel"))
        if yes_btn:
            yes_btn.setText(t("dialog.continue"))
        return box.exec() == QMessageBox.Yes

    def _confirm_network_paths(self):
        paths = [self.base_path, self.rules_path, self.outdir_path]
        if not any(path and is_unc_path(path) for path in paths):
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(t("dialog.netpath_title"))
        box.setText(t("dialog.netpath_text"))
        box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Yes)
        box.setDefaultButton(QMessageBox.Cancel)
        cancel_btn = box.button(QMessageBox.Cancel)
        yes_btn = box.button(QMessageBox.Yes)
        if cancel_btn:
            cancel_btn.setText(t("dialog.cancel"))
        if yes_btn:
            yes_btn.setText(t("dialog.continue"))
        return box.exec() == QMessageBox.Yes

    def _show_error_dialog(self, message, details=""):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle(t("dialog.error_title"))
        box.setText(message)
        if details:
            box.setDetailedText(details)
        box.exec()

    def _start_job(self, preview):
        if self._thread is not None:
            return
        if preview and not self._can_validate():
            QMessageBox.warning(self, t("dialog.validation_title"), t("dialog.validation_pick"))
            return
        if not preview and (self.rules_has_validation_errors or self.last_result_has_validation_errors):
            QMessageBox.warning(
                self,
                t("dialog.process_title"),
                t("dialog.process_rules_invalid"),
            )
            return
        if not preview and not self._can_process():
            QMessageBox.warning(self, t("dialog.process_title"), t("dialog.process_pick"))
            return
        if not preview and not self._confirm_network_paths():
            return
        if not preview and not self._confirm_warns_before_process():
            return

        self._running_preview = preview
        self.status_label.setText(t("status.starting"))
        self.progress.setValue(0)
        self.btn_cancel.setVisible(True)
        self.btn_cancel.setEnabled(True)
        self._set_inputs_enabled(False)

        self._thread = QThread(self)
        self._worker = JobWorker(
            infile=self.base_path,
            rules_path=self.rules_path,
            outdir=self.outdir_path if not preview else None,
            preview=preview,
            ui_sample_limit=300,
            redact_log=self.chk_redact_log.isChecked(),
            write_meta=self.chk_write_meta.isChecked(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _set_inputs_enabled(self, enabled):
        for edit in (self.base_edit, self.rules_edit, self.out_edit):
            edit.setEnabled(enabled)
        locked_buttons = (
            self.btn_cancel,
            self.btn_validate,
            self.btn_process,
            self.btn_open_outdir,
            self.btn_open_log,
        )
        for button in self.findChildren(QPushButton):
            if button in locked_buttons:
                continue
            button.setEnabled(enabled)
        self.cmb_language.setEnabled(enabled)
        self.toggle_dark.setEnabled(enabled)
        self.chk_redact_log.setEnabled(enabled)
        self.chk_write_meta.setEnabled(enabled)
        self.btn_validate.setEnabled(enabled and self._can_validate())
        self.btn_process.setEnabled(enabled and self._can_process())

    def _cancel_job(self):
        if self._worker:
            self._worker.request_cancel()
            self.status_label.setText(t("status.cancel_requested"))
            self.btn_cancel.setEnabled(False)

    def _on_worker_progress(self, current, total, message, percent):
        self.progress.setValue(percent)
        self.status_label.setText(message)

    def _on_worker_failed(self, error, tb):
        self._show_error_dialog(error, tb)

    def _translate_warns(self, warns_struct):
        out = []
        for item in warns_struct:
            row = dict(item)
            msg_id = row.get("msg_id", "")
            params = row.get("msg_params", {}) or {}
            if msg_id:
                row["detail"] = t(msg_id, **params)
            out.append(row)
        return out

    def _build_coverage_rows(self, coverage_rows):
        out = []
        for item in coverage_rows:
            row = dict(item)
            reason_msg_id = row.get("reason_msg_id", "")
            reason_params = row.get("reason_params", {}) or {}
            status_key = {
                "APPLIED": "coverage.status.applied",
                "NO_BASE": "coverage.status.no_base",
                "SKIPPED_ERROR": "coverage.status.skipped_error",
                "CANCELLED": "coverage.status.cancelled",
                "PENDING": "coverage.status.pending",
            }.get(row.get("status", ""), "coverage.status.pending")
            row["status"] = t(status_key)
            row["reason"] = t(reason_msg_id, **reason_params) if reason_msg_id else ""
            out.append(row)
        return out

    def _on_worker_finished(self, result):
        self.last_result = result
        status = result.get("status", "error")
        counters = result.get("counters", {})
        warns = int(counters.get("warns", 0))
        self.last_result_has_validation_errors = bool(result.get("has_validation_errors", False))
        if not self.last_result_has_validation_errors:
            for item in result.get("warns_struct", []):
                if item.get("severity") in ("SEV1", "SEV2"):
                    self.last_result_has_validation_errors = True
                    break
        warns_struct = self._translate_warns(result.get("warns_struct", []))
        errors_count = sum(1 for item in warns_struct if item.get("severity") in ("SEV1", "SEV2"))
        warnings_count = sum(1 for item in warns_struct if item.get("severity") == "SEV3")
        self.adds_value.setText(str(counters.get("adds", 0)))
        self.deletes_value.setText(str(counters.get("deletes", 0)))
        self.replaces_value.setText(str(counters.get("replaces", 0)))
        self.warns_value.setText(str(warns))
        self.errors_value.setText(str(errors_count))
        self.warnings_value.setText(str(warnings_count))

        base_stats = result.get("base_stats", {})
        rules_stats = result.get("rules_stats", {})
        self.lbl_base_stats.setText(
            t(
                "summary.base",
                enc=result.get("encoding_detected", ""),
                lines=base_stats.get("total_lines", 0),
                roles=base_stats.get("roles_unique", 0),
                c1=base_stats.get("agr_1251_lines", 0),
                c2=base_stats.get("agr_1252_lines", 0),
            )
        )
        self.lbl_rules_stats.setText(
            t(
                "summary.rules",
                sheet=result.get("rules_sheet_detected", "") or rules_stats.get("sheet_name", ""),
                rules=rules_stats.get("rules_loaded", 0),
                roles=rules_stats.get("roles_unique", 0),
                tables=", ".join(rules_stats.get("tables_touched", [])) or "-",
            )
        )
        coverage_summary = result.get("coverage_summary", {}) or {}
        self.lbl_coverage_stats.setText(
            t(
                "summary.coverage",
                total=coverage_summary.get("total_rules", 0),
                applied=coverage_summary.get("applied", 0),
                no_base=coverage_summary.get("no_base", 0),
                skipped=coverage_summary.get("skipped_error", 0),
                cancelled=coverage_summary.get("cancelled", 0),
            )
        )

        self.warn_model.set_rows(warns_struct)
        self.change_model.set_rows(self._build_change_rows(result.get("sample_rows", [])))
        self.coverage_model.set_rows(self._build_coverage_rows(result.get("coverage_rows", [])))
        if self.change_model.rowCount() == 0:
            self._clear_diff_view()
        self._refresh_result_counts()

        if status == "cancelled":
            self.lbl_summary_state.setText(t("summary.state.cancelled"))
            self.status_label.setText(t("status.cancelled"))
        elif status == "error":
            err = result.get("error")
            msg = f"{getattr(err, 'code', 'ERR')}: {getattr(err, 'message', str(err))}"
            self.lbl_summary_state.setText(t("summary.state.error", msg=msg))
            self.status_label.setText(t("status.error"))
            if not self._suppress_result_dialog:
                self._show_error_dialog(msg, getattr(err, "details", ""))
        else:
            if errors_count > 0:
                self.lbl_summary_state.setText(t("summary.state.invalid_rules"))
            elif warns > 0:
                self.lbl_summary_state.setText(t("summary.state.with_warns"))
            else:
                self.lbl_summary_state.setText(t("summary.state.ok"))
            if not self._running_preview:
                self.current_outfile = result.get("outfile", "")
                self.current_log_path = result.get("log_path", "")
                self.current_meta_path = result.get("meta_path", "")
            self.status_label.setText(t("status.finished"))

        checksums = result.get("checksums", {}) or {}
        if checksums:
            self.lbl_hashes.setText(
                t(
                    "summary.hashes",
                    base=checksums.get("base_sha256", "")[:12],
                    rules=checksums.get("rules_sha256", "")[:12],
                )
            )
        else:
            self.lbl_hashes.clear()
        if result.get("meta_path"):
            self.lbl_meta.setText(t("summary.meta", meta=Path(result["meta_path"]).name))
        else:
            self.lbl_meta.clear()

        self.btn_open_outdir.setEnabled(bool(self.current_outfile))
        self.btn_open_log.setEnabled(bool(self.current_log_path))
        self._refresh_stepper()

    def _cleanup_thread(self):
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        self.btn_cancel.setVisible(False)
        self.progress.setValue(0)
        self._set_inputs_enabled(True)
        self._refresh_guardrails()

    def _build_change_rows(self, sample_rows):
        out = []
        for row in sample_rows:
            action = row[0] if len(row) > 0 else ""
            before = row[1] if len(row) > 1 else ""
            after = row[2] if len(row) > 2 else ""
            src = before or after
            table = ""
            role = ""
            field_key = ""
            e1 = parse_entry_1251(src)
            if e1:
                table = e1["table"].strip()
                role = e1["role"].strip()
                field_key = f"{e1['object'].strip()}/{e1['auth'].strip()}/{e1['field'].strip()}"
            else:
                e2 = parse_entry_1252(src)
                if e2:
                    table = e2["table"].strip()
                    role = e2["role"].strip()
                    field_key = e2["varbl"].strip()
            out.append(
                {
                    "action": action,
                    "table": table,
                    "role": role,
                    "field_key": field_key,
                    "before": before,
                    "after": after,
                }
            )
        return out

    def _open_local(self, path):
        if not path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def launch_gui(version, lang_code=None):
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    icon_path = resource_path("SAP-Role-Updater-Logo.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow(version, initial_language=lang_code)
    win.show()
    if owns_app:
        return app.exec()
    return 0

