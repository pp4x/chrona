import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit,
    QStackedWidget, QTableView, QTreeView, QHeaderView
)
from PySide6.QtCore import Qt, QAbstractTableModel, QAbstractItemModel, QModelIndex, Signal
from datetime import datetime, timedelta
from formatting import format_minutes, format_seconds_as_minutes
from report_details_dialog import ReportDetailsDialog

class ReportDataAdapter:
    def __init__(self, connection: sqlite3.Connection | None = None):
        self.connection = connection

    def get_categories(self):
        if self.connection is None:
            return ["All"]

        rows = self.connection.execute(
            """
            SELECT DISTINCT category
            FROM tasks
            WHERE category IS NOT NULL AND category <> ''
            ORDER BY category
            """
        ).fetchall()
        return ["All"] + [row["category"] for row in rows]

    def get_report(self, period_type, period_start, category, group_by, text_filter):
        if self.connection is None:
            return []

        if group_by == "Timeline":
            slices = self._session_slices(period_type, period_start, category, text_filter)
            slices.sort(key=lambda row: (row["begin"], row["end"], row["name"].lower()))
            return [
                {
                    "task": row["name"],
                    "begin": row["begin"],
                    "end": row["end"],
                    "time": row["seconds"],
                    "end_display": row["end"].strftime("%H:%M") if row["is_ongoing"] is False else row["end_display"],
                }
                for row in slices
            ]

        task_totals = {}
        for row in self._session_slices(period_type, period_start, category, text_filter):
            task_entry = task_totals.setdefault(
                row["name"],
                {
                    "name": row["name"],
                    "project": row["project"] or "(unassigned)",
                    "time": 0.0,
                },
            )
            task_entry["time"] += row["seconds"]

        task_rows = sorted(task_totals.values(), key=lambda row: (-row["time"], row["name"].lower()))
        if group_by == "Task":
            return [{"name": row["name"], "time": row["time"]} for row in task_rows]

        project_groups = {}
        for row in task_rows:
            group = project_groups.setdefault(
                row["project"],
                {"project": row["project"], "total": 0, "tasks": []},
            )
            group["total"] += row["time"]
            group["tasks"].append({"name": row["name"], "time": row["time"]})

        groups = list(project_groups.values())
        for group in groups:
            group["tasks"].sort(key=lambda row: (-row["time"], row["name"].lower()))

        assigned = sorted(
            [group for group in groups if group["project"] != "(unassigned)"],
            key=lambda group: (-group["total"], group["project"].lower()),
        )
        unassigned = [group for group in groups if group["project"] == "(unassigned)"]
        return assigned + unassigned

    def get_detail_rows(self, period_type, period_start, category, text_filter, group_by, value):
        slices = self._session_slices(period_type, period_start, category, text_filter)
        if group_by == "Task":
            detail_slices = [row for row in slices if row["name"] == value]
        else:
            detail_slices = [row for row in slices if (row["project"] or "(unassigned)") == value]

        detail_slices.sort(key=lambda row: (row["begin"], row["end"]), reverse=True)
        total_seconds = sum(row["seconds"] for row in detail_slices)

        if group_by == "Task":
            rows = [
                [
                    row["begin"].strftime("%b %d"),
                    row["begin"].strftime("%H:%M"),
                    row["end"].strftime("%H:%M") if row["is_ongoing"] is False else row["end_display"],
                    format_seconds_as_minutes(row["seconds"]),
                ]
                for row in detail_slices
            ]
            headers = ["Date", "Begin", "End", "Duration"]
        else:
            rows = [
                [
                    row["name"],
                    row["begin"].strftime("%b %d"),
                    row["begin"].strftime("%H:%M"),
                    row["end"].strftime("%H:%M") if row["is_ongoing"] is False else row["end_display"],
                    format_seconds_as_minutes(row["seconds"]),
                ]
                for row in detail_slices
            ]
            headers = ["Task", "Date", "Begin", "End", "Duration"]

        return headers, rows, total_seconds

    def _session_slices(self, period_type, period_start, category, text_filter):
        period_end = self._get_period_end(period_type, period_start)
        now = datetime.now()
        rows = self.connection.execute(
            """
            SELECT
                t.name,
                t.category,
                t.project,
                s.begin_at,
                s.end_at
            FROM tasks t
            JOIN sessions s ON s.task_id = t.id
            WHERE s.begin_at < ?
              AND COALESCE(s.end_at, ?) > ?
            """,
            (period_end.isoformat(), now.isoformat(), period_start.isoformat()),
        ).fetchall()

        text_filter_normalized = text_filter.strip().lower()
        slices = []
        for row in rows:
            if category != "All" and row["category"] != category:
                continue

            task_name = row["name"]
            if text_filter_normalized and text_filter_normalized not in task_name.lower():
                continue

            begin = datetime.fromisoformat(row["begin_at"])
            raw_end = datetime.fromisoformat(row["end_at"]) if row["end_at"] is not None else now
            overlap_begin = max(begin, period_start)
            overlap_end = min(raw_end, period_end)
            if overlap_begin >= overlap_end:
                continue

            seconds = (overlap_end - overlap_begin).total_seconds()

            slices.append(
                {
                    "name": task_name,
                    "project": row["project"],
                    "begin": overlap_begin,
                    "end": overlap_end,
                    "seconds": seconds,
                    "is_ongoing": row["end_at"] is None and overlap_end == now,
                    "end_display": "Now",
                }
            )
        return slices

    def _get_period_end(self, period_type, period_start):
        if period_type == "Daily":
            return period_start + timedelta(days=1)
        if period_type == "Monthly":
            if period_start.month == 12:
                return period_start.replace(year=period_start.year + 1, month=1, day=1)
            return period_start.replace(month=period_start.month + 1, day=1)
        return period_start + timedelta(days=7)

