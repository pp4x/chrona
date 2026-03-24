import sys
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QPushButton, QLineEdit, QLabel, QTableView, QAbstractItemView, QHeaderView,
    QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QIcon
from reports_pane import ReportsPane
from Task import Task
from task_edit_dialog import TaskEditDialog

APP_ICON_PATH = Path(__file__).resolve().parent.parent / "icons" / "chrona.png"


# --- Utility for time formatting ---
def format_minutes(minutes):
    h, m = divmod(minutes, 60)
    if h:
        return f"{h}h {m:02d}m" if m else f"{h}h"
    return f"{m}m"

# --- Task Table Model ---
class TaskTableModel(QAbstractTableModel):
    def __init__(self, tasks):
        super().__init__()
        self._tasks = tasks

    def rowCount(self, parent=QModelIndex()):
        return len(self._tasks)

    def columnCount(self, parent=QModelIndex()):
        return 3  # Task Name, Total Time, Last Activity

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        task = self._tasks[index.row()]
        if index.column() == 0:
            return task.name
        elif index.column() == 1:
            return format_minutes(task.total_time)
        elif index.column() == 2:
            return task.last_activity_display
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return ["Task Name", "Total Time", "Last Activity"][section]
        return None

    def update_tasks(self, tasks):
        self.beginResetModel()
        self._tasks = tasks
        self.endResetModel()

