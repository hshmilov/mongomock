import sys
import daemonocle
import logging
import json_log_formatter

from axonius.consts.system_consts import LOGS_PATH_HOST
from axonius.logging.metric_helper import log_metric

WATCHDOG_LOGS_DIR = LOGS_PATH_HOST / 'watchdogs'


class WatchdogTask:

    def __init__(self):
        self.name = self.__class__.__name__.lower()
        WATCHDOG_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.logfile = WATCHDOG_LOGS_DIR / f'{self.name}.watchdog.log'
        self.pidfile = WATCHDOG_LOGS_DIR / f'{self.name}.pid'

        formatter = json_log_formatter.JSONFormatter()
        json_handler = logging.FileHandler(filename=self.logfile)
        json_handler.setFormatter(formatter)

        self.logger = logging.getLogger(self.name)
        self.logger.addHandler(json_handler)
        self.logger.setLevel(logging.INFO)
        self.logger.info(f'starting run of {self.name}')

    def run(self):
        pass

    def report_info(self, msg):
        self.logger.info(msg)

    def report_error(self, msg):
        self.logger.error(msg)

    def report_metric(self, metric_name, metric_value, **kwargs):
        log_metric(self.logger, metric_name=metric_name, metric_value=metric_value, **kwargs)

    def start(self):
        daemon = daemonocle.Daemon(worker=self.run, pidfile=self.pidfile)
        daemon.do_action(sys.argv[1])
