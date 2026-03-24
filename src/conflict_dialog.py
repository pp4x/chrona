from datetime import datetime

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


class ConflictResolutionDialog(QDialog):
    KEEP_EXISTING = "existing"
    USE_EDITED = "edited"

    def __init__(self, begin: datetime, end: datetime, existing_task_name: str, edited_task_name: str, parent=None):
        super().__init__(parent)
        self.choice = None
        self.setWindowTitle("Resolve Time Conflict")

        layout = QVBoxLayout(self)
        question = QLabel(
            f"What did you do between {begin.strftime('%Y-%m-%d %H:%M')} and {end.strftime('%Y-%m-%d %H:%M')}?"
        )
        question.setWordWrap(True)
        layout.addWidget(question)

        keep_existing_btn = QPushButton(f"{existing_task_name}\nKeep existing task")
        keep_existing_btn.clicked.connect(lambda: self._choose(self.KEEP_EXISTING))
        layout.addWidget(keep_existing_btn)

        use_edited_btn = QPushButton(f"{edited_task_name}\nUse edited task")
        use_edited_btn.clicked.connect(lambda: self._choose(self.USE_EDITED))
        layout.addWidget(use_edited_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _choose(self, choice: str):
        self.choice = choice
        self.accept()
