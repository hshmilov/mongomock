import threading


class AtomicInteger:
    def __init__(self, value=0):
        self.__value = value
        self.__lock = threading.Lock()

    def inc(self):
        with self.__lock:
            self.__value += 1
            return self.__value

    def dec(self):
        with self.__lock:
            self.__value -= 1
            return self.__value

    @property
    def value(self) -> int:
        return self.__value
