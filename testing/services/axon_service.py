from abc import ABC, abstractmethod
from retrying import retry


class AxonService(ABC):
    def __init__(self, *vargs, **kwargs):
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

    @retry(wait_fixed=1000, stop_max_delay=60 * 5 * 1000)  # Try every 0.25 seconds for 5 minutes
    def wait_for_service(self):
        assert self.is_up(), "Service failed to start"
