from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from PySide6.QtCore import QEvent, Qt, QTime
from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from Task import Session, Task
from formatting import format_seconds_as_minutes as fmt_minutes
from repository import normalize_task_name
from session_ops import effective_end, trim_sessions


def day_bounds(day_start: datetime) -> tuple[datetime, datetime]:
    start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def display_name(value: str) -> str:
    return " ".join(value.split())


@dataclass
class TimelineRow:
    task_name: str
    begin: datetime
    end: datetime
    status: str = ""
    read_only: bool = False
    origin_task_id: int | None = None
    original_begin: datetime | None = None
    original_end: datetime | None = None
    touched_begin: bool = False
    touched_end: bool = False
    sequence: int = 0

    @property
    def is_zero_length(self) -> bool:
        return self.begin == self.end

    @property
    def duration_seconds(self) -> float:
        return max(0.0, (self.end - self.begin).total_seconds())


class TaskNameIndex:
    def __init__(self, active_tasks: list[Task], completed_tasks: list[Task], new_names: list[str] | None = None):
        self.active_names = self._unique_names(active_tasks)
        self.completed_names = self._unique_names(completed_tasks)
        self.new_names = self._unique_strings(new_names or [], sort_values=False)
        self._canonical = {}
        for name in self.active_names + self.completed_names + self.new_names:
            self._canonical.setdefault(normalize_task_name(name), name)

    def canonicalize(self, value: str) -> str:
        name = display_name(value)
        if not name:
            return ""
        normalized = normalize_task_name(name)
        canonical = self._canonical.get(normalized)
        if canonical is not None:
            return canonical
        self._canonical[normalized] = name
        self.new_names.append(name)
        return name

    def groups(self) -> list[tuple[str, list[str]]]:
        return [
            ("Active", self.active_names),
            ("Completed", self.completed_names),
            ("New", self.new_names),
        ]

    def refreshed(self, rows: list[TimelineRow]) -> TaskNameIndex:
        new_names = list(self.new_names)
        existing = {normalize_task_name(name) for name in self.active_names + self.completed_names}
        for row in rows:
            name = display_name(row.task_name)
            if not name:
                continue
            normalized = normalize_task_name(name)
            if normalized not in existing and normalized not in {normalize_task_name(n) for n in new_names}:
                new_names.append(name)
        return TaskNameIndex(
            [Task(name=name) for name in self.active_names],
            [Task(name=name) for name in self.completed_names],
            new_names,
        )

    @staticmethod
    def _unique_names(tasks: list[Task]) -> list[str]:
        return TaskNameIndex._unique_strings([task.name for task in tasks])

    @staticmethod
    def _unique_strings(names: list[str], sort_values: bool = True) -> list[str]:
        seen = set()
        unique = []
        cleaned_names = [display_name(value) for value in names if display_name(value)]
        if sort_values:
            cleaned_names = sorted(set(cleaned_names), key=str.casefold)
        for name in cleaned_names:
            normalized = normalize_task_name(name)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(name)
        return unique


def rows_for_day(tasks: list[Task], day_start: datetime, now: datetime) -> list[TimelineRow]:
    start, end = day_bounds(day_start)
    rows = []
    sequence = 0
    for task in tasks:
        for session in task.sessions:
            session_end = effective_end(session, now)
            overlap_begin = max(session.begin, start)
            overlap_end = min(session_end, end)
            if overlap_begin >= overlap_end:
                continue
            read_only = session.end is None
            rows.append(
                TimelineRow(
                    task_name=task.name,
                    begin=overlap_begin,
                    end=now if read_only else overlap_end,
                    status="Current" if read_only else "",
                    read_only=read_only,
                    origin_task_id=task.id,
                    original_begin=session.begin,
                    original_end=session.end,
                    sequence=sequence,
                )
            )
            sequence += 1
    return sort_rows(rows)


def sort_rows(rows: list[TimelineRow]) -> list[TimelineRow]:
    return sorted(rows, key=lambda row: (row.begin, row.end, row.sequence, row.task_name.casefold()))


