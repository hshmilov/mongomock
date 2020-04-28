import logging
import multiprocessing
import os
import signal

from typing import Tuple, Callable, Dict

logger = logging.getLogger(f'axonius.{__name__}')


def test_func(func: Tuple[Callable, Tuple, Dict]):
    try:
        func[0](*func[1], **func[2])
    except Exception:
        pass

    return 0


def get_function_rv_safe(function_target, *args, **kwargs):
    proc = multiprocessing.Process(target=function_target, args=args, kwargs=kwargs)
    proc.start()
    proc.join(30)
    if proc.is_alive():
        logger.info(f'function {function_target.__name__} timed out.')
        os.kill(proc.pid, signal.SIGKILL)
        raise ValueError(f'timed out')

    if proc.exitcode != 0:
        logger.info(f'function {function_target.__name__} returned unexpected error: {proc.exitcode}')
        raise ValueError(f'Please check the settings')

    return function_target(*args, **kwargs)
