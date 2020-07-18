import shlex
import subprocess

from axonius.consts.plugin_consts import MONGO_UNIQUE_NAME
from axonius.consts.system_consts import DOCKERHUB_URL
from services.ports import DOCKER_PORTS
from services.system_service import SystemService
from services.weave_service import WeaveService


class RemoteMongoProxyService(SystemService, WeaveService):
    def is_up(self, *args, **kwargs):
        return True

    def __init__(self):
        super().__init__(self.name, '')

    @property
    def name(self):
        return 'mongo'

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[MONGO_UNIQUE_NAME], DOCKER_PORTS[MONGO_UNIQUE_NAME])]

    @property
    def _additional_parameters(self):
        """
        Virtual by design
        Add more parameters to the docker up command at the end
        :return:
        """
        mongo_port = DOCKER_PORTS[MONGO_UNIQUE_NAME]
        weave_dns_lookup_command = shlex.split(f'weave dns-lookup {self.fqdn}')
        dns_lookup_result = subprocess.check_output(weave_dns_lookup_command).decode('utf-8')
        mongo_ip = dns_lookup_result.splitlines()[0]
        return shlex.split(f'tcp-listen:{mongo_port},reuseaddr,fork,'
                           f'forever tcp:{mongo_ip}:{mongo_port}')

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

    def add_weave_dns_entry(self):
        """
        we dont want to register dns for this service on weave
        :return:
        """
        return

    @property
    def should_register_unique_dns(self):
        return False

    @property
    def image(self):
        return f'{DOCKERHUB_URL}alpine/socat'
