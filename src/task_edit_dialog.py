from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QHeaderView,
    QWidget,
)

from Task import Session, Task
from session_ops import coalesce_sessions, normalize_sessions


class TaskEditDialog(QDialog):
    DATETIME_FORMAT = "yyyy-MM-dd HH:mm"

    def __init__(self, task: Task, save_handler=None, move_handler=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.save_handler = save_handler
        self.move_handler = move_handler
        self.orig_rows = []
        self.setWindowTitle("Edit Task")
        self.resize(640, 360)

        layout = QVBoxLayout(self)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Task:"))
        self.name_input = QLineEdit(task.name)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        self.sessions_table = QTableWidget(0, 2, self)
        self.sessions_table.setHorizontalHeaderLabels(["Begin", "End"])
        self.sessions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sessions_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.sessions_table)

        button_row = QHBoxLayout()
        self.add_session_btn = QPushButton("Add Session")
        self.add_session_btn.clicked.connect(self.add_session_row)
        self.delete_session_btn = QPushButton("Delete Session")
        self.delete_session_btn.clicked.connect(self.delete_selected_sessions)
        self.coalesce_sessions_btn = QPushButton("Coalesce Selected Sessions")
        self.coalesce_sessions_btn.clicked.connect(self.coalesce_selected_sessions)
        self.move_sessions_btn = QPushButton("Move Selected Sessions")
        self.move_sessions_btn.clicked.connect(self.move_selected_sessions)
        button_row.addWidget(self.add_session_btn)
        button_row.addWidget(self.delete_session_btn)
        button_row.addWidget(self.coalesce_sessions_btn)
        button_row.addWidget(self.move_sessions_btn)
        button_row.addStretch()
        layout.addLayout(button_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate_sessions()
        self.sessions_table.selectionModel().selectionChanged.connect(self._refresh_action_buttons)

    def _populate_sessions(self):
        self.sessions_table.setRowCount(0)
        self.orig_rows = []
        for session in self.task.sessions:
            self._insert_session_row(session.begin, session.end, orig=(session.begin, session.end))
        self._refresh_open_controls()
        self._refresh_action_buttons()

    def _insert_session_row(self, begin=None, end=None, row=0, orig=(None, None)):
        if begin is None:
            begin = datetime.now()

        self.sessions_table.insertRow(row)
        self.orig_rows.insert(row, orig)
        begin_edit = self._create_datetime_edit(begin)
        self.sessions_table.setCellWidget(row, 0, begin_edit)
        self.sessions_table.setCellWidget(row, 1, self._create_end_editor(end))

    def add_session_row(self):
        self._insert_session_row()
        self.sessions_table.selectRow(0)
        self._refresh_open_controls()
        self._refresh_action_buttons()

    def delete_selected_sessions(self):
        selected_rows = sorted(self._selected_rows(), reverse=True)
        for row in selected_rows:
            self.sessions_table.removeRow(row)
            del self.orig_rows[row]
        self._refresh_open_controls()
        self._refresh_action_buttons()

    def coalesce_selected_sessions(self):
        selected_rows = sorted(self._selected_rows())
        if len(selected_rows) != 2:
            return

        first_row, second_row = selected_rows
        merged = coalesce_sessions(
            Session(begin=self._begin_value(first_row), end=self._end_value(first_row)),
            Session(begin=self._begin_value(second_row), end=self._end_value(second_row)),
        )

        for row in reversed(selected_rows):
            self.sessions_table.removeRow(row)
            del self.orig_rows[row]

        insert_row = min(selected_rows)
        self._insert_session_row(merged.begin, merged.end, insert_row)
        self.sessions_table.selectRow(insert_row)
        self._refresh_open_controls()
        self._refresh_action_buttons()

    def _create_datetime_edit(self, value):
        editor = QDateTimeEdit(self)
        editor.setDisplayFormat(self.DATETIME_FORMAT)
        editor.setCalendarPopup(True)
        editor.setDateTime(self._to_qdatetime(value))
        return editor

    def _create_end_editor(self, end):
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        end_edit = self._create_datetime_edit(end or datetime.now())
        open_checkbox = QCheckBox("Open", container)
        open_checkbox.setChecked(end is None)
        end_edit.setEnabled(end is not None)
        open_checkbox.toggled.connect(lambda checked, widget=end_edit: widget.setEnabled(not checked))

        layout.addWidget(end_edit)
        layout.addWidget(open_checkbox)
        return container

    def _refresh_open_controls(self):
        is_completed_task = self.task.completed_at is not None
        for row in range(self.sessions_table.rowCount()):
            container = self.sessions_table.cellWidget(row, 1)
            if container is None:
                continue

            end_edit = container.layout().itemAt(0).widget()
            open_checkbox = container.layout().itemAt(1).widget()
            is_top_row = row == 0 and not is_completed_task

            open_checkbox.setEnabled(is_top_row)
            open_checkbox.setVisible(is_top_row)
            if not is_top_row:
                open_checkbox.setChecked(False)
                end_edit.setEnabled(True)

    def _refresh_action_buttons(self, *_args):
        selected_count = len(self._selected_rows())
        self.delete_session_btn.setEnabled(selected_count > 0)
        self.coalesce_sessions_btn.setEnabled(selected_count == 2)
        self.move_sessions_btn.setEnabled(self.move_handler is not None and selected_count > 0)

    def _selected_rows(self):
        return {index.row() for index in self.sessions_table.selectionModel().selectedRows()}

    def _to_qdatetime(self, value):
        return QDateTime(
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
        )

    def _snap_min(self, value):
        if value is None:
            return value
        return value.replace(second=0, microsecond=0)

    def _same_min(self, left, right):
        return self._snap_min(left) == self._snap_min(right)

    def _begin_value(self, row):
        editor = self.sessions_table.cellWidget(row, 0)
        value = editor.dateTime().toPython()
        orig, _ = self.orig_rows[row]
        if orig is not None and self._same_min(value, orig):
            return orig
        return self._snap_min(value)

    def _end_value(self, row):
        container = self.sessions_table.cellWidget(row, 1)
        end_edit = container.layout().itemAt(0).widget()
        open_checkbox = container.layout().itemAt(1).widget()
        if open_checkbox.isChecked():
            return None
        _, orig = self.orig_rows[row]
        value = end_edit.dateTime().toPython()
        if orig is not None and self._same_min(value, orig):
            return orig
        return self._snap_min(value)

    def _collect_sessions(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Task", "Task name cannot be empty.")
            return None, None

        sessions = []
        now = datetime.now()
        for row in range(self.sessions_table.rowCount() - 1, -1, -1):
            begin = self._begin_value(row)
            end = self._end_value(row)

            if row > 0 and end is None:
                QMessageBox.warning(
                    self,
                    "Invalid Session",
                    "All sessions except the most recent displayed row must have an end.",
                )
                return None, None

            if end is not None and end < begin:
                QMessageBox.warning(
                    self,
                    "Invalid Session",
                    f"End cannot be earlier than begin on row {row + 1}.",
                )
                return None, None

            sessions.append(Session(begin=begin, end=end))
        sessions = normalize_sessions(sessions, now)
        open_sessions = [session for session in sessions if session.end is None]
        if len(open_sessions) > 1:
            QMessageBox.warning(
                self,
                "Invalid Sessions",
                "Only one session can have an empty end.",
            )
            return None, None

        if open_sessions and sessions[-1].end is not None:
            QMessageBox.warning(
                self,
                "Invalid Sessions",
                "Only the most recent session may have an empty end.",
            )
            return None, None

        return name, sessions

    def save(self):
        name, sessions = self._collect_sessions()
        if name is None:
            return

        if self.save_handler is not None:
            if not self.save_handler(self.task, name, sessions):
                return
        else:
            self.task.name = name
            self.task.sessions = sessions
            self.task.is_active = bool(sessions and sessions[-1].end is None)

        self.accept()

    def move_selected_sessions(self):
        if self.move_handler is None:
            return

        name, sessions = self._collect_sessions()
        if name is None:
            return

        selected_rows = sorted(self._selected_rows(), reverse=True)
        selected_sessions = [
            Session(begin=self._begin_value(row), end=self._end_value(row))
            for row in selected_rows
        ]
        selected_sessions.reverse()

        if not selected_sessions:
            QMessageBox.warning(self, "No Sessions Selected", "Select at least one session to move.")
            return

        if not self.move_handler(self.task, name, sessions, selected_sessions):
            return

        self.accept()
