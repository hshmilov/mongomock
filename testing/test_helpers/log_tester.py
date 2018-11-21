import re
import json


class LogTester:
    def __init__(self, filepath):
        self.filepath = filepath

    def is_pattern_in_log(self, pattern, lines_lookback=0):
        """
        :param pattern: pattern to search for in log (passed to re.search)
        :param lines_lookback: num of last lines to search for the pattern. 0 for whole file
        :return: True iff pattern was found in any of the lines
        """
        with open(self.filepath) as f:
            data = f.readlines()
            recent = data[-min(lines_lookback, len(data)):]
            return any(re.search(pattern, line) is not None for line in recent)

    def is_str_in_log(self, str_in_log, lines_lookback=0):
        """
        This is just a nicer version of is_pattern_in_log that doesn't require escaping special characters.
        """
        with open(self.filepath) as f:
            data = f.readlines()
            recent = data[-min(lines_lookback, len(data)):]
            return any(str_in_log in x for x in recent)

    def is_metric_in_log(self, metric_name, value, lines_lookback=0):
        """
        Check is a certain metric is present in log
        :param metric_name: Value of metric_name field
        :param value: str pattern for regex value, or exact numeric value otherwise
        :param lines_lookback: number of lines to go back in log
        :return: True iff the metric was present in the log
        """
        with open(self.filepath) as f:
            data = f.readlines()
            recent = data[-min(lines_lookback, len(data)):]
            for line in recent:
                as_dict = json.loads(line)

                def is_value_match(actual, expected):
                    if isinstance(expected, str):
                        return re.search(expected, str(actual)) is not None
                    return actual == expected

                if as_dict['message'] == 'METRIC':
                    if as_dict['metric_name'] == metric_name and is_value_match(as_dict['value'], value):
                        return True
        return False
