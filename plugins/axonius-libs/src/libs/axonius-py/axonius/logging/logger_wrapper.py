"""
Just calls the regular logger but adds a prefix before.
"""
from axonius.parsing_utils import get_exception_string
from datetime import datetime


class LoggerWrapper(object):
    def __init__(self, original_logger, prefix):
        self.logger = original_logger
        self.prefix = prefix
        self.error_messages = []

    def format_msg(self, msg):
        return f"[{self.prefix}] {msg}"

    def info(self, msg, *args, **kwargs):
        self.logger.info(self.format_msg(msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(self.format_msg(msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.error_messages.append("[{0}] {1}".format(datetime.now(), self.format_msg(msg)))
        self.logger.error(self.format_msg(msg), *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(self.format_msg(msg), *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.error_messages.append("[{0}] {1}:\n{2}".format(
            datetime.now(), self.format_msg(msg), get_exception_string()))
        self.logger.exception(self.format_msg(msg), *args, **kwargs)
