"""
All sorts of retry generic functions.
"""
import time
import logging

from collections import Callable

logger = logging.getLogger(f'axonius.{__name__}')

DEFAULT_MAX_TRIES = 3


class RetryMaxTriesReached(Exception):
    pass


def retry_generator(wait_fixed=None, stop_max_attempt_number=DEFAULT_MAX_TRIES):
    def real_decorator(function_generator: Callable):
        def wrapper(*args, **kwargs):
            for i in range(stop_max_attempt_number):
                try:
                    yield from function_generator(*args, **kwargs)
                    return
                except Exception:
                    logger.exception(f'Failure on {function_generator.__name__} ({i+1}/{stop_max_attempt_number})')
                    if wait_fixed:
                        time.sleep(wait_fixed / 1000)

            raise RetryMaxTriesReached(f'Max retries reached for function {function_generator.__name__}')
        return wrapper
    return real_decorator
