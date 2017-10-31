import subprocess
from abc import abstractmethod
import os

import testing.services.axon_service


class ComposeService(testing.services.axon_service.AxonService):

    def __init__(self, config_file_path):
        super().__init__()
        self._config_file_path = config_file_path

    def start(self):
        self.stop()
        subprocess.check_call(['docker-compose', '-f', self._config_file_path, 'up', '-d'])

    def stop(self):
        subprocess.call(['docker-compose', '-f', self._config_file_path, 'stop'])
        subprocess.call(['docker-compose', '-f', self._config_file_path, 'rm', '-f'])


    @abstractmethod
    def is_up(self):
        pass
