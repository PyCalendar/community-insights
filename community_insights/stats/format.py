"""Times as people read them."""


def format_duration(seconds: float) -> str:
    """Seconds in two units at most: 45min, 3h 12min, 2d 4h."""
    minutes = round(seconds / 60)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {minutes}min" if minutes else f"{hours}h"
    return f"{minutes}min"
