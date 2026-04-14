from datetime import datetime

import chrona
from Task import Session, Task
from chrona import MainWindow


def dt(hour, minute=0):
    return datetime(2026, 3, 24, hour, minute)


class StubRepository:
    def __init__(self):
        self.saved_tasks = []

    def save_tasks(self, tasks):
        self.saved_tasks.append(tasks)


class StubTaskTab:
    def __init__(self, tasks):
        self._all_tasks = list(tasks)
        self.selected = None
        self.refreshed = 0

    def add_task(self, task):
        if task not in self._all_tasks:
            self._all_tasks.append(task)

    def remove_task(self, task):
        if task in self._all_tasks:
            self._all_tasks.remove(task)

    def refresh(self):
        self.refreshed += 1

    def select_task(self, task):
        self.selected = task


class StubTabs:
    def __init__(self, current_widget):
        self._current_widget = current_widget

    def currentWidget(self):
        return self._current_widget

    def setCurrentWidget(self, widget):
        self._current_widget = widget


class StubWindow:
    find_first_conflict = MainWindow.find_first_conflict
    _resolve_task_edits = MainWindow._resolve_task_edits
    _commit_task_updates = MainWindow._commit_task_updates
    apply_task_edits = MainWindow.apply_task_edits
    find_task_by_name = MainWindow.find_task_by_name
    normalize_task_name = staticmethod(MainWindow.normalize_task_name)
    move_task_sessions = MainWindow.move_task_sessions

    def __init__(self, tasks):
        self._tasks = tasks
        self.repository = StubRepository()
        active_tasks = [task for task in tasks if task.completed_at is None]
        completed_tasks = [task for task in tasks if task.completed_at is not None]
        self.active_tab = StubTaskTab(active_tasks)
        self.completed_tab = StubTaskTab(completed_tasks)
        self.tabs = StubTabs(self.active_tab)
        self.toolbar_updates = 0

    def all_tasks(self):
        return self.active_tab._all_tasks + self.completed_tab._all_tasks

    def find_task_by_id(self, task_id):
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    def prompt_move_destination(self, _source_task_name):
        return "Archive task"

    def update_toolbar_state(self):
        self.toolbar_updates += 1


def test_keep_existing_cuts_all(monkeypatch):
    edit_task = Task(
        "Renamed task",
        id=1,
        sessions=[Session(begin=dt(9), end=dt(15))],
    )
    old_task = Task(
        "Existing task",
        id=2,
        sessions=[
            Session(begin=dt(10), end=dt(11)),
            Session(begin=dt(13), end=dt(14)),
        ],
    )
    window = StubWindow([edit_task, old_task])

    class FakeDialog:
        KEEP_EXISTING = chrona.ConflictResolutionDialog.KEEP_EXISTING
        USE_EDITED = chrona.ConflictResolutionDialog.USE_EDITED
        calls = 0

        def __init__(self, *args, **kwargs):
            self.choice = self.KEEP_EXISTING

        def exec(self):
            type(self).calls += 1
            return chrona.QDialog.Accepted

    monkeypatch.setattr(chrona, "ConflictResolutionDialog", FakeDialog)

    saved = window.apply_task_edits(edit_task, edit_task.name, edit_task.sessions)

    assert saved is True
    assert FakeDialog.calls == 1
    assert edit_task.sessions == [
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(11), end=dt(13)),
        Session(begin=dt(14), end=dt(15)),
    ]


def test_move_sessions_resurrects_completed_task(monkeypatch):
    source_task = Task(
        "Source task",
        id=1,
        sessions=[
            Session(begin=dt(9), end=dt(10)),
            Session(begin=dt(11), end=dt(12)),
        ],
    )
    completed_task = Task(
        "Archive task",
        id=2,
        sessions=[Session(begin=dt(7), end=dt(8))],
        completed_at=dt(13),
    )
    window = StubWindow([source_task, completed_task])

    class UnexpectedDialog:
        KEEP_EXISTING = chrona.ConflictResolutionDialog.KEEP_EXISTING
        USE_EDITED = chrona.ConflictResolutionDialog.USE_EDITED

        def __init__(self, *args, **kwargs):
            raise AssertionError("did not expect a conflict dialog")

    monkeypatch.setattr(chrona, "ConflictResolutionDialog", UnexpectedDialog)

    moved = window.move_task_sessions(
        source_task,
        source_task.name,
        source_task.sessions,
        [Session(begin=dt(11), end=dt(12))],
    )

    assert moved is True
    assert source_task.sessions == [Session(begin=dt(9), end=dt(10))]
    assert completed_task.completed_at is None
    assert completed_task.sessions == [
        Session(begin=dt(7), end=dt(8)),
        Session(begin=dt(11), end=dt(12)),
    ]
    assert completed_task in window.active_tab._all_tasks
    assert completed_task not in window.completed_tab._all_tasks
    assert window.active_tab.selected is completed_task
