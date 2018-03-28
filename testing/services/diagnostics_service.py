import subprocess

from services.docker_service import DockerService
from pathlib import Path
import json


class DiagnosticsService(DockerService):
    def is_up(self):
        return True

    def __init__(self):
        name = 'diagnostics'
        super().__init__(name, f'../devops/{name}')

        self.diag_env_file = Path(self.cortex_root_dir) / 'diag_env.json'
        if not self.diag_env_file.is_file():
            raise RuntimeError("env file is missing")

    def get_dockerfile(self, mode=''):
        return ''

    def get_main_file(self):
        return ''

    @property
    def environment(self):
        env = json.loads(self.diag_env_file.read_bytes())
        for k, v in env.items():
            yield f'{k}={v}'

    @property
    def volumes(self):
        return [f'{self.service_dir}:/home/axonius/app']

    @property
    def exposed_ports(self):
        return []

    @property
    def docker_network(self):
        return 'host'

    def stop_async(self, should_delete=False):
        assert self._process_owner, "Only process owner should be able to stop or start the fixture!"

        # just kill the ssh server
        subprocess.Popen(['docker', 'kill', self.container_name], cwd=self.service_dir,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return super().stop_async(should_delete=should_delete)
