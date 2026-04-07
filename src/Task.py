
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class Session:
    begin: datetime
    end: Optional[datetime] = None

@dataclass
class Task:
    name: str  # Full normalized task string, includes @category and #project if present
    id: Optional[int] = None
    sessions: List[Session] = field(default_factory=list)
    is_active: bool = False
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    category: Optional[str] = None  # Extracted from @category
    project: Optional[str] = None   # Extracted from #project

    def start_session(self, start: Optional[datetime] = None):
        if start is None:
            start = datetime.now()
        if self.sessions:
            previous_session = self.sessions[-1]
            if previous_session.end is not None and previous_session.end == start:
                previous_session.end = None
                self.is_active = True
                return
        self.sessions.append(Session(begin=start))
        self.is_active = True

    def stop_session(self, stop: Optional[datetime] = None):
        if stop is None:
            stop = datetime.now()
        if self.sessions and self.sessions[-1].end is None:
            self.sessions[-1].end = stop
        self.is_active = False

    def _last_session(self) -> Optional[Session]:
        if not self.sessions:
            return None
        return self.sessions[-1]

    def _today_start(self) -> datetime:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    @property
    def total_time(self) -> int:
        """Total time in minutes across all sessions."""
        total = 0
        for session in self.sessions:
            end = session.end if session.end is not None else datetime.now()
            seconds = int((end - session.begin).total_seconds())
            total += (seconds // 60)
        return total

    def minutes_since(self, period_start: datetime, period_end: Optional[datetime] = None) -> int:
        total = 0
        now = datetime.now()
        effective_period_end = period_end or now

        for session in self.sessions:
            session_end = session.end if session.end is not None else now
            overlap_begin = max(session.begin, period_start)
            overlap_end = min(session_end, effective_period_end)
            if overlap_begin >= overlap_end:
                continue
            total += int((overlap_end - overlap_begin).total_seconds()) // 60

        return total

    def overlaps_period(self, period_start: datetime, period_end: Optional[datetime] = None) -> bool:
        now = datetime.now()
        effective_period_end = period_end or now

        for session in self.sessions:
            session_end = session.end if session.end is not None else now
            overlap_begin = max(session.begin, period_start)
            overlap_end = min(session_end, effective_period_end)
            if overlap_begin < overlap_end:
                return True

        return False

    @property
    def today_time(self) -> int:
        return self.minutes_since(self._today_start())

    @property
    def has_today_activity(self) -> bool:
        return self.overlaps_period(self._today_start())

    @property
    def last_activity(self) -> Optional[datetime]:
        last = self._last_session()
        if last is None:
            return None
        return last.end if last.end else last.begin

    @property
    def last_activity_type(self) -> Optional[str]:
        last = self._last_session()
        if last is None:
            return None

        return "pause" if last.end else ("resume" if len(self.sessions) > 1 else "started")

    @property
    def last_activity_display(self) -> str:
        session = self._last_session()
        if session is not None:
            today = datetime.now().date()
            prefix = ""
            if session.begin.date() != today:
                prefix = f"{session.begin.strftime('%b %d')} "
            begin = session.begin.strftime('%H:%M')
            end = session.end.strftime('%H:%M') if session.end else 'Now'
            return f"{prefix}{begin} - {end}"
        return ""
