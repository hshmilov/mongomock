
# A help class for dealing with CIMTYPE_DateTime (returning from wmi...)
import logging
logger = logging.getLogger(f'axonius.{__name__}')
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
    try:
        s = date_pattern.search(s)
    except Exception:
        logger.error(f"Error parsing wmi date: {s}")
        raise ValueError(f"Error parsing wmi date: {s}")
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


def wmi_query_namespace_commands(list_of_queries):
    """
    Get wmi queries plus name spaces and returns the format needed for execution commans.
    :param list_of_queries: a list of wmi queries plus namespaces
    :return:
    """
    return [{"type": "query", "args": [q, ns]} for (q, ns) in list_of_queries]


def smb_shell_commands(list_of_shell_commands):
    """
    Gets shell commands and returns the format needed for execution commands.
    :param list_of_shell_commands: a list of wmi queries
    :type list_of_shell_commands: list of str
    :return:
    """

    return [{"type": "shell", "args": [q]} for q in list_of_shell_commands]


def smb_getfile_commands(list_of_getfile_commands):
    """
    Gets getfile commands and returns the format needed for execution commands.
    :param list_of_getfile_commands: a list of paths of files to get
    :type list_of_getfile_commands: list of str
    :return:
    """

    return [{"type": "getfile", "args": [p]} for p in list_of_getfile_commands]


def is_wmi_answer_ok(answer):
    """
    Checks if a specific wmi query was successfully run.
    :param answer: The answer list.
    :return: True if true, else False
    """

    return answer["status"] == "ok"


def is_wmi_answer_invalid_query(answer):
    """
    Not all wmi answers are supported. When they are not supported, we get "WBEM_E_INVALID_QUERY". This function checks
    if the asnwer we got is of this type. However, when we make an error in a wmi answer that's also the answer.
    So we must be careful with that function - and have a logic that understands if the query indicates a problem or
    not.
    :param answer: the wmi answer
    :return: True if the query is invalid, false otherwise
    """

    return answer["status"] == "exception" and "WBEM_E_INVALID_QUERY" in answer["data"]


def check_wmi_answers_integrity(wmi_requests, wmi_answers):
    """
    Gets answers and checks for integrity.
    :param wmi_requests: the wmi requests list
    :param wmi_answers: list of answers from wmi execution.
    :param logger: optional logger.
    :param prefix: optional logger prefix.
    :return:
    """

    ok = True

    for i, a in enumerate(wmi_answers):
        if is_wmi_answer_ok(a) is False:
            ok = False
            if logger is not None:
                # It has to be but i still check it
                try:
                    req = wmi_requests[i]
                except Exception:
                    req = ""
                logger.error(f"Query {i} ({req}) exception: {a['data']}")

    return ok


def reg_view_output_to_dict(output):
    kv = {}
    for line in output[1:].split("\n"):
        # Notice that the first line doesn't matter since we cut it
        # when we split(r"HKEY_LOCAL_MACHINE\Software")
        try:
            line_name, line_type, line_value = line.strip().split("    ")
            line_name = line_name.lower()
            kv[line_name] = line_value.strip()

            if line_type.upper() == "REG_MULTI_SZ":
                kv[line_name] = kv[line_name].split("\x00")
        except Exception:
            pass

    return kv


def reg_view_parse_int(st):
    try:
        return int(st)
    except Exception:
        try:
            return int(st, 16)
        except Exception:
            return None
