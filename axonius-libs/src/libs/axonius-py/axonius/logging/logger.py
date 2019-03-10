import os
import logging
import logging.handlers

from axonius.logging.customised_json_formatter import CustomisedJSONFormatter

BYTES_LIMIT = 5 * 1024 * 1024  # 5MB
VERBOSE_BYTES_LIMIT = 15 * 1024 * 1024  # 15MB


def create_logger(plugin_unique_name, log_level, log_directory):
    """ Creating Json logger.

    Creating a logging object to be used by the plugin. This object is the pythonic logger object
    And can be used the same. The output file of the logs will be in a JSON format and will be entered to
    An ELK stack.
    :param str log_level: the log_level of the log.
    :param str plugin_unique_name: The unique name of the plugin.
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
