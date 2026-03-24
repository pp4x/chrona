from __future__ import annotations

from datetime import datetime
import re
import sqlite3

from Task import Session, Task


CATEGORY_PATTERN = re.compile(r"(?:^|\s)@([^\s#@]+)")
PROJECT_PATTERN = re.compile(r"(?:^|\s)#([^\s#@]+)")


def normalize_task_name(name: str) -> str:
    return " ".join(name.casefold().split())


def extract_category(name: str) -> str | None:
    match = CATEGORY_PATTERN.search(name)
    return match.group(1) if match else None


def extract_project(name: str) -> str | None:
    match = PROJECT_PATTERN.search(name)
    return match.group(1) if match else None


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list_active_tasks(self) -> list[Task]:
        return self._list_tasks("WHERE completed_at IS NULL")

    def list_completed_tasks(self) -> list[Task]:
        return self._list_tasks("WHERE completed_at IS NOT NULL")

    def get_task_by_normalized_name(self, name: str) -> Task | None:
        row = self.connection.execute(
            """
            SELECT id, name, normalized_name, category, project, created_at, completed_at
            FROM tasks
            WHERE normalized_name = ?
            """,
            (normalize_task_name(name),),
        ).fetchone()
        if row is None:
            return None
        return self._hydrate_task(row)

    def save_task(self, task: Task) -> Task:
        category = extract_category(task.name)
        project = extract_project(task.name)
        created_at = task.created_at or datetime.now()

        if task.id is None:
            cursor = self.connection.execute(
                """
                INSERT INTO tasks(name, normalized_name, category, project, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task.name,
                    normalize_task_name(task.name),
                    category,
                    project,
                    created_at.isoformat(),
                    self._iso_or_none(task.completed_at),
                ),
            )
            task.id = cursor.lastrowid
            task.created_at = created_at
        else:
            self.connection.execute(
                """
                UPDATE tasks
                SET name = ?, normalized_name = ?, category = ?, project = ?, created_at = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    task.name,
                    normalize_task_name(task.name),
                    category,
                    project,
                    created_at.isoformat(),
                    self._iso_or_none(task.completed_at),
                    task.id,
                ),
            )
            self.connection.execute("DELETE FROM sessions WHERE task_id = ?", (task.id,))

        for session in task.sessions:
            self.connection.execute(
                """
                INSERT INTO sessions(task_id, begin_at, end_at)
                VALUES (?, ?, ?)
                """,
                (
                    task.id,
                    session.begin.isoformat(),
                    self._iso_or_none(session.end),
                ),
            )

        self.connection.commit()
        task.category = category
        task.project = project
        return task

    def complete_task(self, task: Task, completed_at: datetime | None = None) -> Task:
        task.completed_at = completed_at or datetime.now()
        task.is_active = False
        return self.save_task(task)

    def restart_task(self, task: Task, started_at: datetime | None = None) -> Task:
        task.completed_at = None
        task.start_session(started_at)
        return self.save_task(task)

    def replace_sessions(self, task: Task, sessions: list[Session]) -> Task:
        task.sessions = sessions
        task.is_active = bool(sessions and sessions[-1].end is None)
        return self.save_task(task)

    def _list_tasks(self, where_clause: str) -> list[Task]:
        rows = self.connection.execute(
            f"""
            SELECT id, name, normalized_name, category, project, created_at, completed_at
            FROM tasks
            {where_clause}
            ORDER BY COALESCE(completed_at, created_at), name
            """
        ).fetchall()
        return [self._hydrate_task(row) for row in rows]

    def _hydrate_task(self, row: sqlite3.Row) -> Task:
        sessions = self._load_sessions(row["id"])
        task = Task(
            id=row["id"],
            name=row["name"],
            sessions=sessions,
            is_active=bool(sessions and sessions[-1].end is None),
            created_at=self._from_iso(row["created_at"]),
            completed_at=self._from_iso(row["completed_at"]),
            category=row["category"],
            project=row["project"],
        )
        return task

    def _load_sessions(self, task_id: int) -> list[Session]:
        rows = self.connection.execute(
            """
            SELECT begin_at, end_at
            FROM sessions
            WHERE task_id = ?
            ORDER BY begin_at
            """,
            (task_id,),
        ).fetchall()
        return [
            Session(
                begin=self._from_iso(row["begin_at"]),
                end=self._from_iso(row["end_at"]),
            )
            for row in rows
        ]

    @staticmethod
    def _iso_or_none(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _from_iso(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value is not None else None
