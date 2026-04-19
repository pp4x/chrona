from datetime import datetime

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
import timeline_editor

from Task import Session, Task
from timeline_editor import (
    TaskNameIndex,
    TimelineRow,
    TimelineEditorDialog,
    apply_rows_to_tasks,
    carve_rows,
    editable_save_rows,
    has_save_changes,
    rows_for_day,
)


def dt(hour, minute=0):
    return datetime(2026, 3, 24, hour, minute)


def app():
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    return inst


def test_clips_midnight():
    task = Task("Night work", id=1, sessions=[Session(datetime(2026, 3, 23, 23), dt(1))])

    rows = rows_for_day([task], dt(0), dt(12))

    assert len(rows) == 1
    assert rows[0].begin == dt(0)
    assert rows[0].end == dt(1)


def test_carves_last():
    coding = TimelineRow("Coding", dt(9), dt(11), sequence=1)
    admin = TimelineRow("Admin", dt(10), dt(10, 30), sequence=2)
    index = TaskNameIndex([Task("Coding"), Task("Admin")], [])

    rows, trimmed = carve_rows([coding, admin], admin, index)

    assert trimmed is False
    assert [(row.task_name, row.begin, row.end) for row in rows] == [
        ("Coding", dt(9), dt(10)),
        ("Admin", dt(10), dt(10, 30)),
        ("Coding", dt(10, 30), dt(11)),
    ]


def test_same_task_merge():
    first = TimelineRow("Coding", dt(9), dt(10), sequence=1)
    touching = TimelineRow("Coding", dt(10), dt(11), sequence=2)
    index = TaskNameIndex([Task("Coding")], [])

    rows, _ = carve_rows([first, touching], touching, index)

    assert rows == [first, touching]

    overlap = TimelineRow("Coding", dt(9, 30), dt(10, 30), sequence=3)
    rows, _ = carve_rows([first, overlap], overlap, index)

    assert [(row.task_name, row.begin, row.end) for row in rows] == [
        ("Coding", dt(9), dt(10, 30)),
    ]


def test_current_trim():
    old = TimelineRow("Old", dt(9), dt(11), sequence=1)
    current = TimelineRow("Current", dt(10), dt(12), read_only=True, status="Current", sequence=2)
    index = TaskNameIndex([Task("Old"), Task("Current")], [])

    rows, trimmed = carve_rows([old, current], old, index)

    assert trimmed is True
    assert [(row.task_name, row.begin, row.end, row.read_only) for row in rows] == [
        ("Old", dt(9), dt(10), False),
        ("Current", dt(10), dt(12), True),
    ]


def test_placeholder():
    original = [TimelineRow("Coding", dt(9), dt(10), sequence=1)]
    placeholder = TimelineRow("", dt(10), dt(10), sequence=2)

    assert editable_save_rows(original + [placeholder]) == original
    assert has_save_changes(original, original + [placeholder]) is False


def test_keeps_outside():
    task = Task(
        "Coding",
        id=1,
        sessions=[
            Session(datetime(2026, 3, 23, 23), dt(1)),
            Session(dt(9), dt(11)),
        ],
    )
    admin_row = TimelineRow("Admin", dt(10), dt(10, 30), sequence=1)

    changed = apply_rows_to_tasks([task], [], dt(0), [admin_row], dt(12))

    admin = [changed_task for changed_task in changed if changed_task.name == "Admin"][0]
    assert task.sessions == [Session(datetime(2026, 3, 23, 23), dt(0))]
    assert admin.sessions == [Session(dt(10), dt(10, 30))]


def test_past_done():
    row = TimelineRow("Archive", dt(9), dt(10), sequence=1)

    changed = apply_rows_to_tasks([], [], dt(0), [row], datetime(2026, 3, 25, 12))

    assert changed[0].name == "Archive"
    assert changed[0].completed_at == dt(10)


def test_keeps_current():
    task = Task("Live", id=1, sessions=[Session(dt(9), None)], is_active=True)
    current = TimelineRow("Live", dt(9), dt(12), read_only=True, status="Current")

    changed = apply_rows_to_tasks([task], [], dt(0), [current], dt(12, 30))

    assert changed == []
    assert task.sessions == [Session(dt(9), None)]