def dedupe_rows(rows: list[TimelineRow]) -> list[TimelineRow]:
    seen = set()
    result = []
    for row in rows:
        key = (normalize_task_name(row.task_name), row.begin, row.end, row.read_only)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def editable_save_rows(rows: list[TimelineRow]) -> list[TimelineRow]:
    return [
        row
        for row in dedupe_rows(sort_rows(rows))
        if not row.read_only and not row.is_zero_length
    ]


def has_save_changes(original_rows: list[TimelineRow], current_rows: list[TimelineRow]) -> bool:
    return _save_signature(original_rows) != _save_signature(current_rows)


def _save_signature(rows: list[TimelineRow]):
    return [
        (
            normalize_task_name(row.task_name),
            row.begin,
            row.end,
            row.read_only,
        )
        for row in editable_save_rows(rows)
    ]


def carve_rows(
    rows: list[TimelineRow],
    authoritative: TimelineRow,
    task_index: TaskNameIndex,
) -> tuple[list[TimelineRow], bool]:
    if authoritative.read_only or authoritative.is_zero_length:
        return sort_rows(rows), False

    changed_protected = False
    updated = []
    merged = authoritative
    authoritative_seen = False

    for row in rows:
        if row is authoritative:
            authoritative_seen = True
            continue
        if row.end <= merged.begin or row.begin >= merged.end or row.is_zero_length:
            updated.append(row)
            continue

        if row.read_only:
            changed_protected = True
            if merged.begin < row.begin:
                merged = replace(merged, end=row.begin)
            updated.append(row)
            continue

        if normalize_task_name(row.task_name) == normalize_task_name(merged.task_name):
            canonical_name = task_index.canonicalize(merged.task_name)
            merged = replace(
                merged,
                task_name=canonical_name,
                begin=min(row.begin, merged.begin),
                end=max(row.end, merged.end),
            )
            continue

        if row.begin < merged.begin:
            updated.append(replace(row, end=merged.begin))
        if row.end > merged.end:
            updated.append(replace(row, begin=merged.end))

    if authoritative_seen and not merged.is_zero_length:
        updated.append(merged)
    elif authoritative_seen:
        updated.append(merged)
    return sort_rows([row for row in updated if not (row.is_zero_length and row is not merged)]), changed_protected


def apply_rows_to_tasks(
    active_tasks: list[Task],
    completed_tasks: list[Task],
    day_start: datetime,
    rows: list[TimelineRow],
    now: datetime,
) -> list[Task]:
    start, end = day_bounds(day_start)
    all_tasks = list(active_tasks) + list(completed_tasks)
    by_name = {normalize_task_name(task.name): task for task in all_tasks}
    changed = []
    changed_ids = set()
    protected_intervals = [Session(row.begin, end) for row in rows if row.read_only]
    cut_intervals = trim_sessions([Session(start, end)], protected_intervals, now)

    for task in all_tasks:
        updated_sessions = trim_sessions(task.sessions, cut_intervals, now)
        if updated_sessions != task.sessions:
            task.sessions = updated_sessions
            task.is_active = bool(task.sessions and task.sessions[-1].end is None)
            changed.append(task)
            changed_ids.add(id(task))

    for row in editable_save_rows(rows):
        task_name = display_name(row.task_name)
        normalized = normalize_task_name(task_name)
        task = by_name.get(normalized)
        created = False
        if task is None:
            created = True
            task = Task(name=task_name)
            all_tasks.append(task)
            by_name[normalized] = task

        task.sessions = sort_sessions(task.sessions + [Session(row.begin, row.end)])
        task.is_active = bool(task.sessions and task.sessions[-1].end is None)
        if created and start.date() < now.date():
            task.completed_at = row.end
        if created and start.date() == now.date():
            task.completed_at = None
        if created or id(task) not in changed_ids:
            changed.append(task)
            changed_ids.add(id(task))

    for task in changed:
        if task.id is None and task.completed_at is not None:
            task.completed_at = max((session.end or now) for session in task.sessions)
    return changed