class FilterBar(QWidget):
    def __init__(self, on_filter_applied, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter (press Enter to apply)")
        self.filter_input.returnPressed.connect(lambda: on_filter_applied(self.filter_input.text()))
        layout.addWidget(self.filter_label)
        layout.addWidget(self.filter_input)
        self.setLayout(layout)
class TaskTab(QWidget):
    selection_changed = Signal()
    task_double_clicked = Signal(object)

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self._all_tasks = self._load_tasks()
        self._filtered_tasks = self._all_tasks.copy()
        layout = QVBoxLayout(self)
        self.table = QTableView()
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.model = TaskTableModel(self._filtered_tasks)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.selectionModel().selectionChanged.connect(self._emit_selection_changed)
        self.table.doubleClicked.connect(self._handle_double_click)
        self.filter_bar = FilterBar(self.apply_filter)
        layout.addWidget(self.table)
        layout.addWidget(self.filter_bar)
        self.setLayout(layout)

    def _load_tasks(self):
        # No mock data; return empty list. Replace with real data source later.
        return []

    def add_task(self, task: Task):
        self._all_tasks.append(task)
        self.apply_filter(self.filter_bar.filter_input.text())

    def remove_task(self, task: Task):
        try:
            self._all_tasks.remove(task)
        except ValueError:
            return
        self.apply_filter(self.filter_bar.filter_input.text())

    def _sort_tasks_by_last_activity(self, tasks):
        return sorted(
            tasks,
            key=lambda task: (
                1 if task.is_active else 0,
                task.last_activity or datetime.min,
            ),
            reverse=True,
        )

    def pause_active_tasks(self):
        paused_any = False
        for task in self._all_tasks:
            if task.is_active:
                task.stop_session()
                paused_any = True

        if paused_any:
            self.apply_filter(self.filter_bar.filter_input.text())

    def apply_filter(self, text):
        # Case-insensitive, partial substring match over full task string
        t = text.strip().lower()
        if not t:
            filtered_tasks = self._all_tasks.copy()
        else:
            filtered_tasks = [task for task in self._all_tasks if t in task.name.lower()]
        self._filtered_tasks = self._sort_tasks_by_last_activity(filtered_tasks)
        self.model.update_tasks(self._filtered_tasks)
        self.table.clearSelection()
        self._emit_selection_changed()

    def selected_tasks(self):
        selected_indexes = self.table.selectionModel().selectedIndexes()
        selected_rows = sorted({index.row() for index in selected_indexes})
        return [self._filtered_tasks[row] for row in selected_rows]

    def selected_task(self):
        selected_tasks = self.selected_tasks()
        if len(selected_tasks) != 1:
            return None
        return selected_tasks[0]

    def refresh(self):
        self.apply_filter(self.filter_bar.filter_input.text())

    def select_task(self, task: Task):
        try:
            row = self._filtered_tasks.index(task)
        except ValueError:
            return

        self.table.selectRow(row)

    def _emit_selection_changed(self, *_args):
        self.selection_changed.emit()

    def _handle_double_click(self, index):
        if not index.isValid():
            return
        self.task_double_clicked.emit(self._filtered_tasks[index.row()])

class MainWindow(QMainWindow):
    @staticmethod
    def normalize_task_name(name):
        return " ".join(name.casefold().split())

    def find_task_by_name(self, name):
        normalized_name = self.normalize_task_name(name)
        for task in self.active_tab._all_tasks:
            if self.normalize_task_name(task.name) == normalized_name:
                return task, self.active_tab
        for task in self.completed_tab._all_tasks:
            if self.normalize_task_name(task.name) == normalized_name:
                return task, self.completed_tab
        return None, None

    def add_new_task(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QLineEdit, QLabel
        dialog = QDialog(self)
        dialog.setWindowTitle("New Activity")
        layout = QVBoxLayout(dialog)
        name_label = QLabel("Task:")
        name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(name_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.Accepted:
            name = name_input.text().strip()
            if name:
                self.active_tab.pause_active_tasks()
                task, source_tab = self.find_task_by_name(name)
                if task is None:
                    task = Task(name=name)
                    task.start_session()  # Start tracking immediately
                    self.active_tab.add_task(task)
                else:
                    if source_tab is self.completed_tab:
                        self.completed_tab.remove_task(task)
                        task.completed_at = None
                        self.active_tab.add_task(task)
                    task.start_session()
                    self.active_tab.refresh()
                self.tabs.setCurrentWidget(self.active_tab)
                self.active_tab.select_task(task)
                self.update_toolbar_state()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chrona - Time Tracking, Simplified")
        self.resize(800, 600)
        self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.new_activity_btn = QPushButton(QIcon.fromTheme("list-add"), "New Activity")
        self.new_activity_btn.clicked.connect(self.add_new_task)
        self.resume_btn = QPushButton(QIcon.fromTheme("media-playback-start"), "Resume")
        self.resume_btn.clicked.connect(self.resume_selected_task)
        self.pause_btn = QPushButton(QIcon.fromTheme("media-playback-pause"), "Pause")
        self.pause_btn.clicked.connect(self.pause_selected_task)
        self.complete_btn = QPushButton(QIcon.fromTheme("task-complete"), "Complete")
        self.complete_btn.clicked.connect(self.complete_selected_task)
        toolbar.addWidget(self.new_activity_btn)
        toolbar.addWidget(self.resume_btn)
        toolbar.addWidget(self.pause_btn)
        toolbar.addWidget(self.complete_btn)

        # Tabs
        self.tabs = QTabWidget()
        self.active_tab = TaskTab("Active")
        self.completed_tab = TaskTab("Completed")
        self.reports_tab = ReportsPane()
        self.tabs.addTab(self.active_tab, "Active")
        self.tabs.addTab(self.completed_tab, "Completed")
        self.tabs.addTab(self.reports_tab, "Reports")

        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.update_toolbar_state)
        self.active_tab.selection_changed.connect(self.update_toolbar_state)
        self.completed_tab.selection_changed.connect(self.update_toolbar_state)
        self.active_tab.task_double_clicked.connect(self.edit_task)
        self.completed_tab.task_double_clicked.connect(self.edit_task)
        self.update_toolbar_state()

    def update_toolbar_state(self):
        self.new_activity_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.complete_btn.setEnabled(False)
        self.resume_btn.setText("Resume")

        current_widget = self.tabs.currentWidget()
        if current_widget is self.completed_tab:
            selected_task = self.completed_tab.selected_task()
            if selected_task is not None:
                self.resume_btn.setEnabled(True)
                self.resume_btn.setText("Restart")
            return

        if current_widget is not self.active_tab:
            return

        selected_tasks = self.active_tab.selected_tasks()
        if len(selected_tasks) != 1:
            return

        selected_task = selected_tasks[0]
        if selected_task.is_active:
            self.pause_btn.setEnabled(True)
            self.complete_btn.setEnabled(True)
            return

        self.resume_btn.setEnabled(True)
        self.complete_btn.setEnabled(True)

    def pause_selected_task(self):
        if self.tabs.currentWidget() is not self.active_tab:
            return

        selected_task = self.active_tab.selected_task()
        if selected_task is None or not selected_task.is_active:
            return

        selected_task.stop_session()
        self.active_tab.refresh()
        self.active_tab.select_task(selected_task)
        self.update_toolbar_state()

    def resume_selected_task(self):
        current_widget = self.tabs.currentWidget()

        if current_widget is self.completed_tab:
            selected_task = self.completed_tab.selected_task()
            if selected_task is None:
                return

            self.active_tab.pause_active_tasks()
            self.completed_tab.remove_task(selected_task)
            selected_task.completed_at = None
            selected_task.start_session()
            self.active_tab.add_task(selected_task)
            self.tabs.setCurrentWidget(self.active_tab)
            self.active_tab.select_task(selected_task)
            self.update_toolbar_state()
            return

        if current_widget is not self.active_tab:
            return

        selected_task = self.active_tab.selected_task()
        if selected_task is None or selected_task.is_active:
            return

        self.active_tab.pause_active_tasks()
        selected_task.start_session()
        self.active_tab.refresh()
        self.active_tab.select_task(selected_task)
        self.update_toolbar_state()

    def edit_task(self, task: Task):
        dialog = TaskEditDialog(task, self)
        if dialog.exec() != QDialog.Accepted:
            return

        self.active_tab.refresh()
        self.completed_tab.refresh()
        current_tab = self.tabs.currentWidget()
        if current_tab in (self.active_tab, self.completed_tab):
            current_tab.select_task(task)
        self.update_toolbar_state()

    def complete_selected_task(self):
        if self.tabs.currentWidget() is not self.active_tab:
            return

        selected_task = self.active_tab.selected_task()
        if selected_task is None:
            return

        if selected_task.is_active:
            selected_task.stop_session()

        selected_task.completed_at = datetime.now()
        self.active_tab.remove_task(selected_task)
        self.completed_tab.add_task(selected_task)
        self.completed_tab.refresh()
        self.active_tab.refresh()
        self.active_tab.table.clearSelection()
        self.update_toolbar_state()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
