import shlex
import subprocess

from axonius.consts.plugin_consts import AXONIUS_DNS_SUFFIX, CORE_UNIQUE_NAME
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService


class CoreProxyService(WeaveService):
    def is_up(self, *args, **kwargs):
        return True

    def __init__(self):
        super().__init__(self.name, '')

    @property
    def name(self):
        return 'core-proxy'

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[CORE_UNIQUE_NAME], DOCKER_PORTS[CORE_UNIQUE_NAME])]

    @property
    def _additional_parameters(self):
        """
        Virtual by design
        Add more parameters to the docker up command at the end
        :return:
        """
        core_port = DOCKER_PORTS[CORE_UNIQUE_NAME]

        return shlex.split(f'tcp-listen:{core_port},reuseaddr,fork,'
                           f'forever tcp:{CORE_UNIQUE_NAME}.{AXONIUS_DNS_SUFFIX}:443')

    def get_dockerfile(self, *args, **kwargs):
        return ''

    def get_main_file(self):
        return ''

    @property
    def volumes(self):
        return []

    def build(self, mode='', runner=None, docker_internal_env_vars=None, **kwargs):
        docker_pull = ['docker', 'pull', self.image]
        if runner is None:
            print(' '.join(docker_pull))
            subprocess.check_output(docker_pull, cwd=self.service_dir)
        else:
            runner.append_single(self.container_name, docker_pull, cwd=self.service_dir)

    def get_image_exists(self):
        output = subprocess.check_output(['docker', 'images', self.image]).decode('utf-8')
        return self.image in output

    @property
    def image(self):
        return 'nexus.pub.axonius.com/alpine/socat'
