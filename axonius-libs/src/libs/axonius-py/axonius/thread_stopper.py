import logging

logger = logging.getLogger(f'axonius.{__name__}')
import ctypes


class StopThreadException(BaseException):
    pass


class ThreadStopper(object):
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
