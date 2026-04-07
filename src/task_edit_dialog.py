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
from session_ops import normalize_sessions


class TaskEditDialog(QDialog):
    DATETIME_FORMAT = "yyyy-MM-dd HH:mm"

    def __init__(self, task: Task, save_handler=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.save_handler = save_handler
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
        button_row.addWidget(self.add_session_btn)
        button_row.addWidget(self.delete_session_btn)
        button_row.addStretch()
        layout.addLayout(button_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate_sessions()

    def _populate_sessions(self):
        self.sessions_table.setRowCount(0)
        for session in self.task.sessions:
            self._insert_session_row(session.begin, session.end)
        self._refresh_open_controls()

    def _insert_session_row(self, begin=None, end=None, row=0):
        if begin is None:
            begin = datetime.now()

        self.sessions_table.insertRow(row)
        begin_edit = self._create_datetime_edit(begin)
        self.sessions_table.setCellWidget(row, 0, begin_edit)
        self.sessions_table.setCellWidget(row, 1, self._create_end_editor(end))

    def add_session_row(self):
        self._insert_session_row()
        self.sessions_table.selectRow(0)
        self._refresh_open_controls()

    def delete_selected_sessions(self):
        selected_rows = sorted(
            {index.row() for index in self.sessions_table.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in selected_rows:
            self.sessions_table.removeRow(row)
        self._refresh_open_controls()

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

    def _to_qdatetime(self, value):
        return QDateTime(
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
        )

    def _begin_value(self, row):
        editor = self.sessions_table.cellWidget(row, 0)
        return editor.dateTime().toPython()

    def _end_value(self, row):
        container = self.sessions_table.cellWidget(row, 1)
        end_edit = container.layout().itemAt(0).widget()
        open_checkbox = container.layout().itemAt(1).widget()
        if open_checkbox.isChecked():
            return None
        return end_edit.dateTime().toPython()

    def save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Task", "Task name cannot be empty.")
            return

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
                return

            if end is not None and end < begin:
                QMessageBox.warning(
                    self,
                    "Invalid Session",
                    f"End cannot be earlier than begin on row {row + 1}.",
                )
                return

            sessions.append(Session(begin=begin, end=end))
        sessions = normalize_sessions(sessions, now)
        open_sessions = [session for session in sessions if session.end is None]
        if len(open_sessions) > 1:
            QMessageBox.warning(
                self,
                "Invalid Sessions",
                "Only one session can have an empty end.",
            )
            return

        if open_sessions and sessions[-1].end is not None:
            QMessageBox.warning(
                self,
                "Invalid Sessions",
                "Only the most recent session may have an empty end.",
            )
            return

        if self.save_handler is not None:
            if not self.save_handler(self.task, name, sessions):
                return
        else:
            self.task.name = name
            self.task.sessions = sessions
            self.task.is_active = bool(sessions and sessions[-1].end is None)

        self.accept()
