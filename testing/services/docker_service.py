import subprocess
import os
from abc import abstractmethod

from services.axon_service import AxonService, TimeoutExpception
from services.ports import DOCKER_PORTS
from test_helpers.exceptions import ComposeException


class DockerService(AxonService):
    def __init__(self, container_name, service_dir):
        super().__init__()
        self.container_name = container_name
        self.service_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', service_dir))
        self.log_dir = os.path.abspath(os.path.join("..", "logs", self.container_name))
        self._process_owner = False

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def take_process_ownership(self):
        self._process_owner = True

    @property
    def inner_port(self):
        return 80

    @property
    def exposed_port(self):
        return DOCKER_PORTS[self.container_name]

    @property
    def image(self):
        return f'axonius/{self.container_name}'

    @property
    def volumes(self):
        return [f'{self.container_name}_data:/home/axonius', '{0}:/home/axonius/logs'.format(self.log_dir)]

    @property
    def volumes_override(self):
        return []

    @property
    def environment(self):
        return []

    def start(self, mode='', allow_restart=False):
        assert mode in ('prod', '')
        assert self._process_owner, "Only process owner should be able to stop or start the fixture!"

        logsfile = os.path.join(self.log_dir, "{0}_docker.log".format(self.container_name))

        docker_up = ['docker', 'run', '--name', self.container_name, '--network=axonius', '--publish',
                     f'{self.exposed_port}:{self.inner_port}', '--detach']
        volumes = self.volumes

        if mode == 'prod':
            docker_up.extend(['--restart', 'always'])
        else:
            volumes.extend(self.volumes_override)

        for volume in volumes:
            docker_up.extend(['--volume', volume])
        for env in self.environment:
            docker_up.extend(['--env', env])

        docker_up.append(self.image)

        if self.get_is_container_up(True):
            if allow_restart:
                self.remove_container()
            else:
                print(f'Container {self.container_name} already created - consider removing it and running again')
        if self.get_image_exists():
            print(f'Container {self.container_name} already built - skipping build step')
        else:
            self.build()

        print(' '.join(docker_up))
        subprocess.check_call(docker_up, cwd=self.service_dir)

        # redirect logs to logfile. Make sure redirection lives as long as process lives
        if os.name == 'nt':  # windows
            os.system(f"cd {self.service_dir}; start cmd docker logs -f {self.container_name} >> {logsfile} 2>&1")
        else:  # good stuff
            os.system(f"cd {self.service_dir}; docker logs -f {self.container_name} >> {logsfile} 2>&1 &")

    def build(self):
        subprocess.call(['docker', 'build', '.', '--tag', f'axonius/{self.container_name}'], cwd=self.service_dir)

    def get_is_container_up(self, include_not_running=False):
        docker_cmd = ['docker', 'ps', '--filter', f'name={self.container_name}']
        if include_not_running:
            docker_cmd.append('--all')
        return self.container_name in subprocess.check_output(docker_cmd).decode('utf-8')

    def get_image_exists(self):
        output = subprocess.check_output(['docker', 'images', f'axonius/{self.container_name}']).decode('utf-8')
        return self.container_name in output

    def remove_image(self):
        subprocess.call(['docker', 'rmi', f'axonius/{self.container_name}', '--force'], cwd=self.service_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self, should_delete=False):
        assert self._process_owner, "Only process owner should be able to stop or start the fixture!"

        # killing the container is faster than down. but killing it will make some apps not flush their data
        # to the disk, so we give it a second.
        subprocess.call(['docker', 'stop', '--time', '3', self.container_name], cwd=self.service_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.remove_container(remove_volumes=should_delete)

    def remove_container(self, remove_volumes=False):
        subprocess.call(['docker', 'rm', '--force', self.container_name] + (['--volumes'] if remove_volumes else []),
                        cwd=self.service_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def remove_volume(self):
        subprocess.call(['docker', 'volume', 'rm', f"{self.container_name}_data"], cwd=self.service_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def start_and_wait(self, mode='', allow_restart=False):
        """
        Take notice that the constructor already calls 'start' method. So use this function only
        after manual stop
        """
        self.start(mode=mode, allow_restart=allow_restart)
        self.wait_for_service()

    def get_file_contents_from_container(self, file_path):
        """
        Gets the contents of an internal file.
        :param file_path: the absolute path inside the container.
        :return: the contents
        """

        p = subprocess.Popen(['docker', 'exec', self.container_name, 'cat', file_path],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()

        if p.returncode != 0:
            raise ComposeException("Failed to run 'cat' on docker {0}".format(self.container_name))

        return out, err, p.returncode

    def run_command_in_container(self, command):
        """
        Gets any bash command to execute in this service's docker

        :param command:
        :return:
        """
        p = subprocess.Popen(['docker', 'exec', self.container_name, 'bash', '-c', command],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()

        if p.returncode != 0:
            raise ComposeException("Failed to run {0} on docker {1}".format(command, self.container_name))

        return out, err, p.returncode

    @abstractmethod
    def is_up(self):
        pass

    def wait_for_service(self, timeout=30):
        if timeout > 5:
            try:
                super().wait_for_service(timeout=5)
            except TimeoutExpception:
                try:
                    if subprocess.check_output(['docker', 'exec', '-it',
                                                self.container_name, '/bin/ls']).decode('utf-8') == '':
                        print('Mount failed - please check host sharing settings')
                except:
                    pass
                raise
            timeout -= 5
        super().wait_for_service(timeout=timeout)
