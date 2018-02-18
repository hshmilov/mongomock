# A help class for dealing with CIMTYPE_DateTime (returning from wmi...)
import re
from datetime import tzinfo, datetime, timedelta


class MinutesFromUTC(tzinfo):
    """Fixed offset in minutes from UTC."""

    def __init__(self, offset):
        self.__offset = timedelta(minutes=offset)

    def utcoffset(self, dt):
        return self.__offset

    def dst(self, dt):
        return timedelta(0)


def wmi_date_to_datetime(s):
    # Parse the date. this is how the str format defined here:
    # https://msdn.microsoft.com/en-us/library/system.management.cimtype(v=vs.110).aspx
    date_pattern = re.compile(r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.(\d{6})([+|-])(\d{3})')
    s = date_pattern.search(s)
    if s is not None:
        g = s.groups()
        offset = int(g[8])
        if g[7] == '-':
            offset = -offset
        dt = datetime(int(g[0]), int(g[1]),
                      int(g[2]), int(g[3]),
                      int(g[4]), int(g[5]),
                      int(g[6]), MinutesFromUTC(offset))

        return dt
