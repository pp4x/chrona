from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from formatting import format_seconds_as_minutes


class ReportDetailsDialog(QDialog):
    def __init__(self, title, period_label, subtitle, headers, rows, total_seconds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Details")
        self.resize(720, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(title))
        layout.addWidget(QLabel(period_label))
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        table = QTableWidget(len(rows), len(headers), self)
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, QTableWidgetItem(value))
        table.resizeColumnsToContents()
        layout.addWidget(table)

        layout.addWidget(QLabel(f"Total: {format_seconds_as_minutes(total_seconds)}"))

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)