# --- Table Model for Task Grouping ---
class ReportTableModel(QAbstractTableModel):
    def __init__(self, data, headers=None, value_getters=None):
        super().__init__()
        self._data = data
        self._headers = headers or ["Name", "Time"]
        self._value_getters = value_getters or [
            lambda row: row["name"],
            lambda row: format_seconds_as_minutes(row["time"]),
        ]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        row = self._data[index.row()]
        return self._value_getters[index.column()](row)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
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
                return format_seconds_as_minutes(item["total"])
        else:
            if index.column() == 0:
                return item["name"]
            elif index.column() == 1:
                return format_seconds_as_minutes(item["time"])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return ["Name", "Time"][section]
        return None

# --- Reports Pane Widget ---
class ReportsPane(QWidget):
    edit_day_requested = Signal(object)

    def __init__(self, connection=None, parent=None):
        super().__init__(parent)
        self.adapter = ReportDataAdapter(connection)
        self.state = {
            "report_type": "Weekly",
            "period_start": self._get_current_week_start(),
            "category": "All",
            "group_by": "Project",
            "text_filter": ""
        }
        self._init_ui()
        self._current_data = []
        self._refresh_report()

    def refresh(self):
        self._populate_categories()
        self._refresh_report()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        # Top controls
        top = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.type_combo.setCurrentText(self.state["report_type"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.prev_btn = QPushButton("←")
        self.prev_btn.clicked.connect(self._on_prev)
        self.period_label = QLabel()
        self.current_period_btn = QPushButton("This Week")
        self.current_period_btn.clicked.connect(self._on_current_period)
        self.next_btn = QPushButton("→")
        self.next_btn.clicked.connect(self._on_next)
        self.edit_day_btn = QPushButton("Edit Day")
        self.edit_day_btn.clicked.connect(self._on_edit_day)
        top.addWidget(self.type_combo)
        top.addWidget(self.prev_btn)
        top.addWidget(self.period_label)
        top.addWidget(self.current_period_btn)
        top.addWidget(self.next_btn)
        top.addWidget(self.edit_day_btn)
        top.addStretch()
        layout.addLayout(top)
        # Filters
        filters = QHBoxLayout()
        self.category_combo = QComboBox()
        self._populate_categories()
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self.group_by_combo = QComboBox()
        self.group_by_combo.currentTextChanged.connect(self._on_group_by_changed)
        self._sync_group_by_options()
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
        self.table_view.doubleClicked.connect(self._open_task_details)
        self.tree_view = QTreeView()
        self.tree_view.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree_view.doubleClicked.connect(self._open_project_details)
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
        self.current_period_btn.setText(self._current_period_label())
        self._refresh_edit_btn()
        # Get data
        data = self.adapter.get_report(
            self.state["report_type"],
            self.state["period_start"],
            self.state["category"],
            self.state["group_by"],
            self.state["text_filter"]
        )
        self._current_data = data
        # Update view
        if self.state["group_by"] == "Timeline":
            model = ReportTableModel(
                data,
                headers=["Begin", "End", "Task", "Duration"],
                value_getters=[
                    lambda row: row["begin"].strftime("%H:%M"),
                    lambda row: row["end_display"],
                    lambda row: row["task"],
                    lambda row: format_seconds_as_minutes(row["time"]),
                ],
            )
            self.table_view.setModel(model)
            self.results_stack.setCurrentWidget(self.table_view)
            total = sum(row["time"] for row in data)
        elif self.state["group_by"] == "Task":
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
        self.total_label.setText(f"Total: {format_seconds_as_minutes(total)}")

    def _on_type_changed(self, value):
        self.state["report_type"] = value
        self._sync_group_by_options()
        if value == "Daily":
            self.state["period_start"] = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif value == "Monthly":
            now = datetime.now()
            self.state["period_start"] = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            self.state["period_start"] = self._get_current_week_start()
        self._refresh_report()

    def _populate_categories(self):
        current_value = self.state["category"]
        categories = self.adapter.get_categories()
        self.category_combo.clear()
        self.category_combo.addItems(categories)
        if current_value in categories:
            self.category_combo.setCurrentText(current_value)
            return
        self.state["category"] = "All"
        self.category_combo.setCurrentText("All")

    def _on_prev(self):
        if self.state["report_type"] == "Daily":
            self.state["period_start"] -= timedelta(days=1)
        elif self.state["report_type"] == "Monthly":
            current = self.state["period_start"]
            previous_month_last_day = current.replace(day=1) - timedelta(days=1)
            self.state["period_start"] = previous_month_last_day.replace(day=1)
        else:
            self.state["period_start"] -= timedelta(days=7)
        self._refresh_report()

    def _on_next(self):
        if self.state["report_type"] == "Daily":
            self.state["period_start"] += timedelta(days=1)
        elif self.state["report_type"] == "Monthly":
            current = self.state["period_start"]
            if current.month == 12:
                self.state["period_start"] = current.replace(year=current.year + 1, month=1, day=1)
            else:
                self.state["period_start"] = current.replace(month=current.month + 1, day=1)
        else:
            self.state["period_start"] += timedelta(days=7)
        self._refresh_report()

    def _on_current_period(self):
        if self.state["report_type"] == "Daily":
            self.state["period_start"] = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.state["report_type"] == "Monthly":
            now = datetime.now()
            self.state["period_start"] = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            self.state["period_start"] = self._get_current_week_start()
        self._refresh_report()

    def _on_category_changed(self, value):
        self.state["category"] = value
        self._refresh_report()

    def _on_group_by_changed(self, value):
        self.state["group_by"] = value
        self._refresh_report()

    def _sync_group_by_options(self):
        current_value = self.state["group_by"]
        options = ["Task", "Project"]
        if self.state["report_type"] == "Daily":
            options.append("Timeline")

        self.group_by_combo.blockSignals(True)
        self.group_by_combo.clear()
        self.group_by_combo.addItems(options)
        if current_value not in options:
            current_value = "Task"
            self.state["group_by"] = current_value
        self.group_by_combo.setCurrentText(current_value)
        self.group_by_combo.blockSignals(False)

    def _on_text_filter(self):
        self.state["text_filter"] = self.text_filter.text()
        self._refresh_report()

    def _on_edit_day(self):
        self.edit_day_requested.emit(self.state["period_start"])

    def _refresh_edit_btn(self):
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.edit_day_btn.setEnabled(
            self.state["report_type"] == "Daily"
            and self.state["period_start"] <= today_start
        )

    def _format_period_label(self):
        if self.state["report_type"] == "Daily":
            return self.state["period_start"].strftime("%b %d, %Y")
        if self.state["report_type"] == "Monthly":
            return self.state["period_start"].strftime("%b %Y")
        else:
            start = self.state["period_start"]
            end = start + timedelta(days=6)
            return f"{start.strftime('%b %d')} – {end.strftime('%b %d')}"

    def _current_period_label(self):
        if self.state["report_type"] == "Daily":
            return "Today"
        if self.state["report_type"] == "Monthly":
            return "This Month"
        return "This Week"

    def _get_current_week_start(self):
        now = datetime.now()
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)

    def _open_task_details(self, index):
        if not index.isValid():
            return

        row = self._current_data[index.row()]
        if self.state["group_by"] == "Task":
            self._show_details_dialog("Task", row["name"])
            return
        if self.state["group_by"] == "Timeline":
            self._show_details_dialog("Task", row["task"])

    def _open_project_details(self, index):
        if not index.isValid() or self.state["group_by"] != "Project":
            return

        item = index.internalPointer()
        if "project" in item:
            self._show_details_dialog("Project", item["project"])
            return

        self._show_details_dialog("Task", item["name"])

    def _show_details_dialog(self, detail_type, value):
        headers, rows, total_seconds = self.adapter.get_detail_rows(
            self.state["report_type"],
            self.state["period_start"],
            self.state["category"],
            self.state["text_filter"],
            detail_type,
            value,
        )
        dialog = ReportDetailsDialog(
            value,
            "",
            self._format_period_label(),
            headers,
            rows,
            total_seconds,
            self,
        )
        dialog.exec()
