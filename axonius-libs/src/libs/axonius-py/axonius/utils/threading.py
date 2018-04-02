from threading import Lock


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

    executor.submit(resolver)


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
        return MultiLocker([self.__locks.setdefault(i, Lock()) for i in sorted(str(x) for x in indexes)])

    def is_any_locked(self) -> bool:
        """
        Returns whether any lock is used
        :return:
        """
        return any(x.locked() for x in self.__locks.values())
