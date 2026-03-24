from datetime import datetime

from Task import Session
from session_ops import normalize_sessions, subtract_interval


def dt(hour, minute=0):
    return datetime(2026, 3, 24, hour, minute)


def test_subtract_interval_without_overlap_keeps_session():
    sessions = [Session(begin=dt(9), end=dt(10))]

    updated = subtract_interval(sessions, dt(10), dt(11), dt(12))

    assert updated == [Session(begin=dt(9), end=dt(10))]


def test_subtract_interval_trims_left_edge():
    sessions = [Session(begin=dt(9), end=dt(12))]

    updated = subtract_interval(sessions, dt(9), dt(10), dt(12))

    assert updated == [Session(begin=dt(10), end=dt(12))]


def test_subtract_interval_trims_right_edge():
    sessions = [Session(begin=dt(9), end=dt(12))]

    updated = subtract_interval(sessions, dt(11), dt(12), dt(12))

    assert updated == [Session(begin=dt(9), end=dt(11))]


def test_subtract_interval_splits_middle():
    sessions = [Session(begin=dt(9), end=dt(12))]

    updated = subtract_interval(sessions, dt(10), dt(11), dt(12))

    assert updated == [
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(11), end=dt(12)),
    ]


def test_subtract_interval_removes_fully_covered_session():
    sessions = [Session(begin=dt(9), end=dt(10))]

    updated = subtract_interval(sessions, dt(8), dt(11), dt(12))

    assert updated == []


def test_normalize_sessions_merges_touching_segments_after_subtraction():
    sessions = [
        Session(begin=dt(9), end=dt(10)),
        Session(begin=dt(10), end=dt(11)),
    ]

    normalized = normalize_sessions(sessions, dt(12))

    assert normalized == [Session(begin=dt(9), end=dt(11))]
