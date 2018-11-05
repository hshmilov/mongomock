import logging
logger = logging.getLogger(f'axonius.{__name__}')
import functools
import threading
import ctypes


class StopThreadException(BaseException):
    pass


def call_with_stoppable(func, args=(), kwargs={}):
    if ThreadStopper.stopped.isSet():
        return
    with ThreadStopper.stoppable_threads_lock:
        tid = threading.get_ident()
        logger.debug(f'Adding {tid} to stoppable threads on function {func}')
        ThreadStopper.stoppable_threads.append(tid)
    try:
        r = func(*args, **kwargs)
    finally:
        with ThreadStopper.stoppable_threads_lock:
            ThreadStopper.stoppable_threads.remove(tid)
        logger.debug(f'removing {tid}')
    return r

# see documentation at https://axonius.atlassian.net/wiki/x/CgCZJg


def stoppable(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        return call_with_stoppable(f, args=args, kwargs=kwargs)
    return wrapped


class ThreadStopper(object):
    stoppable_threads = list()  # can't use set due to inheritance (have to support multiple inserts)
    stopped = threading.Event()
    stoppable_threads_lock = threading.Lock()

    @classmethod
    def async_raise(cls, tids):
        """
        Raises a stop in the threads with id tid
        """
        set_async_exc = ctypes.pythonapi.PyThreadState_SetAsyncExc
        set_async_exc.argtypes = (ctypes.c_ulong, ctypes.py_object)
        for tid in tids:
            exception = ctypes.py_object(StopThreadException)
            res = set_async_exc(tid, exception)
            if res == 0:
                # ValueError - "invalid thread id"
                logger.warning(f'invalid thread id {tid}')
            elif res != 1:
                # "if it returns a number greater than one, you're in trouble,
                # and you should call it again with exc=NULL to revert the effect"
                ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
                logger.error(f"raising stop in the remote thread {tid} failed: {res}")

    @classmethod
    def stop_all(cls):
        """Raises an exception in the context of this thread.

                If the thread is busy in a system call (time.sleep(),
                socket.accept(), ...), the exception is defered to the time the function returns.

                CAREFUL : this function is executed in the context of the
                caller thread, to raise an excpetion in the context of the
                thread represented by this instance.
                """
        logger.info(f'stopping {cls.stoppable_threads}')
        tids = list(reversed(cls.stoppable_threads))  # stopping each thread only once
        cls.async_raise(tids)
