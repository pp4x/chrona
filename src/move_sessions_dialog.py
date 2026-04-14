from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QListWidget, QVBoxLayout


class MoveSessionsDialog(QDialog):
    def __init__(self, active_task_names, source_task_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Move Sessions")
        self.resize(480, 360)
        self._source_task_name = source_task_name

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Move selected sessions to:"))

        layout.addWidget(QLabel("Active tasks"))
        self.task_list = QListWidget(self)
        self.task_list.addItems(active_task_names)
        self.task_list.currentTextChanged.connect(self._sync_input_from_list)
        layout.addWidget(self.task_list)

        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Type a task name or pick an active task")
        self.name_input.textChanged.connect(self._sync_list_from_input)
        layout.addWidget(self.name_input)

        self.feedback_label = QLabel("")
        layout.addWidget(self.feedback_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._sync_list_from_input(self.name_input.text())

    def destination_name(self):
        return self.name_input.text().strip()

    def _sync_input_from_list(self, value):
        if not value:
            return
        self.name_input.setText(value)

    def _sync_list_from_input(self, value):
        matching_items = self.task_list.findItems(value, Qt.MatchExactly)
        self.task_list.blockSignals(True)
        if matching_items:
            self.task_list.setCurrentItem(matching_items[0])
        else:
            self.task_list.clearSelection()
            self.task_list.setCurrentItem(None)
        self.task_list.blockSignals(False)

        normalized = " ".join(value.casefold().split())
        source_normalized = " ".join(self._source_task_name.casefold().split())
        if not normalized:
            self.feedback_label.setText("Choose an active task or type a task name.")
        elif normalized == source_normalized:
            self.feedback_label.setText("Destination must be different from the current task.")
        else:
            self.feedback_label.setText("Typing a completed task name will reactivate it.")
