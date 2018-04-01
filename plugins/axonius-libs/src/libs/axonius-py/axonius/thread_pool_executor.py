from concurrent.futures import ThreadPoolExecutor
import logging
logger = logging.getLogger(f"axonius.{__name__}")


class LoggedThreadPoolExecutor(ThreadPoolExecutor):
    def __init__(self, *vargs, **kwargs):
        super().__init__(*vargs, **kwargs)

    def submit(self, *vargs, **kwargs):
        f = super().submit(*vargs, **kwargs)
        f.add_done_callback(self._logger_listener)
        return f

    def _logger_listener(self, future):
        if future.exception():
            logger.exception('Async job error', exc_info=future.exception())
