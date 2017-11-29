import subprocess
import os
from abc import abstractmethod

import services.axon_service


class ComposeService(services.axon_service.AxonService):
    def __init__(self, compose_file_path):
        super().__init__()
        self._compose_file_path = compose_file_path

    def start(self):
        self.stop()
        subprocess.check_call(['docker-compose', 'up', '-d'],
                              cwd=os.path.dirname(self._compose_file_path))

    def stop(self, should_delete=True):
        subprocess.call(['docker-compose', 'stop'],
                        cwd=os.path.dirname(self._compose_file_path))
        if should_delete:
            subprocess.call(['docker-compose', 'rm', "-f"],
                            cwd=os.path.dirname(self._compose_file_path))

    def start_and_wait(self):
        self.start()
        self.wait_for_service()

    @abstractmethod
    def is_up(self):
        pass
