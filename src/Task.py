
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import datetime, timedelta

@dataclass
class Task:
    name: str  # Full normalized task string, includes @category and #project if present
    sessions: List[Tuple[datetime, Optional[datetime]]] = field(default_factory=list)  # List of (start, stop) tuples; stop may be None if active
    is_active: bool = False
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    category: Optional[str] = None  # Extracted from @category
    project: Optional[str] = None   # Extracted from #project

    def start_session(self, start: Optional[datetime] = None):
        if start is None:
            start = datetime.now()
        self.sessions.append((start, None))
        self.is_active = True

    def stop_session(self, stop: Optional[datetime] = None):
        if stop is None:
            stop = datetime.now()
        if self.sessions and self.sessions[-1][1] is None:
            self.sessions[-1] = (self.sessions[-1][0], stop)
        self.is_active = False

    @property
    def total_time(self) -> int:
        """Total time in minutes across all sessions, rounded up."""
        import math
        total = 0
        for start, stop in self.sessions:
            if stop is None:
                stop = datetime.now()
            seconds = (stop - start).total_seconds()
            total += math.ceil(seconds / 60)
        return total

    @property
    def last_activity(self) -> Optional[datetime]:
        if not self.sessions:
            return None
        last = self.sessions[-1]
        return last[1] if last[1] else last[0]

    @property
    def last_activity_type(self) -> Optional[str]:
        if not self.sessions:
            return None
        
        return "pause" if self.sessions[-1][1] else ( "resume" if len( self.sessions ) > 1 else "started" )

    @property
    def last_activity_display(self) -> str:
        if self.last_activity and self.last_activity_type:
            return f"{self.last_activity.strftime('%H:%M')} ({self.last_activity_type})"
        return ""
