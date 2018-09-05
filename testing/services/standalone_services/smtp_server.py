import subprocess

from services.docker_service import DockerService
from services.ports import DOCKER_PORTS


class SMTPService(DockerService):
    def is_up(self):
        return True

    @property
    def name(self):
        return 'smtp'

    @property
    def port(self):
        return DOCKER_PORTS[self.name]

    def __init__(self):
        super().__init__(self.name, '')

    def get_dockerfile(self, mode=''):
        return ''

    def get_main_file(self):
        return ''

    def build(self, mode='', runner=None):
        docker_pull = ['docker', 'pull', self.image]
        if runner is None:
            print(' '.join(docker_pull))
            subprocess.check_output(docker_pull, cwd=self.service_dir)
        else:
            runner.append_single(self.container_name, docker_pull, cwd=self.service_dir)

    @property
    def volumes(self):
        return []

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[self.name], DOCKER_PORTS[self.name])]

    @property
    def image(self):
        return 'namshi/smtp'
