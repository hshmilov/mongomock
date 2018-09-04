import concurrent.futures
import multiprocessing
import queue
import threading
from datetime import datetime
from threading import RLock
import logging

import func_timeout


logger = logging.getLogger(f'axonius.{__name__}')
from axonius.thread_stopper import StopThreadException, ThreadStopper, stoppable


def run_in_executor_helper(executor, method_to_call, resolve, reject, *_, args=[], kwargs={}, **__):
    """
    Helps with running Promises in an executor
    :param executor: executor to run on
    :param method_to_call: method to run
    :param resolve: will be called if method returns
    :param reject: will be called with exception from method
    :param args: args to method_to_call
    :param kwargs: kwargs to method_to_call
    :return:
    """

    def resolver():
        try:
            resolve(method_to_call(*args, **kwargs))
        except Exception as e:
            reject(e)
        except (StopThreadException, func_timeout.exceptions.FunctionTimedOut) as e:
            reject(e)

    executor.submit(resolver)


GLOBAL_RUN_AND_FORGET = concurrent.futures.ThreadPoolExecutor(max_workers=2 * multiprocessing.cpu_count())


def run_and_forget(call_this):
    """
    Run a method on a remote worker without caring about the result, if it ever comes
    """
    GLOBAL_RUN_AND_FORGET.submit(call_this)


@stoppable
def timeout_iterator(iterable, timeout):
    """
    Iterates over an iterator, and counting time between yields of the given iterator.
    If the iterator stalls for too long since the last yield - this function raises StopThreadException.
    This has been benchmarked to run at about 100k yields per second, which is a latency of 0.01ms per yield.
    :param iterable: iterator to iterate
    :param timeout: timeout, in seconds
    :raises: func_timeout.exceptions.FunctionTimedOut
    :return: Whatever the iterator is supposed to return, or exception
    """
    q = queue.Queue()
    # this is a dummy object to represent the end of the iterator
    finished_queue = object()

    # iterate the iterator into a queue
    @stoppable
    def iterate_into_queue():
        for x in iterable:
            q.put(x)
        q.put(finished_queue)

    t = threading.Thread(target=iterate_into_queue, daemon=True)
    t.start()

    def checker():
        started = datetime.now()
        while True:
            try:
                item = q.get(block=True, timeout=timeout)
                if item is finished_queue:
                    return
                yield item
            except queue.Empty:
                ThreadStopper.async_raise([t.ident])
                raise func_timeout.exceptions.FunctionTimedOut(timedOutAfter=(datetime.now() - started).total_seconds(),
                                                               timedOutFunction=iterate_into_queue,
                                                               timedOutArgs=[],
                                                               timedOutKwargs={})

    return checker()


class MultiLocker(object):
    """
    Locks many locks in once
    """

    def __init__(self, locks):
        self.__locks = locks

    def acquire(self):
        for l in self.__locks:
            l.acquire()

    def release(self):
        for l in self.__locks[::-1]:
            l.release()

    def __enter__(self, *args, **kwargs):
        self.acquire()
        return self

    def __exit__(self, *args, **kwargs):
        self.release()


class LazyMultiLocker(object):
    """
    Allows for lazy locking on a per index basis.
    For example, you may want lock on "1", "2" and something else wants to lock "1" and "3".
    In this example, these locks have a nonempty intersection, therefore these locks will lock "as if" they
    are the same lock. Locking one will make locking the other sleep until the first lock is released.
    """

    def __init__(self):
        self.__locks = {}

    def get_lock(self, indexes: list) -> MultiLocker:
        """
        Get a lock that will be the "union" lock of all indexes
        :param indexes: List of anything sortable that act as indexes
        :return:
        """
        return MultiLocker([self.__locks.setdefault(i, RLock()) for i in sorted(str(x) for x in indexes)])

    def is_any_locked(self) -> bool:
        """
        Returns whether any lock is used
        :return:
        """
        return any(x.locked() for x in self.__locks.values())
