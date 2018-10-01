import os
import subprocess
from typing import Iterable

from services.docker_service import DockerService
from services.ports import DOCKER_PORTS


class SyslogService(DockerService):
    def __init__(self):
        super().__init__(self.name, '')
        self.__syslog_dir = os.path.abspath(os.path.join(self.log_dir, 'syslogs/'))
        if not os.path.exists(self.__syslog_dir):
            os.makedirs(self.__syslog_dir)

        self.__conf_file = os.path.abspath(
            os.path.join(self.cortex_root_dir, 'testing', 'services', 'standalone_services', 'syslog-ng.conf'))

    def is_up(self):
        return True

    @property
    def name(self):
        return 'syslog'

    @property
    def port(self):
        return DOCKER_PORTS[self.name]

    def get_dockerfile(self, mode=''):
        return ''

    def get_main_file(self):
        return ''

    @property
    def volumes_override(self):
        return [
            f'{self.__syslog_dir}:/var/log/syslog-ng',
            f'{self.__conf_file}:/etc/syslog-ng/syslog-ng.conf'
        ]

    def get_syslog_data(self) -> Iterable[str]:
        """
        Get all lines from the syslog
        """
        out, _, _ = self.get_file_contents_from_container('/var/log/syslog-ng/syslog.log')
        return [x.decode('ascii') for x in out.splitlines()]

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
        return []

    @property
    def image(self):
        return 'bobrik/syslog-ng'
