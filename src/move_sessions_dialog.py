from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QListWidget, QVBoxLayout


class MoveSessionsDialog(QDialog):
    def __init__(self, active_task_names, source_task_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Move Sessions")
        self.resize(480, 360)
        self._source_task_name = source_task_name
        self._all_task_names = list(active_task_names)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Move selected sessions to:"))

        layout.addWidget(QLabel("Active tasks"))
        self.task_list = QListWidget(self)
        self.task_list.itemClicked.connect(self._sync_input_from_item)
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
        self.ok_button = buttons.button(QDialogButtonBox.Ok)

        self._sync_list_from_input(self.name_input.text())
        self.name_input.setFocus(Qt.OtherFocusReason)

    def destination_name(self):
        return self.name_input.text().strip()

    @staticmethod
    def _normalize_name(value):
        return " ".join(value.casefold().split())

    def _sync_input_from_item(self, item):
        if item is None:
            return
        self.name_input.setText(item.text())

    def _sync_list_from_input(self, value):
        normalized_value = self._normalize_name(value)
        self.task_list.blockSignals(True)
        self.task_list.clear()
        if not normalized_value:
            filtered_names = self._all_task_names
        else:
            filtered_names = [
                task_name
                for task_name in self._all_task_names
                if self._normalize_name(task_name).startswith(normalized_value)
            ]
        self.task_list.addItems(filtered_names)
        self.task_list.blockSignals(False)

        source_normalized = self._normalize_name(self._source_task_name)
        if not normalized_value:
            self.feedback_label.setText("Choose an active task or type a new task name.")
        elif normalized_value == source_normalized:
            self.feedback_label.setText("Destination must be different from the current task.")
        elif filtered_names:
            self.feedback_label.setText("Click a task to use its exact name, or keep typing to create/reactivate.")
        else:
            self.feedback_label.setText("No active match. Typing a new name creates a task; a completed name reactivates it.")

        self.ok_button.setEnabled(bool(value.strip()))
