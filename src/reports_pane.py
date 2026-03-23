from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit,
    QStackedWidget, QTableView, QTreeView, QHeaderView
)
from PySide6.QtCore import Qt, QAbstractTableModel, QAbstractItemModel, QModelIndex
from datetime import datetime, timedelta

# --- Mock Data Adapter ---
class ReportDataAdapter:
    """Mock data adapter for report data. Replace with real DB logic later."""
    def get_categories(self):
        return ["All", "work", "personal"]

    def get_report(self, period_type, period_start, category, group_by, text_filter):
        # Return empty data (no sample/mock entries)
        if group_by == "Task":
            return []
        else:  # group_by == "Project"
            return []

# --- Table Model for Task Grouping ---
class ReportTableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 2  # Name, Time

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        row = self._data[index.row()]
        if index.column() == 0:
            return row["name"]
        elif index.column() == 1:
            return format_minutes(row["time"])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return ["Name", "Time"][section]
        return None

# --- Tree Model for Project Grouping ---
class ReportTreeModel(QAbstractItemModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self._data)
        if parent.internalPointer() and "tasks" in parent.internalPointer():
            return len(parent.internalPointer()["tasks"])
        return 0

    def columnCount(self, parent):
        return 2

    def index(self, row, column, parent):
        if not parent.isValid():
            return self.createIndex(row, column, self._data[row])
        parent_item = parent.internalPointer()
        if parent_item and "tasks" in parent_item:
            return self.createIndex(row, column, parent_item["tasks"][row])
        return QModelIndex()

    def parent(self, index):
        item = index.internalPointer()
        if item and "project" in item:
            return QModelIndex()
        for group in self._data:
            if "tasks" in group and item in group["tasks"]:
                row = self._data.index(group)
                return self.createIndex(row, 0, group)
        return QModelIndex()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        item = index.internalPointer()
        if "project" in item:
            if index.column() == 0:
                return item["project"]
            elif index.column() == 1:
                return format_minutes(item["total"])
        else:
            if index.column() == 0:
                return item["name"]
            elif index.column() == 1:
                return format_minutes(item["time"])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return ["Name", "Time"][section]
        return None

# --- Utility ---
def format_minutes(minutes):
    h, m = divmod(minutes, 60)
    if h:
        return f"{h}h {m:02d}m" if m else f"{h}h"
    return f"{m}m"

# --- Reports Pane Widget ---
class ReportsPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.adapter = ReportDataAdapter()
        self.state = {
            "report_type": "Weekly",
            "period_start": self._get_current_week_start(),
            "category": "All",
            "group_by": "Project",
            "text_filter": ""
        }
        self._init_ui()
        self._refresh_report()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        # Top controls
        top = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Daily", "Weekly"])
        self.type_combo.setCurrentText(self.state["report_type"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.prev_btn = QPushButton("←")
        self.prev_btn.clicked.connect(self._on_prev)
        self.period_label = QLabel()
        self.next_btn = QPushButton("→")
        self.next_btn.clicked.connect(self._on_next)
        top.addWidget(self.type_combo)
        top.addWidget(self.prev_btn)
        top.addWidget(self.period_label)
        top.addWidget(self.next_btn)
        top.addStretch()
        layout.addLayout(top)
        # Filters
        filters = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.adapter.get_categories())
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self.group_by_combo = QComboBox()
        self.group_by_combo.addItems(["Task", "Project"])
        self.group_by_combo.setCurrentText(self.state["group_by"])
        self.group_by_combo.currentTextChanged.connect(self._on_group_by_changed)
        filters.addWidget(QLabel("Category:"))
        filters.addWidget(self.category_combo)
        filters.addWidget(QLabel("Group by:"))
        filters.addWidget(self.group_by_combo)
        filters.addStretch()
        layout.addLayout(filters)
        # Results area
        self.results_stack = QStackedWidget()
        self.table_view = QTableView()
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tree_view = QTreeView()
        self.tree_view.header().setSectionResizeMode(QHeaderView.Stretch)
        self.results_stack.addWidget(self.table_view)
        self.results_stack.addWidget(self.tree_view)
        layout.addWidget(self.results_stack)
        # Total row
        self.total_label = QLabel()
        layout.addWidget(self.total_label)
        # Text filter
        filter_layout = QHBoxLayout()
        self.text_filter = QLineEdit()
        self.text_filter.setPlaceholderText("Filter (press Enter to apply)")
        self.text_filter.returnPressed.connect(self._on_text_filter)
        filter_layout.addWidget(self.text_filter)
        layout.addLayout(filter_layout)
        self.setLayout(layout)

    def _refresh_report(self):
        # Update period label
        self.period_label.setText(self._format_period_label())
        # Get data
        data = self.adapter.get_report(
            self.state["report_type"],
            self.state["period_start"],
            self.state["category"],
            self.state["group_by"],
            self.state["text_filter"]
        )
        # Update view
        if self.state["group_by"] == "Task":
            model = ReportTableModel(data)
            self.table_view.setModel(model)
            self.results_stack.setCurrentWidget(self.table_view)
            total = sum(row["time"] for row in data)
        else:
            # Sort projects, keep (unassigned) at bottom
            data_sorted = sorted(
                [d for d in data if d["project"] != "(unassigned)"],
                key=lambda x: -x["total"]
            )
            unassigned = [d for d in data if d["project"] == "(unassigned)"]
            data_sorted += unassigned
            model = ReportTreeModel(data_sorted)
            self.tree_view.setModel(model)
            self.results_stack.setCurrentWidget(self.tree_view)
            total = sum(group["total"] for group in data)
        self.total_label.setText(f"Total: {format_minutes(total)}")

    def _on_type_changed(self, value):
        self.state["report_type"] = value
        if value == "Daily":
            self.state["period_start"] = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            self.state["period_start"] = self._get_current_week_start()
        self._refresh_report()

    def _on_prev(self):
        if self.state["report_type"] == "Daily":
            self.state["period_start"] -= timedelta(days=1)
        else:
            self.state["period_start"] -= timedelta(days=7)
        self._refresh_report()

    def _on_next(self):
        if self.state["report_type"] == "Daily":
            self.state["period_start"] += timedelta(days=1)
        else:
            self.state["period_start"] += timedelta(days=7)
        self._refresh_report()

    def _on_category_changed(self, value):
        self.state["category"] = value
        self._refresh_report()

    def _on_group_by_changed(self, value):
        self.state["group_by"] = value
        self._refresh_report()

    def _on_text_filter(self):
        self.state["text_filter"] = self.text_filter.text()
        self._refresh_report()

    def _format_period_label(self):
        if self.state["report_type"] == "Daily":
            return self.state["period_start"].strftime("%b %d, %Y")
        else:
            start = self.state["period_start"]
            end = start + timedelta(days=6)
            return f"{start.strftime('%b %d')} – {end.strftime('%b %d')}"

    def _get_current_week_start(self):
        now = datetime.now()
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
