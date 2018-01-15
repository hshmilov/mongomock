import time
from abc import ABC, abstractmethod


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

    def wait_for_service(self, interval=0.25, num_intervals=4 * 30):

        success = False
        for x in range(1, num_intervals):
            try:
                assert self.is_up()
                success = True
                break
            except:
                time.sleep(interval)

        if not success:
            raise Exception("Service failed to start")