def test_dup_keeps_task():
    app()
    task = Task("Coding", id=1, sessions=[Session(dt(9), dt(10))])
    dialog = TimelineEditorDialog(dt(0), [task], [], lambda *_args: True)

    dialog.table.selectRow(0)
    dialog.duplicate_slot()

    assert [(row.task_name, row.begin, row.end) for row in dialog.rows] == [
        ("Coding", dt(9), dt(10)),
        ("Coding", dt(10), dt(10)),
    ]


def test_no_keeps_open(monkeypatch):
    app()
    task = Task("Coding", id=1, sessions=[Session(dt(9), dt(10))])
    dialog = TimelineEditorDialog(dt(0), [task], [], lambda *_args: True)
    dialog.show()
    dialog.add_slot()
    monkeypatch.setattr(
        timeline_editor.QMessageBox,
        "question",
        lambda *_args: timeline_editor.QMessageBox.StandardButton.No,
    )

    dialog.reject()

    assert dialog.isVisible()


def test_esc_with_focus_stays():
    app()
    task = Task("Coding", id=1, sessions=[Session(dt(9), dt(10))])
    dialog = TimelineEditorDialog(dt(0), [task], [], lambda *_args: True)
    dialog.show()

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    dialog.keyPressEvent(event)

    assert dialog.isVisible()


def test_enter_stays_open():
    app()
    task = Task("Coding", id=1, sessions=[Session(dt(9), dt(10))])
    dialog = TimelineEditorDialog(dt(0), [task], [], lambda *_args: True)
    dialog.show()

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
    dialog.keyPressEvent(event)

    assert dialog.isVisible()


def test_yes_discard_once(monkeypatch):
    app()
    task = Task("Coding", id=1, sessions=[Session(dt(9), dt(10))])
    dialog = TimelineEditorDialog(dt(0), [task], [], lambda *_args: True)
    dialog.show()
    dialog.add_slot()
    calls = []

    def fake_question(*_args):
        calls.append("question")
        return timeline_editor.QMessageBox.StandardButton.Yes

    monkeypatch.setattr(timeline_editor.QMessageBox, "question", fake_question)

    dialog.reject()
    dialog.close()

    assert calls == ["question"]


def test_save_skips_discard(monkeypatch):
    app()
    task = Task("Coding", id=1, sessions=[Session(dt(9), dt(10))])
    dialog = TimelineEditorDialog(dt(0), [task], [], lambda *_args: True)
    dialog.show()
    dialog.rows[0].end = dt(11)
    dialog._set_dirty(True)
    titles = []

    def fake_question(_parent, title, *_args):
        titles.append(title)
        return timeline_editor.QMessageBox.StandardButton.Yes

    monkeypatch.setattr(timeline_editor.QMessageBox, "question", fake_question)

    dialog.save_day()
    dialog.close()

    assert titles == ["Save Timeline"]


def test_time_typing_defers_carve():
    app()
    coding = Task("Coding", id=1, sessions=[Session(dt(9), dt(11))])
    admin = Task("Admin", id=2, sessions=[Session(dt(12), dt(13))])
    dialog = TimelineEditorDialog(dt(0), [coding, admin], [], lambda *_args: True)

    end_edit = dialog.table.cellWidget(0, 1)
    end_edit.setTime(dialog._to_time(dt(12, 30)))

    assert [(row.task_name, row.begin, row.end) for row in dialog.rows] == [
        ("Coding", dt(9), dt(11)),
        ("Admin", dt(12), dt(13)),
    ]


def test_row_change_carves():
    app()
    coding = Task("Coding", id=1, sessions=[Session(dt(9), dt(11))])
    admin = Task("Admin", id=2, sessions=[Session(dt(12), dt(13))])
    dialog = TimelineEditorDialog(dt(0), [coding, admin], [], lambda *_args: True)

    end_edit = dialog.table.cellWidget(0, 1)
    end_edit.setTime(dialog._to_time(dt(12, 30)))
    dialog._commit_end(dialog.rows[0], end_edit)

    assert [(row.task_name, row.begin, row.end) for row in dialog.rows] == [
        ("Coding", dt(9), dt(12, 30)),
        ("Admin", dt(12), dt(13)),
    ]

    dialog._activate_row(dialog.rows[1])

    assert [(row.task_name, row.begin, row.end) for row in dialog.rows] == [
        ("Coding", dt(9), dt(12, 30)),
        ("Admin", dt(12, 30), dt(13)),
    ]
