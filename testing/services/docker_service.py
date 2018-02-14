import subprocess
import os
from abc import abstractmethod

from services.axon_service import AxonService, TimeoutException
from services.ports import DOCKER_PORTS
from test_helpers.exceptions import DockerException
from test_helpers.parallel_runner import ParallelRunner


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
    def exposed_ports(self):
        """
        :return: list of pairs (exposed_port, inner_port)
        """
        return [(DOCKER_PORTS[self.container_name], 80)]

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

    def get_dockerfile(self, mode=''):
        return """
FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY src/ ./
"""[1:]

    def start(self, mode='', allow_restart=False, rebuild=False):
        assert mode in ('prod', '')
        assert self._process_owner, "Only process owner should be able to stop or start the fixture!"

        logsfile = os.path.join(self.log_dir, "{0}_docker.log".format(self.container_name))

        docker_up = ['docker', 'run', '--name', self.container_name, '--network=axonius', '--detach']

        for exposed in self.exposed_ports:
            docker_up.extend(['--publish', f'{exposed[0]}:{exposed[1]}'])

        volumes = self.volumes

        if mode == 'prod':
            docker_up.extend(['--restart', 'always'])
        else:
            volumes.extend(self.volumes_override)

        for volume in volumes:
            docker_up.extend(['--volume', volume])
        for env in self.environment:
            docker_up.extend(['--env', env])
        docker_up.extend(['--env', "DOCKER=true"])

        docker_up.append(self.image)

        if self.get_is_container_up(True):
            if allow_restart:
                self.remove_container()
            else:
                print(f'Container {self.container_name} already created - consider removing it and running again')
        if self.get_image_exists():
            if rebuild:
                self.remove_image()
                self.build(mode)
            else:
                print(f'Container {self.container_name} already built - skipping build step')
        else:
            self.build(mode)

        # print(' '.join(docker_up))
        print(f"Running container {self.container_name} in -{'production' if mode == 'prod' else 'debug'}- mode.")
        subprocess.check_call(docker_up, cwd=self.service_dir, stdout=subprocess.PIPE)

        # redirect logs to logfile. Make sure redirection lives as long as process lives
        if os.name == 'nt':  # windows
            os.system(f'start /B cmd /c "docker logs -f {self.container_name} >> {logsfile} 2>&1"')
        else:  # good stuff
            os.system(f"docker logs -f {self.container_name} >> {logsfile} 2>&1 &")

    def build(self, mode='', runner=None):
        docker_build = ['docker', 'build', '.']

        # If Dockerfile exists, use it, else use the provided Dockerfile test from self.get_dockerfile
        dockerfile_path = os.path.join(self.service_dir, 'Dockerfile')
        if not os.path.isfile(dockerfile_path):
            dockerfile = self.get_dockerfile(mode)
            assert dockerfile is not None

            # dump Dockerfile.autogen to local folder
            dockerfile_path += '.autogen'
            open(dockerfile_path, 'w').write('# This is an auto-generated file, Do not modify\n\n' + dockerfile)
            docker_build.extend(['-f', os.path.relpath(dockerfile_path, self.service_dir)])

        docker_build.extend(['--tag', self.image])

        wait = False
        if runner is None:  # runner is passed as a ParallelRunner
            runner = ParallelRunner()
            wait = True

        runner.append_single(self.container_name, docker_build, cwd=self.service_dir)

        if wait:
            assert runner.wait_for_all() == 0

    def get_is_container_up(self, include_not_running=False):
        docker_cmd = ['docker', 'ps', '--filter', f'name={self.container_name}']
        if include_not_running:
            docker_cmd.append('--all')
        return self.container_name in subprocess.check_output(docker_cmd).decode('utf-8')

    def get_image_exists(self):
        output = subprocess.check_output(['docker', 'images', self.image]).decode('utf-8')
        return self.container_name in output

    def remove_image(self):
        subprocess.call(['docker', 'rmi', self.image, '--force'], cwd=self.service_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self, should_delete=False):
        for _ in self.stop_async(should_delete=should_delete):
            pass

    def stop_async(self, should_delete=False):
        assert self._process_owner, "Only process owner should be able to stop or start the fixture!"

        # killing the container is faster than down. but killing it will make some apps not flush their data
        # to the disk, so we give it a second.
        process = subprocess.Popen(['docker', 'stop', '--time', '3', self.container_name], cwd=self.service_dir,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        yield process
        process.wait()
        self.remove_container(remove_volumes=should_delete)

    def remove_container(self, remove_volumes=False):
        subprocess.call(['docker', 'rm', '--force', self.container_name] + (['--volumes'] if remove_volumes else []),
                        cwd=self.service_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def remove_volume(self):
        subprocess.call(['docker', 'volume', 'rm', f"{self.container_name}_data"], cwd=self.service_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def start_and_wait(self, mode='', allow_restart=False, rebuild=False):
        """
        Take notice that the constructor already calls 'start' method. So use this function only
        after manual stop
        """
        self.start(mode=mode, allow_restart=allow_restart, rebuild=rebuild)
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
            raise DockerException("Failed to run 'cat' on docker {0}".format(self.container_name))

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
            raise DockerException("Failed to run {0} on docker {1}".format(command, self.container_name))

        return out, err, p.returncode

    @abstractmethod
    def is_up(self):
        pass

    def wait_for_service(self, timeout=30):
        if timeout > 3:
            try:
                super().wait_for_service(timeout=3)
            except TimeoutException:
                try:
                    if subprocess.check_output(['docker', 'exec', '-it',
                                                self.container_name, '/bin/ls']).decode('utf-8') == '':
                        print('Mount failed - please check host sharing settings')
                except:
                    pass
            timeout -= 3
        try:
            super().wait_for_service(timeout=timeout)
        except TimeoutException:
            raise TimeoutException(f'Service {self.container_name} failed to start')
