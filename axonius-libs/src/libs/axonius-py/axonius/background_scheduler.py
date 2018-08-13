import logging
logger = logging.getLogger(f'axonius.{__name__}')
from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler


class LoggedBackgroundScheduler(BackgroundScheduler):
    def __init__(self, *vargs, **kwargs):
        super().__init__(*vargs, **kwargs)
        self.add_listener(self._logger_listener, EVENT_JOB_ERROR)

    def _logger_listener(self, event):
        if event.exception:
            logger.exception('Async job error', exc_info=event.exception)
