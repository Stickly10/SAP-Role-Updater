#!/usr/bin/env python3
"""PySide6 GUI for SAP Role Updater."""

from __future__ import annotations

import os
import sys
import traceback

from PySide6.QtCore import QAbstractTableModel, QObject, QRegularExpression, QSortFilterProxyModel, Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from error_handler import CodedError
from sap_role_updater_core import build_entries, build_output_paths, parse_entry_1251, parse_entry_1252, parse_rules, read_text, run_job_ex


def _apply_dark_theme(app: QApplication):
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


class MultiColumnFilterProxy(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        expr = self.filterRegularExpression()
        if not expr.pattern():
            return True
        model = self.sourceModel()
        for col in range(model.columnCount()):
            idx = model.index(source_row, col, source_parent)
            text = str(model.data(idx, Qt.DisplayRole) or "")
            if expr.match(text).hasMatch():
                return True
        return False


class DictTableModel(QAbstractTableModel):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.rows = []

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=None):  # noqa: N802
        return len(self.rows)

    def columnCount(self, parent=None):  # noqa: N802
        return len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        key, _ = self.columns[index.column()]
        value = row.get(key, "")
        if role in (Qt.DisplayRole, Qt.EditRole):
            return str(value)
        if role == Qt.ToolTipRole:
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.columns[section][1]
        return str(section + 1)


class JobWorker(QObject):
    progress = Signal(int, int, str, int)
    finished = Signal(dict)
    failed = Signal(str, str)

    def __init__(self, infile, rules_path, outdir, preview, ui_sample_limit=300):
        super().__init__()
        self.infile = infile
        self.rules_path = rules_path
        self.outdir = outdir
        self.preview = preview
        self.ui_sample_limit = ui_sample_limit
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def run(self):
        try:
            def on_progress(current, total, message):
                total_safe = max(total, 1)
                percent = int((current / total_safe) * 100)
                self.progress.emit(current, total, message, percent)

            result = run_job_ex(
                infile=self.infile,
                rules_path=self.rules_path,
                outdir=self.outdir,
                preview=self.preview,
                ui_sample_limit=self.ui_sample_limit,
                progress_cb=on_progress,
                is_cancelled=lambda: self._cancel_requested,
            )
            self.finished.emit(result)
        except Exception as ex:  # noqa: BLE001
            self.failed.emit(str(ex), traceback.format_exc())


