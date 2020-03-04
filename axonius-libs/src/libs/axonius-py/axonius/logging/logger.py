import multiprocessing
import os
import logging
import logging.handlers

from axonius.logging.customised_json_formatter import CustomisedJSONFormatter

BYTES_LIMIT = 5 * 1024 * 1024  # 5MB
VERBOSE_BYTES_LIMIT = 15 * 1024 * 1024  # 15MB


class AxoniusQueueHandler(logging.handlers.QueueHandler):
    def prepare(self, record: logging.LogRecord):
        # QueueHandler assumes self.format will change record, but instead it is just returning the json,
        # thus we need to make this change here
        record.msg = self.format(record)
        # Look at the inheritor to understand the logic - these are not pickelable
        record.args = None
        record.exc_info = None
        return record


def logger_listener(plugin_unique_name, log_level, log_directory, queue):
    # 1. Create a regular logged
    regular_log_path = os.path.join(log_directory, f'{plugin_unique_name}.axonius.log')
    verbose_regular_log_path = os.path.join(log_directory, f'{plugin_unique_name}.verbose.axonius.debug')

    # Creating a rotating file log handler
    file_handler = logging.handlers.RotatingFileHandler(regular_log_path,
                                                        maxBytes=BYTES_LIMIT,
                                                        backupCount=3)
    file_handler.setLevel(log_level)

    verbose_file_handler = logging.handlers.RotatingFileHandler(verbose_regular_log_path,
                                                                maxBytes=VERBOSE_BYTES_LIMIT,
                                                                backupCount=3)
    verbose_file_handler.setLevel(logging.DEBUG)

    # Building the logger object
    logger = logging.getLogger('axonius')
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

    logger.addHandler(verbose_file_handler)

    # 2. Run an infinite loop that gets messages
    while True:
        try:
            record = queue.get()
            logger = logging.getLogger(record.name)
            logger.handle(record)  # No level or filter logic applied - just do it!
        except Exception:
            import sys
            import traceback
            print('Logger error!', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


def create_logger(plugin_unique_name, log_level, log_directory):
    """ Creating Json logger.

    Create a thread-safe, process-safe logger.
    :param str log_level: the log_level of the log.
    :param str plugin_unique_name: The unique name of the plugin.
    :param str log_directory: The path for the log file.
    """
    queue = multiprocessing.Queue(-1)
    listener = multiprocessing.Process(
        target=logger_listener, args=(plugin_unique_name, log_level, log_directory, queue), daemon=True
    )
    listener.start()

    # Configure this current process listener
    h = AxoniusQueueHandler(queue)  # Just the one handler needed
    h.setFormatter(CustomisedJSONFormatter(plugin_unique_name))

    logger = logging.getLogger('axonius')
    logger.addHandler(h)
    logger.setLevel(logging.DEBUG)
