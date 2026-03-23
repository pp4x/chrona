import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QPushButton, QLineEdit, QLabel, QListView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

class FilterBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        layout.addWidget(self.filter_label)
        layout.addWidget(self.filter_input)
        self.setLayout(layout)

class TaskTab(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.task_list = QListView()
        self.task_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.filter_bar = FilterBar()
        layout.addWidget(self.task_list)
        layout.addWidget(self.filter_bar)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chrona - Time Tracking, Simplified")
        self.resize(800, 600)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.new_activity_btn = QPushButton(QIcon.fromTheme("list-add"), "New Activity")
        self.resume_btn = QPushButton(QIcon.fromTheme("media-playback-start"), "Resume")
        self.pause_btn = QPushButton(QIcon.fromTheme("media-playback-pause"), "Pause")
        self.complete_btn = QPushButton(QIcon.fromTheme("task-complete"), "Complete")
        toolbar.addWidget(self.new_activity_btn)
        toolbar.addWidget(self.resume_btn)
        toolbar.addWidget(self.pause_btn)
        toolbar.addWidget(self.complete_btn)

        # Tabs
        self.tabs = QTabWidget()
        self.active_tab = TaskTab("Active")
        self.completed_tab = TaskTab("Completed")
        self.reports_tab = TaskTab("Reports")
        self.tabs.addTab(self.active_tab, "Active")
        self.tabs.addTab(self.completed_tab, "Completed")
        self.tabs.addTab(self.reports_tab, "Reports")

        self.setCentralWidget(self.tabs)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
