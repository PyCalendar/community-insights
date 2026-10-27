def set_time_zone(client, name: str) -> None:
    """What django-tz-detect stores when the browser tells its time zone."""
    session = client.session
    session["detected_tz"] = name
    session.save()
