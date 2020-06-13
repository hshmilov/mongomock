"""
Multiprocess utils
"""
import concurrent.futures
import logging
import multiprocessing
import queue
import sys
import threading

from typing import List, Callable, Tuple, Dict

logger = logging.getLogger(f'axonius.{__name__}')
CHECK_QUEUE_INTERVAL = 60   # every minute


class EnhancedGenerator:
    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        self.value = yield from self.gen


def multiprocess_yield_wrapper(func: Tuple[Callable, Tuple, Dict], m_queue: multiprocessing.Queue):
    try:
        generator = EnhancedGenerator(func[0](*func[1], **func[2]))
        for yield_result in generator:
            m_queue.put(yield_result)

        # at last, return the value of the function. this is enhanced generators - read this:
        # https://stackoverflow.com/questions/34073370/best-way-to-receive-the-return-value-from-a-python-generator
        return generator.value
    except Exception:
        logger.exception(f'Multiprocess_yield_wrapper exception while calling {str(func[0])}')
    finally:
        m_queue.put(None)


def concurrent_multiprocess_yield(to_execute: List[Tuple[Callable, Tuple, Dict]], parallel_count):
    """
    Gets a list of functions to execute. Assumes each function returns a generator.
    Executes each one of those functions in its own process, and yields the result in the calling process.
    :param to_execute: a list of tuples, each tuple is a tuple of (function, args_tuple, kwargs_dict)
    :param parallel_count: How much to execute in parallel.
    :return:
    """
    logger.info(f'Found {len(to_execute)} functions to execute, with {parallel_count} processes')
    manager = multiprocessing.Manager()
    queue_instance = manager.Queue()

    results = []

    with concurrent.futures.ProcessPoolExecutor(parallel_count) as pool:
        try:
            futures = [pool.submit(multiprocess_yield_wrapper, func_tuple, queue_instance) for func_tuple in to_execute]

            def notify_as_completed():
                try:
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        logger.info(f'ProcessPoolExecutor - Finished {i} out of {len(to_execute)}.')
                        results.append(future.result())
                except Exception:
                    logger.exception(
                        f'Error while notifying as_completed for concurrent_multiprocess_yield'
                    )

            thread = threading.Thread(target=notify_as_completed)
            thread.start()

            none_recieved = 0
            try:
                while none_recieved != len(to_execute):
                    try:
                        res = queue_instance.get(True, CHECK_QUEUE_INTERVAL)
                    except queue.Empty:
                        if thread.is_alive():
                            continue
                        else:
                            logger.error(f'Receiving thead is no longer alive.')
                            break
                    if res is None:
                        none_recieved += 1
                    else:
                        yield res
            except Exception:
                logger.critical(f'Error while yielding results from concurrent_multiprocess_yield', exc_info=True)
        except Exception:
            logger.critical(f'General exception in processpoolexecutor', exc_info=True)

    return results


def test_number_yielder(x, y):
    for i in range(x, y):
        yield i

    return f'done with {x}, {y}'


def test():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    result = EnhancedGenerator(
        concurrent_multiprocess_yield([(test_number_yielder, (i, i + 10), {}) for i in range(10)], 1)
    )
    for i in result:
        print(f'Got {i}')

    print(f'All results: {result.value}')


if __name__ == '__main__':
    sys.exit(test())
