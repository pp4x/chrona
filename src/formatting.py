def format_minutes(minutes):
    h, m = divmod(minutes, 60)
    if h:
        return f"{h}h {m:02d}m" if m else f"{h}h"
    return f"{m}m"


def format_seconds_as_minutes(total_seconds):
    return format_minutes(int(total_seconds // 60))
