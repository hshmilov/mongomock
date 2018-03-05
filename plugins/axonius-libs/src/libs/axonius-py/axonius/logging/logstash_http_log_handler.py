# Customized logger handler in order to send logs to logstash using http
import logging
import time
from datetime import datetime

import requests
from threading import Lock
from apscheduler.executors.pool import ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


class LogstashHttpServer(logging.Handler):
    def __init__(self, logstash_host, fatal_logger, **kwargs):
        """
            Logging handler for connecting logstash through http.
        """
        self.max_logs = 100000  # lines
        self.current_logs = []
        self.logstash_host = logstash_host
        self.fatal_logger = fatal_logger
        self.logs_array_lock = Lock()

        # Creating thread for sending logs to logstash
        executors = {'default': ThreadPoolExecutorApscheduler(1)}
        self._log_sender_scheduler = BackgroundScheduler(executors=executors)
        self._log_sender_scheduler.add_job(func=self.log_sender_thread,
                                           trigger=IntervalTrigger(seconds=3),  # 3 Seconds between each log sending
                                           next_run_time=datetime.now(),
                                           name="logstash_sender_thread",
                                           id="logstash_sender_thread",
                                           max_instances=1)
        self._log_sender_scheduler.start()

        super().__init__()

    def log_sender_thread(self):
        try:
            # Checking if we even have logs to send
            if len(self.current_logs) == 0:
                return

            # Copying all current logs to send and clearing log queue:
            with self.logs_array_lock:
                logs_to_send = list(self.current_logs)  # Hard copy
                self.current_logs = []

            with requests.Session() as s:  # Sending all logs on one session
                unsent_logs = []
                # The warning count will count how much time we couldn't save a log due to an error.
                warning_count = 0
                for log_line in logs_to_send:
                    try:
                        s.post(self.logstash_host,
                               data=log_line, timeout=2)

                    except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout,
                            requests.exceptions.InvalidSchema):
                        # We should add this log line again to the list because the problem
                        # Is in the connection and not in the log
                        unsent_logs.append(log_line)
                        warning_count = warning_count + 1
                    except Exception as e:
                        exception_log = f"Error while sending log. *Log is lost*. Error details: " \
                                        "type={type(e).__name__}, message={str(e)}"
                        print("[fatal error]: %s" %
                              (exception_log,))
                        self.fatal_logger.exception(exception_log)
                        warning_count = warning_count + 1
                        continue
                        # In any other cases, we should just ignore the current log line
                        # (This line will not be sent anymore)
                if warning_count != 0:
                    print("[fatal error]: %s." %
                          (f"connection error occured {warning_count} times while sending log.",))
                    self.fatal_logger.warning(f"connection error occured {warning_count} times while sending log.")
                    # Adding logs that we couldn't send to the next cycle
                    if len(unsent_logs) > 0:
                        # That means we have logs we need to retry sending them. In order to do so we are
                        # just adding them to the logs queue.
                        with self.logs_array_lock:
                            if len(self.current_logs) < self.max_logs:
                                self.current_logs.extend(unsent_logs)
                            else:
                                error_msg = "Logs queue is to big, probably logstash is down"
                                print(error_msg)
                                self.fatal_logger.error(error_msg)

        except Exception as e:  # We must catch every exception from the logger
            # Nothing we can do here
            exception_message = "Error on logger Error details: type={0}, message={0}".format(type(e).__name__,
                                                                                              str(e))
            print("[fatal error]: %s" % (exception_message,))
            self.fatal_logger.exception(exception_message)

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

            # Checking if we can append the new log entry
            if len(self.current_logs) < self.max_logs:
                with self.logs_array_lock:
                    self.current_logs.append(log_entry)
            else:
                raise RuntimeError("Maximum log cache reached, probably a problem with logstash connection")

            return ''

        except Exception as e:  # We must catch every exception from the logger
            # Nothing we can do here
            exception_message = "Error on logger Error details: type={0}, message={0}".format(type(e).__name__,
                                                                                              str(e))
            print("[fatal error]: %s" % (exception_message,))
            self.fatal_logger.exception(exception_message)
            return ''
