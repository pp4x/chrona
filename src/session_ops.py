from __future__ import annotations

from datetime import datetime

from Task import Session


def effective_end(session: Session, now: datetime) -> datetime:
    return session.end or now


def normalize_sessions(sessions: list[Session], now: datetime) -> list[Session]:
    ordered = sorted(
        sessions,
        key=lambda session: (effective_end(session, now), session.begin),
    )

    merged = []
    for session in ordered:
        if not merged:
            merged.append(Session(begin=session.begin, end=session.end))
            continue

        previous = merged[-1]
        previous_end = effective_end(previous, now)

        if session.begin < previous_end:
            previous.begin = min(previous.begin, session.begin)
            if previous.end is None or session.end is None:
                previous.end = None
            else:
                previous.end = max(previous.end, session.end)
            continue

        merged.append(Session(begin=session.begin, end=session.end))

    return merged


def subtract_interval(
    sessions: list[Session],
    overlap_begin: datetime,
    overlap_end: datetime,
    now: datetime,
) -> list[Session]:
    updated_sessions = []

    for session in sessions:
        session_end = effective_end(session, now)
        if session.begin >= overlap_end or session_end <= overlap_begin:
            updated_sessions.append(Session(begin=session.begin, end=session.end))
            continue

        if session.begin < overlap_begin:
            left_end = min(overlap_begin, session_end)
            if left_end > session.begin:
                updated_sessions.append(Session(begin=session.begin, end=left_end))

        if session_end > overlap_end:
            right_begin = max(overlap_end, session.begin)
            right_end = session.end
            if right_end is None or right_end > right_begin:
                updated_sessions.append(Session(begin=right_begin, end=right_end))

    return updated_sessions
