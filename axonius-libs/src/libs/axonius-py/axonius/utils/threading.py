import concurrent.futures
import multiprocessing
import queue
import sys
from datetime import datetime
from threading import RLock
import logging

from apscheduler.executors.pool import BasePoolExecutor

from axonius.thread_stopper import ThreadStopper, StopThreadException

import func_timeout


logger = logging.getLogger(f'axonius.{__name__}')


class ReusableThread:
    """
    A thread that you can call "start" many times without having the following exception
        RuntimeError: threads can only be started once
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__build_executor()

    def __build_executor(self):
        """
        Makes a new executor for threads
        """
        self.__executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='ReusableThread')

    def start(self, target):
        """
        Runs the target function on the thread
        assumes the thread is stable
        :param target: function target to run
        """
        self.__executor.submit(target)

    def terminate_thread(self):
        """
        Makes sure the thread does not continue execution
        """
        threads = list(self.__executor._threads)
        if not threads:
            return

        thread = threads[0]

        logger.info(f'Stopping thread {thread}')
        ThreadStopper.async_raise([thread.ident])
        self.__executor.shutdown(wait=False)
        self.__build_executor()

    def __str__(self):
        threads = list(self.__executor._threads)
        thread_str = ', '.join(str(x) for x in list(self.__executor._threads))
        return f'{super().__str__()} with {len(threads)} threads - {thread_str}'


def run_in_thread_helper(thread: ReusableThread, method_to_call, resolve, reject, *_, args=None, kwargs=None, **__):
    """
    Helps with running Promises in a ReusableThread
    :param thread: thread to call on
    :param method_to_call: method to run
    :param resolve: will be called if method returns
    :param reject: will be called with exception from method
    :param args: args to method_to_call
    :param kwargs: kwargs to method_to_call
    """
    args = args or []
    kwargs = kwargs or {}

    def resolver():
        try:
            resolve(method_to_call(*args, **kwargs))
        except Exception as e:
            logger.exception(f'Exception in {method_to_call.__name__} using thread {thread}')
            reject(e)
        except (StopThreadException, func_timeout.exceptions.FunctionTimedOut):
            logger.exception(f'StopThread or Timeout in {method_to_call.__name__} using thread {thread}')

    thread.start(resolver)


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


class ThreadPoolExecutorReusable(BasePoolExecutor):
    """
    An executor that runs jobs in the pool given
    """

    def __init__(self, pool):
        super(ThreadPoolExecutorReusable, self).__init__(pool)


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

    out_exception = [None]

    # iterate the iterator into a queue
    def iterate_into_queue():
        try:
            for x in iterable:
                q.put(x)
        except BaseException as e:
            out_exception[0] = e
        finally:
            q.put(finished_queue)

    t = ReusableThread()
    t.start(iterate_into_queue)

    def checker():
        started = datetime.now()
        while True:
            try:
                item = q.get(block=True, timeout=timeout)
                if item is finished_queue:
                    if out_exception[0]:
                        raise out_exception[0]
                    return
                yield item
            except queue.Empty:
                t.terminate_thread()
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
