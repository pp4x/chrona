from datetime import datetime

from Task import Session
from session_ops import coalesce_sessions, normalize_sessions, subtract_interval, trim_sessions


def dt(hour, minute=0):
    return datetime(2026, 3, 24, hour, minute)


def test_subtract_keeps_session():
    """A non-overlapping interval leaves the session unchanged."""
    sessions = [Session(begin=dt(9), end=dt(10))]

    updated = subtract_interval(sessions, dt(10), dt(11), dt(12))

    assert updated == [Session(begin=dt(9), end=dt(10))]


def test_subtract_trims_left():
    """Subtracting the left edge shifts the session start forward."""
    sessions = [Session(begin=dt(9), end=dt(12))]

    updated = subtract_interval(sessions, dt(9), dt(10), dt(12))

    assert updated == [Session(begin=dt(10), end=dt(12))]


def test_subtract_trims_right():
    """Subtracting the right edge shortens the session end."""
    sessions = [Session(begin=dt(9), end=dt(12))]

    updated = subtract_interval(sessions, dt(11), dt(12), dt(12))

    assert updated == [Session(begin=dt(9), end=dt(11))]


def test_subtract_splits_middle():
    """Subtracting from the middle splits the session into two parts."""
    sessions = [Session(begin=dt(9), end=dt(12))]

    updated = subtract_interval(sessions, dt(10), dt(11), dt(12))

    assert updated == [
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(11), end=dt(12)),
    ]


def test_subtract_removes_session():
    """A fully covered session is removed entirely."""
    sessions = [Session(begin=dt(9), end=dt(10))]

    updated = subtract_interval(sessions, dt(8), dt(11), dt(12))

    assert updated == []


def test_trim_sessions_cuts_all():
    sessions = [Session(begin=dt(9), end=dt(15))]
    cuts = [
        Session(begin=dt(10), end=dt(11)),
        Session(begin=dt(13), end=dt(14)),
    ]

    updated = trim_sessions(sessions, cuts, dt(16))

    assert updated == [
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(11), end=dt(13)),
        Session(begin=dt(14), end=dt(15)),
    ]


def test_normalize_keeps_touching():
    """Touching segments remain separate."""
    sessions = [
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(10), end=dt(11)),
    ]

    normalized = normalize_sessions(sessions, dt(12))

    assert normalized == [
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(10), end=dt(11)),
    ]


def test_normalize_keeps_adjacent_sessions():
    """Adjacent sessions remain separate instead of expanding the earlier begin."""
    sessions = [
        Session(begin=dt(8, 30), end=dt(9)),
        Session(begin=dt(9), end=dt(9, 30)),
    ]

    normalized = normalize_sessions(sessions, dt(12))

    assert normalized == sessions


def test_coalesce_sessions_spans_selected_range():
    merged = coalesce_sessions(
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(11), end=dt(12)),
    )

    assert merged == Session(begin=dt(9), end=dt(12))


def test_coalesce_sessions_keeps_open_end():
    merged = coalesce_sessions(
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(11), end=None),
    )

    assert merged == Session(begin=dt(9), end=None)
