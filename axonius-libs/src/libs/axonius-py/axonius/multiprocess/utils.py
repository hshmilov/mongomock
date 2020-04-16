import logging

from multiprocessing import Pool
from typing import Tuple, Callable, Dict

logger = logging.getLogger(f'axonius.{__name__}')


def test_func(func: Tuple[Callable, Tuple, Dict]):
    try:
        func[0](*func[1], **func[2])
    except Exception:
        pass

    return 0


# https://www.cs.ubc.ca/~gberseth/blog/handling-segfaults-in-python-that-occur-in-custom-c-libraries.html
def get_function_rv_safe(function_target, *args, **kwargs):
    pool = Pool(1)

    try:
        result = pool.apply_async(test_func, args=((function_target, args, kwargs), ))
        result.get(timeout=30)
    except Exception as e:
        logger.info(f'function {function_target.__name__} returned unexpected error: {str(e)}')
        raise ValueError(f'Please check the settings')

    return function_target(*args, **kwargs)
