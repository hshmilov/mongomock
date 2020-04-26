import time
from abc import ABC, abstractmethod
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TimeoutException(Exception):
    pass


class AxonService(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self, **kwargs):
        pass

    @abstractmethod
    def is_up(self, *args, **kwargs):
        pass

    def wait_for_service(self, timeout=180):
        success = False
        start = time.time()
        while time.time() - start < timeout:
            try:
                assert self.is_up(raise_via_core=False)
                success = True
                break
            except Exception:
                time.sleep(0.5)

        if not success:
            raise TimeoutException('Service failed to start')
