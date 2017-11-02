import pytest
from abc import ABC, abstractmethod
from retrying import retry


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

    def wait_for_service(self, interval=1000, num_intervals=300):
        @retry(wait_fixed=interval, stop_max_attempt_number=num_intervals)
        def check_if_up():
            assert self.is_up()

        check_if_up()
