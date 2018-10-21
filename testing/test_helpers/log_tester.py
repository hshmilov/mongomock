import re


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
