import logging
import logging.handlers

from axonius.logging.customised_json_formatter import CustomisedJSONFormatter
from axonius.logging.logstash_http_log_handler import LogstashHttpServer


def create_logger(plugin_unique_name, log_level, logstash_host, log_path):
    """ Creating Json logger.

    Creating a logging object to be used by the plugin. This object is the pythonic logger object
    And can be used the same. The output file of the logs will be in a JSON format and will be entered to
    An ELK stack.
    :param str log_level: the log_level of the log.
    :param str plugin_unique_name: The unique name of the plugin.
    :param str logstash_host: The address of logstash HTTP interface.
    :param str log_path: The path for the log file.
    """
    plugin_unique_name = plugin_unique_name

    fatal_log_path = log_path.split('.log')[0] + '_FATAL.log'
    file_handler_fatal = logging.handlers.RotatingFileHandler(fatal_log_path,
                                                              maxBytes=50 * 1024 * 1024,  # 150Mb Max
                                                              backupCount=3)
    formatter = CustomisedJSONFormatter(plugin_unique_name)
    file_handler_fatal.setFormatter(formatter)
    fatal_logger = logging.getLogger('axonius_plugin_fatal_log')
    fatal_logger.addHandler(file_handler_fatal)
    fatal_logger.setLevel(log_level)

    # Creating the logger using our custumized logger fomatter
    formatter = CustomisedJSONFormatter(plugin_unique_name)
    # Creating a rotating file log handler
    file_handler = logging.handlers.RotatingFileHandler(log_path,
                                                        maxBytes=50 * 1024 * 1024,  # 150Mb Max
                                                        backupCount=3)
    file_handler.setFormatter(formatter)

    # Creating logstash file handler (implemeted above)
    logstash_handler = LogstashHttpServer(logstash_host, fatal_logger)
    logstash_handler.setFormatter(formatter)

    # Building the logger object
    logger = logging.getLogger('axonius_plugin_log')
    logger.addHandler(file_handler)
    logger.addHandler(logstash_handler)
    logger.setLevel(log_level)

    return logger
