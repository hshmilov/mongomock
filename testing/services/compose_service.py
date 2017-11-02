import subprocess
import os
from abc import abstractmethod

import services.axon_service


class ComposeService(services.axon_service.AxonService):

    def __init__(self, config_file_path):
        super().__init__()
        self._config_file_path = config_file_path

    def start(self):
        self.stop()
        subprocess.check_call(['docker-compose', 'up', '-d'], cwd=os.path.dirname(self._config_file_path))

    def stop(self):
        subprocess.call(['docker-compose', 'stop'], cwd=os.path.dirname(self._config_file_path))
        subprocess.call(['docker-compose', 'rm', "-f"], cwd=os.path.dirname(self._config_file_path))


    @abstractmethod
    def is_up(self):
        pass
