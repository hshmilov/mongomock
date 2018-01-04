from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler


class LoggedBackgroundScheduler(BackgroundScheduler):
    def __init__(self, logger, *vargs, **kwargs):
        super().__init__(*vargs, **kwargs)
        self._user_logger = logger
        self.add_listener(self._logger_listener, EVENT_JOB_ERROR)

    def _logger_listener(self, event):
        if event.exception:
            self._user_logger.exception('Async job error', exc_info=event.exception)
