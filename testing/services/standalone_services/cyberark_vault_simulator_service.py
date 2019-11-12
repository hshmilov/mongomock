import subprocess
from pathlib import Path

from services.weave_service import WeaveService


class CyberarkVaultSimulatorService(WeaveService):
    def __init__(self):
        super().__init__(self.name, '')
        self._conf_dir = Path(self.cortex_root_dir, 'testing', 'services', 'standalone_services',
                              'cyberark_vault_simulator')

    def is_up(self, *args, **kwargs):
        return True

    @property
    def name(self):
        return 'cyberark_vault_simulator'

    def get_dockerfile(self, *args, **kwargs):
        return ''

    def get_main_file(self):
        return ''

    def build(self, mode='', runner=None, docker_internal_env_vars=None, **kwargs):
        docker_pull = ['docker', 'pull', self.image]
        if runner is None:
            print(' '.join(docker_pull))
            subprocess.check_output(docker_pull, cwd=self.service_dir)
        else:
            runner.append_single(self.container_name, docker_pull, cwd=self.service_dir)

    @property
    def volumes_override(self):
        return [
            f'{self._conf_dir}/:/src'
        ]

    @property
    def volumes(self):
        return []

    @property
    def image(self):
        return 'jcdemo/flaskapp'
