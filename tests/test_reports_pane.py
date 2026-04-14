import sqlite3
from datetime import datetime

from db import ensure_schema
from reports_pane import ReportDataAdapter


def make_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    ensure_schema(connection)
    return connection


def test_report_includes_sub_minute_task():
    connection = make_connection()
    connection.execute(
        """
        INSERT INTO tasks(name, normalized_name, category, project, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("Quick thing", "quick thing", None, None, "2026-03-24T09:00:00", None),
    )
    task_id = connection.execute("SELECT id FROM tasks").fetchone()["id"]
    connection.execute(
        """
        INSERT INTO sessions(task_id, begin_at, end_at)
        VALUES (?, ?, ?)
        """,
        (task_id, "2026-03-24T09:00:00", "2026-03-24T09:00:30"),
    )
    connection.commit()

    adapter = ReportDataAdapter(connection)

    report = adapter.get_report("Daily", datetime(2026, 3, 24), "All", "Task", "")
    headers, rows, total_seconds = adapter.get_detail_rows(
        "Daily",
        datetime(2026, 3, 24),
        "All",
        "",
        "Task",
        "Quick thing",
    )

    assert report == [{"name": "Quick thing", "time": 30.0}]
    assert headers == ["Date", "Begin", "End", "Duration"]
    assert rows == [["Mar 24", "09:00", "09:00", "0m"]]
    assert total_seconds == 30.0


def test_daily_timeline_report_is_sorted_by_time():
    connection = make_connection()
    connection.execute(
        """
        INSERT INTO tasks(name, normalized_name, category, project, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("Later task", "later task", None, None, "2026-03-24T11:00:00", None),
    )
    connection.execute(
        """
        INSERT INTO tasks(name, normalized_name, category, project, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("Earlier task", "earlier task", None, None, "2026-03-24T09:00:00", None),
    )
    task_rows = connection.execute("SELECT id, name FROM tasks").fetchall()
    task_ids = {row["name"]: row["id"] for row in task_rows}
    connection.executemany(
        """
        INSERT INTO sessions(task_id, begin_at, end_at)
        VALUES (?, ?, ?)
        """,
        [
            (task_ids["Later task"], "2026-03-24T11:15:00", "2026-03-24T11:45:00"),
            (task_ids["Earlier task"], "2026-03-24T09:30:00", "2026-03-24T10:00:00"),
        ],
    )
    connection.commit()

    adapter = ReportDataAdapter(connection)

    report = adapter.get_report("Daily", datetime(2026, 3, 24), "All", "Timeline", "")

    assert report == [
        {
            "task": "Earlier task",
            "begin": datetime(2026, 3, 24, 9, 30),
            "end": datetime(2026, 3, 24, 10, 0),
            "time": 1800.0,
            "end_display": "10:00",
        },
        {
            "task": "Later task",
            "begin": datetime(2026, 3, 24, 11, 15),
            "end": datetime(2026, 3, 24, 11, 45),
            "time": 1800.0,
            "end_display": "11:45",
        },
    ]
