from datetime import datetime

from PySide6.QtWidgets import QApplication

from Task import Session, Task
from task_edit_dialog import TaskEditDialog


def app():
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    return inst


def dt(hour, minute=0, second=0):
    return datetime(2026, 4, 11, hour, minute, second)


def test_begin_keeps_orig():
    app()
    task = Task("demo", sessions=[Session(begin=dt(16, 20, 35), end=dt(16, 25, 19))])
    dlg = TaskEditDialog(task)

    assert dlg._begin_value(0) == dt(16, 20, 35)


def test_begin_revert_keeps_orig():
    app()
    task = Task("demo", sessions=[Session(begin=dt(16, 20, 35), end=dt(16, 25, 19))])
    dlg = TaskEditDialog(task)
    edit = dlg.sessions_table.cellWidget(0, 0)

    edit.setDateTime(dlg._to_qdatetime(dt(16, 22)))
    edit.setDateTime(dlg._to_qdatetime(dt(16, 20)))

    assert dlg._begin_value(0) == dt(16, 20, 35)


def test_begin_edit_snaps_min():
    app()
    task = Task("demo", sessions=[Session(begin=dt(16, 20, 35), end=dt(16, 25, 19))])
    dlg = TaskEditDialog(task)
    edit = dlg.sessions_table.cellWidget(0, 0)

    edit.setDateTime(dlg._to_qdatetime(dt(16, 21)))

    assert dlg._begin_value(0) == dt(16, 21)


def test_new_row_after_delete_snaps_min():
    app()
    task = Task("demo", sessions=[Session(begin=dt(16, 20, 35), end=dt(16, 25, 19))])
    dlg = TaskEditDialog(task)

    dlg.sessions_table.selectRow(0)
    dlg.delete_selected_sessions()
    dlg._insert_session_row(begin=dt(17, 10, 45), end=dt(17, 15, 12))

    assert dlg._begin_value(0) == dt(17, 10)
    assert dlg._end_value(0) == dt(17, 15)
