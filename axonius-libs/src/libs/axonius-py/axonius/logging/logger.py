import os
import logging
import logging.handlers

from axonius.logging.customised_json_formatter import CustomisedJSONFormatter

BYTES_LIMIT = 5 * 1024 * 1024  # 5MB
VERBOSE_BYTES_LIMIT = 15 * 1024 * 1024  # 15MB

LOGGER = None


def _create_logger(plugin_unique_name, log_level, logstash_host, log_directory):
    """ Creating Json logger.

    Creating a logging object to be used by the plugin. This object is the pythonic logger object
    And can be used the same. The output file of the logs will be in a JSON format and will be entered to
    An ELK stack.
    :param str log_level: the log_level of the log.
    :param str plugin_unique_name: The unique name of the plugin.
    :param str logstash_host: The address of logstash HTTP interface.
    :param str log_directory: The path for the log file.
    """
    regular_log_path = os.path.join(log_directory, f'{plugin_unique_name}.axonius.log')
    verbose_regular_log_path = os.path.join(log_directory, f'{plugin_unique_name}.verbose.axonius.debug')

    # Creating the logger using our customized logger formatter
    formatter = CustomisedJSONFormatter(plugin_unique_name)
    # Creating a rotating file log handler
    file_handler = logging.handlers.RotatingFileHandler(regular_log_path,
                                                        maxBytes=BYTES_LIMIT,
                                                        backupCount=3)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    verbose_file_handler = logging.handlers.RotatingFileHandler(verbose_regular_log_path,
                                                                maxBytes=VERBOSE_BYTES_LIMIT,
                                                                backupCount=3)
    verbose_file_handler.setFormatter(formatter)
    verbose_file_handler.setLevel(logging.DEBUG)

    # Building the logger object
    logger = logging.getLogger('axonius')
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

    logger.addHandler(verbose_file_handler)
    return logger


def create_logger(*args, **kwargs):
    # pylint: disable=W0603
    global LOGGER
    if not LOGGER:
        LOGGER = _create_logger(*args, **kwargs)
    return LOGGER


def clean_locks_from_logger():
    # pylint: disable=W0212
    # cleaning logger locks we might still be holding
    if not LOGGER:
        return
    LOGGER.info(f'Clearing locks from {LOGGER.handlers}')
    for handler in LOGGER.handlers:
        try:
            lock = handler.lock
            lock._release_save()
        except Exception:
            LOGGER.exception(f'Exception while restoring locks - {handler} - {lock}')
