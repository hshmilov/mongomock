import subprocess

from services.docker_service import DockerService
from pathlib import Path
import json
import hashlib


class DiagnosticsService(DockerService):
    def is_up(self):
        return True

    def __init__(self):
        name = 'diagnostics'
        self.diag_env_file = None
        super().__init__(name, f'../devops/{name}')

    def start(self, **kwargs):
        self.diag_env_file = Path(self.cortex_root_dir) / 'diag_env.json'
        if not self.diag_env_file.is_file():
            raise RuntimeError("env file is missing")

        diag_bytes = self.diag_env_file.read_bytes()
        new_hash = hashlib.sha1(diag_bytes).digest()

        hash_file = Path(self.service_dir) / "env_hash.bin"
        if hash_file.is_file():
            if hash_file.read_bytes() != new_hash:
                print('Diag env changed, forcing restart.')
                kwargs['allow_restart'] = True

        hash_file.open('wb').write(new_hash)

        super().start(**kwargs)

    def get_dockerfile(self, mode=''):
        return ''

    def get_main_file(self):
        return ''

    @property
    def environment(self):
        env = json.loads(self.diag_env_file.read_bytes())
        generated_env = Path(self.service_dir) / 'env_autogen.sh'
        with generated_env.open('wb') as env_file:
            for k, v in env.items():
                env_file.write(f'export {k}={v}\n'.encode())
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

    def stop_async(self, should_delete=False, remove_image=False):
        assert self._process_owner, "Only process owner should be able to stop or start the fixture!"

        # just kill the ssh server
        subprocess.Popen(['docker', 'kill', self.container_name], cwd=self.service_dir,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return super().stop_async(should_delete=should_delete, remove_image=remove_image)
