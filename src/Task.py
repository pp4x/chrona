
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timedelta

@dataclass
class Session:
    begin: datetime
    end: Optional[datetime] = None

def truncate_to_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)

@dataclass
class Task:
    name: str  # Full normalized task string, includes @category and #project if present
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
            if previous_session.end is not None and truncate_to_minute(previous_session.end) == truncate_to_minute(start):
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

    @property
    def total_time(self) -> int:
        """Total time in minutes across all sessions."""
        total = 0
        for session in self.sessions:
            end = session.end if session.end is not None else datetime.now()
            seconds = int((end - session.begin).total_seconds())
            total += (seconds // 60)
        return total

    @property
    def last_activity(self) -> Optional[datetime]:
        if not self.sessions:
            return None
        last = self.sessions[-1]
        return last.end if last.end else last.begin

    @property
    def last_activity_type(self) -> Optional[str]:
        if not self.sessions:
            return None

        return "pause" if self.sessions[-1].end else ("resume" if len(self.sessions) > 1 else "started")

    @property
    def last_activity_display(self) -> str:
        if self.last_activity and self.last_activity_type:
            return f"{self.last_activity.strftime('%H:%M')} ({self.last_activity_type})"
        return ""
