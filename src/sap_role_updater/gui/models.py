"""Reusable Qt models and worker objects for the desktop UI."""

from __future__ import annotations

import traceback

from PySide6.QtCore import (
    Property,
    QAbstractTableModel,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRectF,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QPushButton

from sap_role_updater.core.processor import run_job_ex
from sap_role_updater.gui.i18n import t


class MultiColumnFilterProxy(QSortFilterProxyModel):
    """Filter rows when any visible column matches the search expression."""

    def filterAcceptsRow(self, source_row, source_parent):  # noqa: N802
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
    """Simple table model backed by a list of dictionaries."""

    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.rows = []

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def refresh_headers(self):
        if self.columnCount() > 0:
            self.headerDataChanged.emit(Qt.Horizontal, 0, self.columnCount() - 1)

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
        if role in (Qt.DisplayRole, Qt.EditRole, Qt.ToolTipRole):
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return t(self.columns[section][1])
        return str(section + 1)


class JobWorker(QObject):
    """Run the core job in a background thread and emit progress safely."""

    progress = Signal(int, int, str, int)
    finished = Signal(dict)
    failed = Signal(str, str)

    def __init__(self, infile, rules_path, outdir, preview, ui_sample_limit=300, redact_log=False, write_meta=False):
        super().__init__()
        self.infile = infile
        self.rules_path = rules_path
        self.outdir = outdir
        self.preview = preview
        self.ui_sample_limit = ui_sample_limit
        self.redact_log = redact_log
        self.write_meta = write_meta
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
                redact_log=self.redact_log,
                write_meta=self.write_meta,
            )
            self.finished.emit(result)
        except Exception as ex:  # noqa: BLE001
            self.failed.emit(str(ex), traceback.format_exc())


class AnimatedToggle(QPushButton):
    """Animated on/off toggle used for theme switching."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(50, 24)
        self.setFlat(True)
        self._offset = 3.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def sync_position(self):
        self._offset = self.width() - self.height() + 3 if self.isChecked() else 3
        self.update()

    def _animate(self, _checked=None):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(self.width() - self.height() + 3 if self.isChecked() else 3)
        self._anim.start()

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)  # type: ignore[assignment]

    def paintEvent(self, event):  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        bg = QColor("#2563EB") if self.isChecked() else QColor("#94A3B8")
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        knob_d = rect.height() - 6
        knob_rect = QRectF(self._offset, 3, knob_d, knob_d)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(knob_rect)
