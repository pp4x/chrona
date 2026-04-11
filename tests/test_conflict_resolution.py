from datetime import datetime

import chrona
from Task import Session, Task
from chrona import MainWindow


def dt(hour, minute=0):
    return datetime(2026, 3, 24, hour, minute)


class StubRepository:
    def __init__(self):
        self.saved_tasks = None

    def save_tasks(self, tasks):
        self.saved_tasks = tasks


class StubWindow:
    find_first_conflict = MainWindow.find_first_conflict
    apply_task_edits = MainWindow.apply_task_edits

    def __init__(self, tasks):
        self._tasks = tasks
        self.repository = StubRepository()

    def all_tasks(self):
        return self._tasks

    def find_task_by_id(self, task_id):
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None


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