def sort_sessions(sessions: list[Session]) -> list[Session]:
    return sorted(sessions, key=lambda session: (session.begin, session.end or datetime.max))


class TaskChoiceDialog(QDialog):
    def __init__(self, task_index: TaskNameIndex, current_name: str, parent=None):
        super().__init__(parent)
        self.task_index = task_index
        self.setWindowTitle("Choose Task")
        self.resize(480, 420)

        layout = QVBoxLayout(self)
        self.input = QLineEdit(display_name(current_name))
        self.input.setPlaceholderText("Type a task name")
        self.input.textChanged.connect(self._refresh_list)
        layout.addWidget(self.input)

        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self._choose_item)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_list(self.input.text())
        self.input.setFocus(Qt.OtherFocusReason)

    def selected_name(self) -> str:
        return display_name(self.input.text())

    def _choose_item(self, item):
        value = item.data(Qt.UserRole)
        if value:
            self.input.setText(value)

    def _refresh_list(self, value: str):
        normalized_value = normalize_task_name(value)
        self.list_widget.clear()
        for label, names in self.task_index.groups():
            filtered = [
                name
                for name in names
                if not normalized_value or normalize_task_name(name).startswith(normalized_value)
            ]
            if not filtered:
                continue
            header = f"{label}"
            self.list_widget.addItem(header)
            self.list_widget.item(self.list_widget.count() - 1).setFlags(Qt.NoItemFlags)
            for name in filtered:
                self.list_widget.addItem(name)
                self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, name)


