import shlex
import subprocess

import docker

from axonius.consts.plugin_consts import AXONIUS_DNS_SUFFIX
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService, is_weave_up


class TunnelerService(WeaveService):

    def check_ssh(self):
        client = docker.from_env()
        instance_control = client.containers.list(filters={'name': 'instance-control'})[0]
        result = instance_control.exec_run(
            f'ssh -o StrictHostKeyChecking=no -p {DOCKER_PORTS[self.name]} '
            f'ubuntu@{self.name}.{AXONIUS_DNS_SUFFIX} "echo blah"')
        return result

    def is_up(self, *args, **kwargs):
        try:
            return 'Permission denied, please try again.' in self.check_ssh().output.decode('utf-8')
        except Exception:
            return False

    def __init__(self):
        super().__init__(self.name, '')

    @property
    def name(self):
        return 'tunneler'

    @property
    def _additional_parameters(self):
        """
        Virtual by design
        Add more parameters to the docker up command at the end
        :return:
        """
        if not is_weave_up():
            print('Weave network is down.')
            return []

        host_ip = subprocess.check_output(shlex.split('weave dns-args')).decode('utf-8')
        host_ip = [x for x in host_ip.split() if '--dns' in x][0]
        host_ip = host_ip[len('--dns='):]

        return shlex.split(f'tcp-listen:{DOCKER_PORTS[self.name]},reuseaddr,fork,forever tcp:{host_ip}:22')

    def start(self, *args, **kwargs):  # pylint: disable=arguments-differ
        if len(self._additional_parameters) == 0:
            print(f'{self.name} should not run without weave.')
            return

        super().start(*args, **kwargs)

    def get_dockerfile(self, *args, **kwargs):
        return ''

    def get_main_file(self):
        return ''

    @property
    def volumes(self):
        return []

    @property
    def exposed_ports(self):
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
