from datetime import timedelta


def next_weekday(current_day, weekday):
    """
    Returns the next occurrence of weekday (day of work week).
    :param current_day: Current datetime
    :param weekday: The day in the work week to return (0 is the beginning of the work week).
    :return: The closest next occurrence of weekday.
    """
    days_ahead = weekday - current_day.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return current_day + timedelta(days_ahead)