class TimelineEditorDialog(QDialog):
    def __init__(self, day_start: datetime, active_tasks: list[Task], completed_tasks: list[Task], save_handler, parent=None):
        super().__init__(parent)
        self.day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
        self.active_tasks = active_tasks
        self.completed_tasks = completed_tasks
        self.save_handler = save_handler
        self.now = datetime.now()
        self.task_index = TaskNameIndex(active_tasks, completed_tasks)
        self._next_sequence = 10_000
        self._loading = False
        self._close_allowed = False
        self._active_row = None
        self._pending_row = None

        self.setWindowTitle(f"Edit Timeline - {self.day_start.strftime('%b %d, %Y')}")
        self.resize(860, 520)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["Begin", "End", "Duration", "Task", "Status"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.add_btn = QPushButton("Add Slot")
        self.add_btn.clicked.connect(self.add_slot)
        self.delete_btn = QPushButton("Delete Slot")
        self.delete_btn.clicked.connect(self.delete_slots)
        self.duplicate_btn = QPushButton("Duplicate Slot")
        self.duplicate_btn.clicked.connect(self.duplicate_slot)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_day)
        actions.addWidget(self.add_btn)
        actions.addWidget(self.delete_btn)
        actions.addWidget(self.duplicate_btn)
        actions.addStretch()
        actions.addWidget(self.reset_btn)
        layout.addLayout(actions)

        self.total_label = QLabel()
        layout.addWidget(self.total_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.save_day)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.save_btn = buttons.button(QDialogButtonBox.Save)
        self.save_btn.setDefault(False)
        self.save_btn.setAutoDefault(False)
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)

        self.delete_shortcut = QShortcut(QKeySequence(QKeySequence.Delete), self)
        self.delete_shortcut.activated.connect(self.delete_slots)

        self.original_rows = rows_for_day(active_tasks + completed_tasks, self.day_start, self.now)
        self.rows = [replace(row) for row in self.original_rows]
        self._render_rows()
        self._set_dirty(False)

    def add_slot(self):
        row = self._new_placeholder()
        selected_row = self._single_index()
        if selected_row is not None:
            gap = self._gap_around(selected_row)
            if gap is not None:
                row.begin, row.end = gap
            else:
                boundary = self.rows[selected_row].end
                row.begin = boundary
                row.end = boundary
        self.rows.append(row)
        self.rows = sort_rows(self.rows)
        self._render_rows(select_row=row)
        self._set_dirty(True)

    def duplicate_slot(self):
        selected_row = self._single_selected_row()
        if selected_row is None or selected_row.read_only:
            return
        boundary = selected_row.end
        row = TimelineRow(
            task_name=selected_row.task_name,
            begin=boundary,
            end=boundary,
            sequence=self._take_sequence(),
        )
        self.rows.append(row)
        self.rows = sort_rows(self.rows)
        self._render_rows(select_row=row)
        self._set_dirty(True)

    def delete_slots(self):
        selected_indexes = self._selected_indexes()
        if not selected_indexes or any(self.rows[index].read_only for index in selected_indexes):
            return
        self.rows = [row for index, row in enumerate(self.rows) if index not in selected_indexes]
        self._render_rows()
        self._set_dirty(True)

    def reset_day(self):
        if not self.reset_btn.isEnabled():
            return
        result = QMessageBox.question(
            self,
            "Reset Timeline",
            "Discard unsaved edits and reload this day?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        self.rows = [replace(row) for row in self.original_rows]
        self._render_rows()
        self._set_dirty(False)

    def save_day(self):
        self._sync_active_row()
        self._commit_pending()
        rows = editable_save_rows(self.rows)
        for row in rows:
            if not display_name(row.task_name):
                QMessageBox.warning(self, "Invalid Timeline", "Non-zero slots need a task name.")
                return
        result = QMessageBox.question(
            self,
            "Save Timeline",
            f"Save changes to {self.day_start.strftime('%b %d, %Y')}? "
            "The timeline layout shown here will become the final layout for this day.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        if not self.save_handler(self.day_start, self.rows, self.active_tasks, self.completed_tasks):
            return
        self._set_dirty(False)
        self._close_allowed = True
        self.accept()

    def reject(self):
        self.done(QDialog.Rejected)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
            event.accept()
            return
        super().keyPressEvent(event)

    def done(self, result):
        if result == QDialog.Accepted:
            self._close_allowed = True
        if result == QDialog.Rejected and not self._close_allowed and not self._confirm_discard():
            return
        if result == QDialog.Rejected:
            self._set_dirty(False)
            self._close_allowed = True
        super().done(result)

    def closeEvent(self, event):
        if self._close_allowed or not self.isVisible():
            super().closeEvent(event)
            return
        if not self._confirm_discard():
            event.ignore()
            return
        self._close_allowed = True
        try:
            super().closeEvent(event)
        finally:
            self._close_allowed = False

    def _confirm_discard(self):
        if not self.reset_btn.isEnabled():
            return True
        result = QMessageBox.question(
            self,
            "Discard Edits",
            "Discard unsaved timeline edits?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _render_rows(self, select_row: TimelineRow | None = None):
        self._loading = True
        self._pending_row = None
        self.table.setRowCount(0)
        for row in self.rows:
            self._insert_row(row)
        self._loading = False
        self._refresh_total()
        self._refresh_actions()
        self._refresh_save_state()
        if select_row is not None:
            try:
                self.table.selectRow(self._row_index(select_row))
            except ValueError:
                pass

    def _insert_row(self, row: TimelineRow):
        index = self.table.rowCount()
        self.table.insertRow(index)

        begin_edit = self._time_edit(row.begin)
        begin_edit.setEnabled(not row.read_only)
        self._track_widget(begin_edit, row)
        begin_edit.timeChanged.connect(lambda _time: self._preview_total())
        begin_edit.editingFinished.connect(lambda item=row, editor=begin_edit: self._commit_begin(item, editor))
        self.table.setCellWidget(index, 0, begin_edit)

        end_edit = self._time_edit(row.end)
        end_edit.setEnabled(not row.read_only)
        self._track_widget(end_edit, row)
        end_edit.timeChanged.connect(lambda _time: self._preview_total())
        end_edit.editingFinished.connect(lambda item=row, editor=end_edit: self._commit_end(item, editor))
        self.table.setCellWidget(index, 1, end_edit)

        self.table.setItem(index, 2, self._label_item(fmt_minutes(row.duration_seconds)))

        task_widget = self._task_widget(row)
        self.table.setCellWidget(index, 3, task_widget)

        status = row.status
        self.table.setItem(index, 4, self._label_item(status))

    def _task_widget(self, row: TimelineRow):
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        line = QLineEdit(row.task_name)
        line.setEnabled(not row.read_only)
        self._track_widget(line, row)
        line.editingFinished.connect(lambda item=row, editor=line: self._on_task_finished(item, editor))
        choose = QPushButton("...")
        choose.setEnabled(not row.read_only)
        self._track_widget(choose, row)
        choose.clicked.connect(lambda _checked=False, item=row, editor=line: self._choose_task(item, editor))
        layout.addWidget(line)
        layout.addWidget(choose)
        return widget

    def _label_item(self, value: str):
        from PySide6.QtWidgets import QTableWidgetItem

        item = QTableWidgetItem(value)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return item

    def _time_edit(self, value: datetime):
        edit = QTimeEdit(self)
        edit.setDisplayFormat("HH:mm")
        edit.setTime(self._to_time(value))
        return edit

    def _to_time(self, value: datetime):
        return QTime(value.hour, value.minute)

    def _track_widget(self, widget, row: TimelineRow):
        widget.setProperty("timeline_row", row)
        widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.FocusIn and not self._loading:
            row = watched.property("timeline_row")
            if isinstance(row, TimelineRow):
                self._activate_row(row)
        return super().eventFilter(watched, event)

    def _activate_row(self, row: TimelineRow):
        if self._active_row is not row:
            self._commit_pending(except_row=row)
        self._active_row = row

    def _commit_begin(self, row: TimelineRow, edit: QTimeEdit):
        if self._loading:
            return
        new_begin = self._begin_datetime(edit.time())
        if row.begin == new_begin:
            return
        row.begin = new_begin
        row.touched_begin = True
        self._mark_row_dirty(row)

    def _commit_end(self, row: TimelineRow, edit: QTimeEdit):
        if self._loading:
            return
        new_end = self._end_datetime(row.begin, edit.time())
        if row.end == new_end:
            return
        row.end = new_end
        row.touched_end = True
        self._mark_row_dirty(row)

    def _on_task_finished(self, row: TimelineRow, editor: QLineEdit):
        if self._loading:
            return
        canonical = self.task_index.canonicalize(editor.text())
        editor.setText(canonical)
        row.task_name = canonical
        self.task_index = self.task_index.refreshed(self.rows)
        self._mark_row_dirty(row)

    def _choose_task(self, row: TimelineRow, editor: QLineEdit):
        dialog = TaskChoiceDialog(self.task_index.refreshed(self.rows), editor.text(), self)
        if dialog.exec() != QDialog.Accepted:
            return
        canonical = self.task_index.canonicalize(dialog.selected_name())
        editor.setText(canonical)
        row.task_name = canonical
        self.task_index = self.task_index.refreshed(self.rows)
        self._mark_row_dirty(row)

    def _mark_row_dirty(self, row: TimelineRow):
        self._pending_row = row
        self._set_dirty(True)
        self._refresh_total()

    def _commit_pending(self, except_row: TimelineRow | None = None):
        row = self._pending_row
        if row is None or row is except_row:
            return
        self._pending_row = None
        if not self._has_row(row):
            return
        self._apply_row(row)

    def _apply_row(self, row: TimelineRow):
        if row.end < row.begin:
            row.end = row.begin
        self.rows, trimmed_current = carve_rows(self.rows, row, self.task_index)
        self.rows = sort_rows(self.rows)
        self._render_rows(select_row=row if self._has_row(row) else None)
        self._set_dirty(True)
        if trimmed_current:
            QMessageBox.information(
                self,
                "Current Session Protected",
                "The edited slot was trimmed to avoid the current running session.",
            )

    def _sync_active_row(self):
        row = self._active_row
        if row is None or not self._has_row(row):
            return
        index = self._row_index(row)
        begin_edit = self.table.cellWidget(index, 0)
        end_edit = self.table.cellWidget(index, 1)
        if begin_edit is not None:
            row.begin = self._begin_datetime(begin_edit.time())
        if end_edit is not None:
            row.end = self._end_datetime(row.begin, end_edit.time())
        task_widget = self.table.cellWidget(index, 3)
        if task_widget is not None:
            line = task_widget.layout().itemAt(0).widget()
            row.task_name = self.task_index.canonicalize(line.text())
        self._pending_row = row

    def _begin_datetime(self, time: QTime):
        return self.day_start.replace(hour=time.hour(), minute=time.minute(), second=0, microsecond=0)

    def _end_datetime(self, begin: datetime, time: QTime):
        value = self.day_start.replace(hour=time.hour(), minute=time.minute(), second=0, microsecond=0)
        if time.hour() == 0 and time.minute() == 0 and begin > self.day_start:
            return self.day_start + timedelta(days=1)
        return value

    def _new_placeholder(self):
        boundary = self.day_start
        if self.rows:
            boundary = self.rows[-1].end
        return TimelineRow(task_name="", begin=boundary, end=boundary, sequence=self._take_sequence())

    def _gap_around(self, index: int) -> tuple[datetime, datetime] | None:
        row = self.rows[index]
        if index + 1 < len(self.rows):
            next_row = self.rows[index + 1]
            if not next_row.read_only and row.end < next_row.begin:
                return row.end, next_row.begin
            if next_row.read_only and row.end < next_row.begin:
                return row.end, next_row.begin
        if index > 0:
            previous = self.rows[index - 1]
            if previous.end < row.begin:
                return previous.end, row.begin
        return None

    def _selected_indexes(self):
        return sorted({index.row() for index in self.table.selectionModel().selectedRows()})

    def _single_index(self):
        indexes = self._selected_indexes()
        if len(indexes) != 1:
            return None
        return indexes[0]

    def _single_selected_row(self):
        index = self._single_index()
        if index is None:
            return None
        return self.rows[index]

    def _row_index(self, row: TimelineRow):
        for index, item in enumerate(self.rows):
            if item is row:
                return index
        raise ValueError("row is not in timeline")

    def _has_row(self, row: TimelineRow):
        return any(item is row for item in self.rows)

    def _on_selection_changed(self, *_args):
        selected_row = self._single_selected_row()
        if selected_row is not None:
            self._activate_row(selected_row)
        self._refresh_actions()

    def _refresh_total(self):
        total = sum(row.duration_seconds for row in self.rows if not row.is_zero_length)
        self.total_label.setText(f"Total: {fmt_minutes(total)}")
        for index, row in enumerate(self.rows):
            item = self.table.item(index, 2)
            if item is not None:
                item.setText(fmt_minutes(row.duration_seconds))

    def _preview_total(self):
        if self._loading:
            return
        total = 0.0
        for index, row in enumerate(self.rows):
            begin = self._begin_datetime(self.table.cellWidget(index, 0).time())
            end = self._end_datetime(begin, self.table.cellWidget(index, 1).time())
            seconds = max(0.0, (end - begin).total_seconds())
            total += seconds
            item = self.table.item(index, 2)
            if item is not None:
                item.setText(fmt_minutes(seconds))
        self.total_label.setText(f"Total: {fmt_minutes(total)}")

    def _refresh_actions(self):
        indexes = self._selected_indexes()
        selected_rows = [self.rows[index] for index in indexes]
        contains_read_only = any(row.read_only for row in selected_rows)
        self.delete_btn.setEnabled(bool(selected_rows) and not contains_read_only)
        self.duplicate_btn.setEnabled(len(selected_rows) == 1 and not selected_rows[0].read_only)
        self.delete_shortcut.setEnabled(self.delete_btn.isEnabled())

    def _refresh_save_state(self):
        self.save_btn.setEnabled(has_save_changes(self.original_rows, self.rows))

    def _set_dirty(self, dirty: bool):
        self.reset_btn.setEnabled(dirty)
        self._refresh_save_state()

    def _take_sequence(self):
        self._next_sequence += 1
        return self._next_sequence
