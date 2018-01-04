from concurrent.futures import ThreadPoolExecutor


class LoggedThreadPoolExecutor(ThreadPoolExecutor):
    def __init__(self, logger, *vargs, **kwargs):
        super().__init__(*vargs, **kwargs)
        self._user_logger = logger

    def submit(self, *vargs, **kwargs):
        f = super().submit(*vargs, **kwargs)
        f.add_done_callback(self._logger_listener)
        return f

    def _logger_listener(self, future):
        if future.exception():
            self._user_logger.exception('Async job error', exc_info=future.exception())
