from datetime import datetime

from Task import Session, Task


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


def test_has_today_activity_for_sub_minute_session():
    task = Task(
        "demo",
        sessions=[
            Session(
                begin=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                end=datetime.now().replace(hour=9, minute=0, second=30, microsecond=0),
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
