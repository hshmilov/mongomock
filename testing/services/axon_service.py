import time
from abc import ABC, abstractmethod


class TimeoutException(Exception):
    pass


class AxonService(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def is_up(self):
        pass

    def wait_for_service(self, timeout=70):
        success = False
        start = time.time()
        while time.time() - start < timeout:
            try:
                assert self.is_up()
                success = True
                break
            except:
                time.sleep(0.25)

        if not success:
            raise TimeoutException("Service failed to start")
