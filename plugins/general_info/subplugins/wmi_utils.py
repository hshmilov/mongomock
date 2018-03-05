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


def wmi_query_commands(list_of_queries):
    """
    Gets wmi queries and returns the format needed for execution commands.
    :param list_of_queries: a list of wmi queries
    :type list_of_queries: list of str
    :return:
    """

    return [{"type": "query", "args": [q]} for q in list_of_queries]


def smb_shell_commands(list_of_shell_commands):
    """
    Gets shell commands and returns the format needed for execution commands.
    :param list_of_shell_commands: a list of wmi queries
    :type list_of_shell_commands: list of str
    :return:
    """

    return [{"type": "shell", "args": [q]} for q in list_of_shell_commands]


def is_wmi_answer_ok(answer):
    """
    Checks if a specific wmi query was successfully run.
    :param answer: The answer list.
    :return: True if true, else False
    """

    return answer["status"] == "ok"


def check_wmi_answers_integrity(answers, logger=None):
    """
    Gets answers and checks for integrity.
    :param answers: list of answers from wmi execution.
    :param logger: optional logger.
    :param prefix: optional logger prefix.
    :return:
    """

    ok = True

    for i, a in enumerate(answers):
        if is_wmi_answer_ok(a) is False:
            ok = False
            if logger is not None:
                logger.error(f"Query {i} exception: {a['data']}")

    return ok