class MainWindow(QMainWindow):
    def __init__(self, version):
        super().__init__()
        self.version = version
        self.base_path = ""
        self.rules_path = ""
        self.outdir_path = ""
        self.current_outfile = ""
        self.current_log_path = ""
        self.last_result = None
        self._thread = None
        self._worker = None
        self._running_preview = False
        self.base_ok = False
        self.rules_ok = False
        self.rules_has_validation_errors = False
        self.last_result_has_validation_errors = False
        self.setWindowTitle(f"SAP Role Updater {version}")
        self.resize(1300, 860)
        self._build_ui()
        self._refresh_stepper()
        self._refresh_guardrails()

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        header = QFrame()
        header_layout = QVBoxLayout(header)
        title = QLabel(f"SAP Role Updater {self.version}")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        header_layout.addWidget(title)
        steps = QHBoxLayout()
        self.step_base = QLabel("\u2460 Base")
        self.step_rules = QLabel("\u2461 Reglas")
        self.step_out = QLabel("\u2462 Salida")
        self.step_run = QLabel("\u2463 Validar/Procesar")
        for w in (self.step_base, self.step_rules, self.step_out, self.step_run):
            w.setStyleSheet("padding: 4px 10px; border: 1px solid #374151; border-radius: 8px;")
            steps.addWidget(w)
        steps.addStretch(1)
        header_layout.addLayout(steps)
        layout.addWidget(header)

        self.base_edit, self.base_detail, self.base_indicator = self._add_path_group(
            layout,
            "Paso 1: Archivo Base (PFCG Mass Download)",
            self._pick_base,
            "\U0001F4C2",
        )
        self.rules_edit, self.rules_detail, self.rules_indicator = self._add_path_group(
            layout,
            "Paso 2: Reglas (CSV AGR_1251/AGR_1252)",
            self._pick_rules,
            "\U0001F4C2",
        )
        self.out_edit, self.out_detail, self.out_indicator = self._add_path_group(
            layout,
            "Paso 3: Carpeta de salida",
            self._pick_outdir,
            "\U0001F4C1",
        )

        actions = QHBoxLayout()
        self.btn_validate = QPushButton("Validar")
        self.btn_validate.clicked.connect(lambda: self._start_job(preview=True))
        self.btn_process = QPushButton("Procesar y generar _MOD")
        self.btn_process.setObjectName("primaryButton")
        self.btn_process.clicked.connect(lambda: self._start_job(preview=False))
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("cancelButton")
        self.btn_cancel.clicked.connect(self._cancel_job)
        self.btn_cancel.setVisible(False)
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.status_label = QLabel("Listo.")
        actions.addWidget(self.btn_validate)
        actions.addWidget(self.btn_process)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.progress, 1)
        actions.addWidget(self.status_label, 2)
        layout.addLayout(actions)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._build_summary_tab()
        self._build_warns_tab()
        self._build_changes_tab()

        footer = QHBoxLayout()
        self.btn_open_outdir = QPushButton("Abrir carpeta salida")
        self.btn_open_outdir.clicked.connect(lambda: self._open_local(self.outdir_path))
        self.btn_open_log = QPushButton("Abrir log")
        self.btn_open_log.clicked.connect(lambda: self._open_local(self.current_log_path))
        self.btn_open_outdir.setEnabled(False)
        self.btn_open_log.setEnabled(False)
        footer.addStretch(1)
        footer.addWidget(self.btn_open_outdir)
        footer.addWidget(self.btn_open_log)
        layout.addLayout(footer)

    def _add_path_group(self, parent_layout, title, browse_fn, icon_text):
        box = QGroupBox(title)
        lay = QGridLayout(box)
        edit = QLineEdit()
        edit.setReadOnly(True)
        btn = QPushButton(icon_text)
        btn.setFixedWidth(42)
        btn.clicked.connect(browse_fn)
        detail = QLabel("Sin seleccionar.")
        detail.setStyleSheet("color: #9CA3AF;")
        detail.setWordWrap(True)
        indicator = QLabel("⚠")
        indicator.setStyleSheet("font-size: 18px;")
        lay.addWidget(edit, 0, 0)
        lay.addWidget(btn, 0, 1)
        lay.addWidget(indicator, 0, 2)
        lay.addWidget(detail, 1, 0, 1, 3)
        parent_layout.addWidget(box)
        return edit, detail, indicator

    def _build_summary_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        counters = QHBoxLayout()
        self.lbl_adds = QLabel("Adds: 0")
        self.lbl_deletes = QLabel("Deletes: 0")
        self.lbl_replaces = QLabel("Replaces: 0")
        self.lbl_warns = QLabel("Warns: 0")
        self.lbl_errors = QLabel("Errores (SEV1/SEV2): 0")
        self.lbl_warnings = QLabel("Advertencias (SEV3): 0")
        for w in (self.lbl_adds, self.lbl_deletes, self.lbl_replaces, self.lbl_warns, self.lbl_errors, self.lbl_warnings):
            w.setStyleSheet("font-size: 18px; font-weight: 700;")
            counters.addWidget(w)
        counters.addStretch(1)
        lay.addLayout(counters)
        self.lbl_summary_state = QLabel("Sin ejecucion.")
        self.lbl_summary_state.setStyleSheet("font-size: 16px; font-weight: 700;")
        lay.addWidget(self.lbl_summary_state)
        self.lbl_base_stats = QLabel("Base: -")
        self.lbl_rules_stats = QLabel("Reglas: -")
        self.lbl_base_stats.setWordWrap(True)
        self.lbl_rules_stats.setWordWrap(True)
        lay.addWidget(self.lbl_base_stats)
        lay.addWidget(self.lbl_rules_stats)
        lay.addStretch(1)
        self.tabs.addTab(tab, "Resumen")

    def _build_warns_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        self.warn_search = QLineEdit()
        self.warn_search.setPlaceholderText("Buscar...")
        self.warn_model = DictTableModel(
            [
                ("code", "code"),
                ("severity", "severity"),
                ("row", "row"),
                ("table", "table"),
                ("role", "role"),
                ("field", "field"),
                ("detail", "detail"),
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
        lay.addWidget(self.warn_search)
        lay.addWidget(self.warn_table)
        self.tabs.addTab(tab, "Advertencias")

    def _build_changes_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        self.change_search = QLineEdit()
        self.change_search.setPlaceholderText("Buscar...")
        self.change_model = DictTableModel(
            [
                ("action", "action"),
                ("table", "table"),
                ("role", "role"),
                ("field_key", "field/key"),
                ("before", "before"),
                ("after", "after"),
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
        lay.addWidget(self.change_search)
        lay.addWidget(self.change_table)
        self.tabs.addTab(tab, "Cambios")

    def _filter_warns(self, text):
        self.warn_proxy.setFilterRegularExpression(QRegularExpression(text, QRegularExpression.CaseInsensitiveOption))

    def _filter_changes(self, text):
        self.change_proxy.setFilterRegularExpression(QRegularExpression(text, QRegularExpression.CaseInsensitiveOption))

    def _pick_base(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona archivo base", "", "All files (*)")
        if not path:
            return
        self.base_path = path
        self.base_edit.setText(path)
        if not self.outdir_path:
            self.outdir_path = os.path.dirname(path)
            self.out_edit.setText(self.outdir_path)
        self._analyze_base()
        self._refresh_guardrails()

    def _pick_rules(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona reglas", "", "CSV/TSV (*.csv *.tsv);;All files (*)")
        if not path:
            return
        self.rules_path = path
        self.rules_edit.setText(path)
        self.last_result = None
        self.last_result_has_validation_errors = False
        self._analyze_rules()
        self._refresh_guardrails()

    def _pick_outdir(self):
        path = QFileDialog.getExistingDirectory(self, "Selecciona carpeta de salida")
        if not path:
            return
        self.outdir_path = path
        self.out_edit.setText(path)
        self._refresh_output_details()
        self._refresh_guardrails()

    def _analyze_base(self):
        try:
            lines, enc = read_text(self.base_path)
            entries = build_entries(lines)
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
                f"encoding={enc} | total_lineas={len(lines)} | roles_unicos={len(roles)} | AGR_1251={c1251} | AGR_1252={c1252}"
            )
            self.base_ok = True
            self.base_indicator.setText("✅")
        except Exception as ex:  # noqa: BLE001
            self.base_ok = False
            self.base_indicator.setText("⚠")
            self.base_detail.setText(f"Error leyendo base: {ex}")
        self._refresh_stepper()

    def _analyze_rules(self):
        try:
            _, meta = parse_rules(self.rules_path, return_meta=True)
            rs = meta.get("rules_stats", {})
            val_errs = int(rs.get("validation_errors", 0))
            self.rules_has_validation_errors = bool(meta.get("has_validation_errors", False))
            tables = ", ".join(rs.get("tables_touched", [])) or "-"
            self.rules_detail.setText(
                "delimiter={delim} | filas={rows} | roles_unicos={roles} | tablas={tables} | columnas_ok={cols} | errores_validacion={errs}".format(
                    delim=meta.get("delimiter_detected", ""),
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
            self.rules_detail.setText(f"Error leyendo reglas: {ex}")
        self._refresh_stepper()

    def _refresh_output_details(self):
        if not self.base_path or not self.outdir_path:
            self.out_detail.setText("Selecciona base + carpeta salida para ver nombres esperados.")
            self.out_indicator.setText("⚠")
            return
        out_file, log_file = build_output_paths(self.base_path, self.outdir_path)
        self.out_detail.setText(f"Salida esperada: {os.path.basename(out_file)} | Log: {os.path.basename(log_file)}")
        writable = os.path.isdir(self.outdir_path) and os.access(self.outdir_path, os.W_OK)
        self.out_indicator.setText("✅" if writable else "⚠")

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
        run_ok = self.last_result is not None and self.last_result.get("status") == "ok"
        self.step_base.setText(f"1 Base {'✅' if base_ok else '⚠'}")
        self.step_rules.setText(f"2 Reglas {'✅' if rules_ok else '⚠'}")
        self.step_out.setText(f"3 Salida {'✅' if out_ok else '⚠'}")
        self.step_run.setText(f"4 Validar/Procesar {'✅' if run_ok else '⏳'}")

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
        box.setWindowTitle("Advertencias detectadas")
        box.setText(f"Hay {warns} advertencias. Se recomienda corregir antes de cargar a SAP. ¿Deseas continuar?")
        box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Yes)
        box.setDefaultButton(QMessageBox.Cancel)
        cancel_btn = box.button(QMessageBox.Cancel)
        yes_btn = box.button(QMessageBox.Yes)
        if cancel_btn:
            cancel_btn.setText("Cancelar")
        if yes_btn:
            yes_btn.setText("Continuar")
        return box.exec() == QMessageBox.Yes

    def _start_job(self, preview):
        if self._thread is not None:
            return
        if preview and not self._can_validate():
            QMessageBox.warning(self, "Validacion", "Selecciona base y reglas validas antes de validar.")
            return
        if not preview and (self.rules_has_validation_errors or self.last_result_has_validation_errors):
            QMessageBox.warning(
                self,
                "Procesar",
                "No se puede procesar: RULES.csv tiene errores de validacion. Revisa la pestana Advertencias.",
            )
            return
        if not preview and not self._can_process():
            QMessageBox.warning(self, "Procesar", "Selecciona base, reglas y carpeta de salida escribible.")
            return
        if not preview and not self._confirm_warns_before_process():
            return

        self._running_preview = preview
        self.status_label.setText("Iniciando...")
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
        for button in self.findChildren(QPushButton):
            if button in (self.btn_cancel, self.btn_validate, self.btn_process, self.btn_open_outdir, self.btn_open_log):
                continue
            button.setEnabled(enabled)
        self.btn_validate.setEnabled(enabled and self._can_validate())
        self.btn_process.setEnabled(enabled and self._can_process())

    def _cancel_job(self):
        if self._worker:
            self._worker.request_cancel()
            self.status_label.setText("Cancelacion solicitada...")
            self.btn_cancel.setEnabled(False)

    def _on_worker_progress(self, current, total, message, percent):
        self.progress.setValue(percent)
        self.status_label.setText(message)

    def _on_worker_failed(self, error, tb):
        QMessageBox.critical(self, "Error", f"{error}\n\n{tb}")

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
        warns_struct = result.get("warns_struct", [])
        errors_count = sum(1 for item in warns_struct if item.get("severity") in ("SEV1", "SEV2"))
        warnings_count = sum(1 for item in warns_struct if item.get("severity") == "SEV3")
        self.lbl_adds.setText(f"Adds: {counters.get('adds', 0)}")
        self.lbl_deletes.setText(f"Deletes: {counters.get('deletes', 0)}")
        self.lbl_replaces.setText(f"Replaces: {counters.get('replaces', 0)}")
        self.lbl_warns.setText(f"Warns: {warns}")
        self.lbl_errors.setText(f"Errores (SEV1/SEV2): {errors_count}")
        self.lbl_warnings.setText(f"Advertencias (SEV3): {warnings_count}")

        base_stats = result.get("base_stats", {})
        rules_stats = result.get("rules_stats", {})
        self.lbl_base_stats.setText(
            "Base: encoding={enc}, lineas={lines}, roles={roles}, AGR_1251={c1}, AGR_1252={c2}".format(
                enc=result.get("encoding_detected", ""),
                lines=base_stats.get("total_lines", 0),
                roles=base_stats.get("roles_unique", 0),
                c1=base_stats.get("agr_1251_lines", 0),
                c2=base_stats.get("agr_1252_lines", 0),
            )
        )
        self.lbl_rules_stats.setText(
            "Reglas: delimiter={delim}, reglas={rules}, roles={roles}, tablas={tables}".format(
                delim=result.get("delimiter_detected", ""),
                rules=rules_stats.get("rules_loaded", 0),
                roles=rules_stats.get("roles_unique", 0),
                tables=", ".join(rules_stats.get("tables_touched", [])) or "-",
            )
        )

        self.warn_model.set_rows(warns_struct)
        self.change_model.set_rows(self._build_change_rows(result.get("sample_rows", [])))

        if status == "cancelled":
            self.lbl_summary_state.setText("⚠ Cancelado. No se escribieron archivos.")
            self.status_label.setText("Cancelado por usuario.")
        elif status == "error":
            err = result.get("error")
            msg = f"{getattr(err, 'code', 'ERR')}: {getattr(err, 'message', str(err))}"
            self.lbl_summary_state.setText(f"⚠ Error: {msg}")
            self.status_label.setText("Error.")
            QMessageBox.critical(self, "Error", msg)
        else:
            if errors_count > 0:
                self.lbl_summary_state.setText("❌ Reglas inválidas: corrige RULES.csv antes de procesar")
            elif warns > 0:
                self.lbl_summary_state.setText("⚠ Revisar advertencias antes de cargar a SAP")
            else:
                self.lbl_summary_state.setText("✅ Listo (sin advertencias)")
            if not self._running_preview:
                self.current_outfile = result.get("outfile", "")
                self.current_log_path = result.get("log_path", "")
            self.status_label.setText("Finalizado.")

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


def launch_gui(version):
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    _apply_dark_theme(app)
    win = MainWindow(version)
    win.show()
    if owns_app:
        return app.exec()
    return 0

