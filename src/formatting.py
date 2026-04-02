def format_minutes(minutes):
    h, m = divmod(minutes, 60)
    if h:
        return f"{h}h {m:02d}m" if m else f"{h}h"
    return f"{m}m"
