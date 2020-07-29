import logging

from datetime import timedelta, datetime, timezone

import dateutil

logger = logging.getLogger(f'axonius.{__name__}')


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


def time_from_now(duration_in_hours):
    return datetime.now() + timedelta(hours=duration_in_hours)


def is_date_real(datetime_to_parse):
    """
    Often we might encounter a situation where a datetime is valid, but actually represents
    an empty value. for that case we have this function.
    :param datetime_to_parse:
    :return: True if real, False otherwise.
    """

    # 1/1/1970 - Unix epoch
    # 1/1/1601 - Windows NT epoch(The FILETIME structure records time in the form
    #            of 100-nanosecond intervals since January 1, 1601.)

    return isinstance(datetime_to_parse, datetime) and \
        datetime_to_parse.replace(tzinfo=None) != datetime(1601, 1, 1) and \
        datetime_to_parse.replace(tzinfo=None) != datetime(1970, 1, 1)


def _parse_unix_timestamp(unix_timestamp):
    if unix_timestamp == -1:
        return None
    try:
        return datetime.utcfromtimestamp(unix_timestamp)
    except Exception:
        # This must be unix timestamp with milliseconds, we continue to the next line.
        pass
    try:
        return datetime.utcfromtimestamp(unix_timestamp / 1000)
    except Exception:
        logger.exception(f'problem parsing unix timestamp {unix_timestamp}')
        return None


def parse_date(datetime_to_parse, dayfirst=False):
    """
    Parses date and returns it as UTC
    """
    try:
        if datetime_to_parse is None:
            # Optimizations
            return None
        if isinstance(datetime_to_parse, int):
            datetime_from_int = _parse_unix_timestamp(datetime_to_parse)
            if datetime_from_int:
                return datetime_from_int
        if isinstance(datetime_to_parse, datetime):
            # sometimes that happens too
            return datetime_to_parse.astimezone(timezone.utc)
        if isinstance(datetime_to_parse, str) and datetime_to_parse.isnumeric():
            int_datetime = int(datetime_to_parse)
            datetime_from_str = _parse_unix_timestamp(int_datetime)
            if datetime_from_str and is_date_real(datetime_from_str):
                return datetime_from_str
        datetime_to_parse = str(datetime_to_parse)
        d = dateutil.parser.parse(datetime_to_parse, dayfirst=dayfirst).astimezone(timezone.utc)

        # Sometimes, this would be a fake date (see is_date_real). in this case return None
        return d if is_date_real(d) else None
    except Exception:
        return None


def time_diff(time1: datetime.time, time2: datetime.time) -> timedelta:
    """
    Return time diff between two datetime.time objects
    :param time1: first time object
    :param time2: second time object
    :return:
    """
    now = datetime.now()
    datetime1 = datetime.combine(now, time1)
    datetime2 = datetime.combine(now, time2)
    return datetime1 - datetime2


def days_diff(datetime1: datetime, datetime2: datetime) -> int:
    """
    Calculate difference of days between given dates
    :param datetime1: first date object
    :param datetime2: second date object
    :return: amount of days
    """
    return (datetime1 - datetime2).days
