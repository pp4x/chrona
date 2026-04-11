from datetime import datetime

import Task as task_module

from Task import Session, Task


class FrozenDateTime(datetime):
    current = datetime(2026, 3, 25, 10, 0, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.current if tz is None else tz.fromutc(cls.current)


def test_start_and_stop_keep_full_precision():
    task = Task("demo")
    start = datetime(2026, 3, 24, 10, 0, 45, 123456)
    stop = datetime(2026, 3, 24, 10, 1, 5, 654321)

    task.start_session(start)
    task.stop_session(stop)

    assert task.sessions == [Session(begin=start, end=stop)]


def test_start_session_does_not_merge_same_minute_timestamps():
    task = Task(
        "demo",
        sessions=[
            Session(
                begin=datetime(2026, 3, 24, 9, 0, 0),
                end=datetime(2026, 3, 24, 10, 0, 15),
            )
        ],
    )

    task.start_session(datetime(2026, 3, 24, 10, 0, 50))

    assert task.sessions == [
        Session(
            begin=datetime(2026, 3, 24, 9, 0, 0),
            end=datetime(2026, 3, 24, 10, 0, 15),
        ),
        Session(begin=datetime(2026, 3, 24, 10, 0, 50)),
    ]


def test_has_today_activity_for_sub_minute_session(monkeypatch):
    monkeypatch.setattr(task_module, "datetime", FrozenDateTime)
    task = Task(
        "demo",
        sessions=[
            Session(
                begin=datetime(2026, 3, 25, 9, 0, 0),
                end=datetime(2026, 3, 25, 9, 0, 30),
            )
        ],
    )

    assert task.today_time == 0
    assert task.today_seconds == 30.0
    assert task.has_today_activity is True


def test_total_seconds_keeps_sub_minute_precision():
    task = Task(
        "demo",
        sessions=[
            Session(
                begin=datetime(2026, 3, 24, 9, 0, 0),
                end=datetime(2026, 3, 24, 9, 0, 30),
            ),
            Session(
                begin=datetime(2026, 3, 24, 10, 0, 0),
                end=datetime(2026, 3, 24, 10, 0, 45),
            ),
        ],
    )

    assert task.total_time == 1
    assert task.total_seconds == 75.0


def test_view_today_secs_xmid(monkeypatch):
    monkeypatch.setattr(task_module, "datetime", FrozenDateTime)
    task = Task(
        "demo",
        sessions=[
            Session(
                begin=datetime(2026, 3, 24, 23, 30, 0),
                end=datetime(2026, 3, 25, 1, 0, 0),
            )
        ],
    )

    assert task.today_seconds == 3600.0
    assert task.view_today_secs == 5400.0
    assert task.has_view_today is True


def test_view_today_secs_open(monkeypatch):
    monkeypatch.setattr(task_module, "datetime", FrozenDateTime)
    task = Task(
        "demo",
        sessions=[
            Session(begin=datetime(2026, 3, 24, 23, 30, 0), end=None)
        ],
    )

    assert task.today_seconds == 36000.0
    assert task.view_today_secs == 37800.0
    assert task.view_today_mins == 630


def test_view_today_secs_old(monkeypatch):
    monkeypatch.setattr(task_module, "datetime", FrozenDateTime)
    task = Task(
        "demo",
        sessions=[
            Session(
                begin=datetime(2026, 3, 23, 23, 30, 0),
                end=datetime(2026, 3, 24, 1, 0, 0),
            )
        ],
    )

    assert task.today_seconds == 0.0
    assert task.view_today_secs == 0.0
    assert task.has_view_today is False
