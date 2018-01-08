# Customized logger handler in order to send logs to logstash using http
import logging
import time

import requests


class LogstashHttpServer(logging.Handler):
    def __init__(self, logstash_host, fatal_logger, **kwargs):
        """
            Logging handler for connecting logstash through http.
        """
        self.bulk_size = 100  # lines
        self.max_time = 30  # Secs
        self.error_cooldown = 120  # Secs
        self.max_logs = 100000  # lines
        self.warning_before_cooldown = 3
        self.currentLogs = []
        self.last_sent = time.time()
        self.last_error_time = 0
        self.logstash_host = logstash_host
        self.fatal_logger = fatal_logger
        super().__init__()

    def emit(self, record):
        """ The callback that is called in each log message.

        This function will actually send the log to logstash. I order to be more efficient, log messages are
        Not sent directly but instead this function saves a bulk of log messages and then send them together.
        This will avoid the TCP/SSL connection overhead.
        Since we cant send a bulk of messages in one http request (Logstash do not support this) we will create
        One TCP session (with keep alive) and post messages one by one.
        """
        try:
            log_entry = self.format(record)
            current_time = time.time()

            # Checking if we can append the new log entry
            if len(self.currentLogs) < self.max_logs:
                self.currentLogs.append(log_entry)

            # Checking if we need to dump logs to the server
            if ((len(self.currentLogs) > self.bulk_size or
                 current_time - self.last_sent > self.max_time) and
                    current_time - self.last_error_time > self.max_time):
                self.last_sent = current_time
                with requests.Session() as s:  # Sending all logs on one session
                    new_list = []
                    # The warning count will count how much time we couldnt save a log due to an error.
                    # In case of too much errors (defined by 'warning_before_cooldown') we will enter
                    # some cooldown period (defined by 'error_cooldown')
                    warning_count = 0
                    for log_line in self.currentLogs:
                        try:
                            if warning_count > self.warning_before_cooldown:
                                # Something bad with the connection, not trying to send anymore. Just append
                                # All the messages that we couldnt send
                                new_list.append(log_line)
                            else:
                                s.post(self.logstash_host,
                                       data=log_line, timeout=2)

                        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout,
                                requests.exceptions.InvalidSchema):
                            # We should add this log line again to the list because the problem
                            # Is in the connection and not in the log
                            new_list.append(log_line)
                            warning_count = warning_count + 1
                        except Exception as e:
                            exception_log = "Error while sending log. *Log is lost*. Error details: " \
                                            "type={0}, message={1}".format(type(e).__name__, str(e))
                            print("[fatal error]: %s" %
                                  (exception_log,))
                            self.fatal_logger.exception(exception_log)
                            warning_count = warning_count + 1
                            continue
                            # In any other cases, we should just try the other log lines
                            # (This line will not be sent anymore)
                    if warning_count != 0:
                        warning_message = "connection error occured {0} times while sending log." \
                            .format(warning_count)
                        print("[fatal error]: %s." %
                              (warning_message,))
                        self.fatal_logger.warning(warning_message)
                        if warning_count > self.warning_before_cooldown:
                            self.last_error_time = time.time()
                    self.currentLogs = new_list
                return ''
        except Exception as e:  # We must catch every exception from the logger
            # Nothing we can do here
            exception_message = "Error on logger Error details: type={0}, message={0}".format(type(e).__name__,
                                                                                              str(e))
            print("[fatal error]: %s" % (exception_message,))
            self.fatal_logger.exception(exception_message)
            return 'Bad'
