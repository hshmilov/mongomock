import json
import os
import shlex
import subprocess
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from retrying import retry

from axonius.consts.plugin_consts import (AXONIUS_SETTINGS_DIR_NAME,
                                          NODE_ID_ENV_VAR_NAME,
                                          NODE_ID_FILENAME)
from axonius.consts.system_consts import (AXONIUS_DNS_SUFFIX, AXONIUS_NETWORK,
                                          WEAVE_NETWORK, LOGS_PATH_HOST)
from axonius.utils.debug import COLOR
from services.axon_service import AxonService, TimeoutException
from services.ports import DOCKER_PORTS
from test_helpers.exceptions import DockerException
from test_helpers.parallel_runner import ParallelRunner


def retry_if_timeout(exception):
    """Return True if we should retry (in this case when it's a TimeoutException), False otherwise"""
    return isinstance(exception, TimeoutException)


# pylint: disable=too-many-branches, too-many-instance-attributes
class DockerService(AxonService):
    def __init__(self, container_name: str, service_dir: str):
        super().__init__()
        self._system_config = dict()
        self.container_name = container_name
        self.cortex_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        if not (Path(self.cortex_root_dir) / 'venv').is_dir:
            raise RuntimeError(f'Cortex dir is wrong ... {self.cortex_root_dir}')

        self.log_dir = str(LOGS_PATH_HOST / self.container_name)
        self.uploaded_files_dir = os.path.abspath(os.path.join(self.cortex_root_dir, 'uploaded_files'))
        if not os.path.exists(self.uploaded_files_dir):
            os.mkdir(self.uploaded_files_dir)
        self.shared_readonly_dir = os.path.abspath(os.path.join(self.cortex_root_dir, 'shared_readonly_files'))
        self.service_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', service_dir))
        self.package_name = os.path.basename(self.service_dir)
        self._process_owner = False
        self.service_class_name = container_name.replace('-', ' ').title().replace(' ', '')
        self.override_exposed_port = False
        self._id = None

    def take_process_ownership(self):
        self._process_owner = True

    @property
    def id(self):
        """
        :return: The current docker service's container id (if it already started).
        """
        if not self._id:
            inspect_command = shlex.split('docker inspect --format="{{.Id}}" ' + self.container_name)
            self._id = subprocess.check_output(inspect_command).decode('utf-8').strip()
        return self._id

    @property
    def inspect(self):
        inspect_command = shlex.split(f'docker inspect {self.container_name}')
        container_properties = json.loads(subprocess.check_output(inspect_command))
        return container_properties

    @property
    def fqdn(self):
        """
        :return: fqdn of the container including our dns domain suffix
        """
        return f'{self.container_name}.{AXONIUS_DNS_SUFFIX}'

    @property
    def service_name(self):
        return f'{self.container_name}'.replace('-', '_')

    @property
    def should_register_unique_dns(self):
        return False

    @property
    def exposed_ports(self):
        """
        :return: list of pairs (exposed_port, inner_port)
        """
        return [(DOCKER_PORTS[self.container_name], 443)]

    @property
    def image(self):
        return f'axonius/{self.container_name}'

    @property
    def run_timeout(self):
        return 60 * 3

    @property
    def volumes(self):
        return [
            f'{self.container_name}_data:/home/axonius',
            f'{self.log_dir}:/home/axonius/logs',
            f'{self.uploaded_files_dir}:/home/axonius/uploaded_files',
            f'{self.shared_readonly_dir}:/home/axonius/shared_readonly_files:ro'
        ]

    @property
    def volumes_override(self):
        return []

    @property
    def environment(self):
        return []

    @property
    def max_allowed_memory(self) -> int:
        """
        Max allowed memory in megabytes
        """
        return None

    @property
    def max_allowed_cpu(self) -> int:
        """
        Max allowed cpu usage. e.g. if you have 2 cpu's, return 1.5 to use only 1.5 of them.
        :return:
        """
        return None

    @property
    def get_max_uwsgi_threads(self) -> int:
        return 70

    @property
    def get_max_uwsgi_processes(self) -> int:
        return 1

    def get_dockerfile(self, *args, **kwargs):
        return f'''
FROM axonius/axonius-libs

# Set the working directory to /app
WORKDIR /home/axonius/app

# Copy the current directory contents into the container at /app
COPY ./ ./{self.package_name}/

# Link to libcrypto for RSA keys (originally was a problem for chef adapter)
RUN ln -s /lib/x86_64-linux-gnu/libcrypto.so.1.0.0 /lib/x86_64-linux-gnu/libcrypto.so
'''[1:]

    def get_uwsgi_file(self):
        return f'''
[uwsgi]
chdir = /home/axonius/app
module = main:wsgi_app

master = true
threads = {self.get_max_uwsgi_threads}
processes = {self.get_max_uwsgi_processes}

socket = /tmp/openresty-uwsgi.sock
chmod-socket = 666
vacuum = true

die-on-term = true

ignore-sigpipe = true
ignore-write-errors = true
disable-write-exception = true
buffer-size = 65535
'''[1:]

    def get_main_file(self):
        return f'''
from {self.package_name}.service import {self.service_class_name} as CurrentService
from axonius.utils.server import init_wsgi

if __name__ == '__main__':
    # Initialize
    service = CurrentService()

    # Run (Blocking)
    service.start_serve()
else:
    # Init wsgi if in it.
    wsgi_app = init_wsgi(CurrentService)
'''[1:]

    @property
    def docker_network(self):
        return AXONIUS_NETWORK

    @property
    def _additional_parameters(self) -> Iterable[str]:
        """
        Virtual by design
        Add more parameters to the docker up command at the end
        :return:
        """
        return []

    def _get_basic_docker_run_command_with_network(self):
        if self.docker_network == 'host':
            docker_up = ['docker', 'run', '--name', self.container_name, f'--network={self.docker_network}', '--detach']
        elif self.docker_network == WEAVE_NETWORK:
            docker_up = ['docker', 'run', '--name', self.container_name, '--detach']
        else:
            docker_up = ['docker', 'run', '--name', self.container_name, f'--network={self.docker_network}',
                         '--network-alias', self.fqdn, '--detach']

        return docker_up

    def _get_allowed_memory(self):
        allowed_memory = []
        max_allowed_memory = self.max_allowed_memory
        if max_allowed_memory:
            allowed_memory = [f'--memory={max_allowed_memory}m',
                              '--oom-kill-disable']  # don't kill my container
            print(f'Memory constraint: {max_allowed_memory}MB')
        return allowed_memory

    def _get_allowed_cpu(self):
        allowed_cpu = []
        max_allowed_cpu = self.max_allowed_cpu
        if max_allowed_cpu:
            assert isinstance(max_allowed_cpu, float), \
                f'max allowed cpu is {max_allowed_cpu}, expected float'
            allowed_cpu = [f'--cpus={max_allowed_cpu}']
            print(f'CPU constraints: {max_allowed_cpu} CPU\'s')

        return allowed_cpu

    def _get_exposed_ports(self, mode, expose_port):
        publish_ports = []
        publish_port_mode = '127.0.0.1:'  # bind host port only to localhost
        if mode != 'prod' or self.override_exposed_port or expose_port:
            publish_port_mode = ''  # if in debug mode or override_exposed_port is set, bind on all ips on host

        for exposed in self.exposed_ports:
            publish_ports.extend(['--publish', f'{publish_port_mode}{exposed[0]}:{exposed[1]}'])

        return publish_ports

    def _get_volumes(self):
        all_volumes = []
        volumes = self.volumes

        volumes.extend(self.volumes_override)

        for volume in volumes:
            all_volumes.extend(['--volume', volume])

        return all_volumes

    def _get_env_varaibles(self, docker_internal_env_vars):
        env_variables = []
        for env in self.environment:
            env_variables.extend(['--env', env])

        if docker_internal_env_vars is not None:
            for env in docker_internal_env_vars:
                env_variables.extend(['--env', env])

        env_variables.extend(['--env', 'DOCKER=true'])
        node_id_path = Path(
            os.path.abspath(os.path.join(self.cortex_root_dir, AXONIUS_SETTINGS_DIR_NAME, NODE_ID_FILENAME)))
        if node_id_path.is_file():
            env_variables.extend(['--env', f'{NODE_ID_ENV_VAR_NAME}={node_id_path.read_text().strip()}'])

        return env_variables

    # pylint: disable=arguments-differ
    def start(self,
              mode='',
              allow_restart=False,
              rebuild=False,
              hard=False,
              show_print=True,
              expose_port=False,
              extra_flags=None,
              docker_internal_env_vars=None,
              run_env=None):
        assert mode in ('prod', '')
        assert self._process_owner, 'Only process owner should be able to stop or start the fixture!'

        print(f'{COLOR.get("light_green", "<")}'
              f'Running container {self.container_name} in -{"production" if mode == "prod" else "debug"}- mode.'
              f'{COLOR.get("reset", ">")}')

        self._migrate_db()

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        logsfile = os.path.join(self.log_dir, '{0}.docker.log'.format(self.service_name))

        docker_up = self._get_basic_docker_run_command_with_network()

        docker_up.extend(self._get_allowed_memory())

        docker_up.extend(self._get_allowed_cpu())

        docker_up.extend(self._get_exposed_ports(mode, expose_port))

        docker_up.extend(['--restart', 'always'])

        docker_up.extend(self._get_volumes())

        docker_up.extend(self._get_env_varaibles(docker_internal_env_vars))

        docker_up.extend(extra_flags or [])

        docker_up.append(self.image)

        docker_up += self._additional_parameters

        if self.get_is_container_up(True):
            if allow_restart:
                self.remove_container()
            else:
                print(f'Container {self.container_name} already created - consider removing it and running again')
        if self.get_image_exists():
            if rebuild:
                self.build(mode, docker_internal_env_vars=docker_internal_env_vars)
            elif show_print:
                print(f'Container {self.container_name} already built - skipping build step')
        else:
            self.build(mode, docker_internal_env_vars=docker_internal_env_vars)

        if hard:
            self.remove_volume()

        cmd = ' '.join(docker_up)
        print(f'{cmd}')

        docker_run_process = subprocess.Popen(docker_up, cwd=self.service_dir, env=run_env, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
        all_output = docker_run_process.communicate(timeout=self.run_timeout)

        if docker_run_process.returncode != 0:
            all_output = ' '.join([current_output_stream.decode('utf-8') for current_output_stream in all_output])
            raise Exception(f'Failed to start container {self.container_name}', f'failure output is: {all_output}')

        self._id = all_output[0].decode('utf-8')

        # redirect logs to logfile. Make sure redirection lives as long as process lives
        if os.name == 'nt':  # windows
            os.system(f'start /B cmd /c "docker logs -f {self.container_name} >> {logsfile} 2>&1"')
        else:  # good stuff
            os.system(f'docker logs -f {self.container_name} >> {logsfile} 2>&1 &')

    def build(self, mode='', runner=None, docker_internal_env_vars=None, **kwargs):
        docker_build = ['docker', 'build', '.']

        # If Dockerfile exists, use it, else use the provided Dockerfile from self.get_dockerfile
        dockerfile_path = os.path.join(self.service_dir, 'Dockerfile')
        if os.path.isfile(dockerfile_path):
            dockerfile = open(dockerfile_path, 'r').read()
        else:
            dockerfile = self.get_dockerfile(docker_internal_env_vars=docker_internal_env_vars)
            assert dockerfile is not None

        # Append the main.py file creation
        main_file_data = self.get_main_file().replace('\n', '\\n')
        assert '"' not in main_file_data
        if len(main_file_data) > 0:
            dockerfile += f'\nRUN echo "{main_file_data}" > ./main.py'

        # Append the main.py file creation
        uwsgi_file = self.get_uwsgi_file().replace('\n', '\\n')
        assert '"' not in uwsgi_file
        if len(uwsgi_file) > 0:
            dockerfile += f'\nRUN echo "{uwsgi_file}" > /etc/uwsgi.ini'

        # dump Dockerfile.autogen to local folder
        autogen_path = dockerfile_path + '.autogen'
        open(autogen_path, 'w').write('# This is an auto-generated file, Do not modify\n\n' + dockerfile)
        docker_build.extend(['-f', os.path.relpath(autogen_path, self.service_dir)])

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

    def get_container_id(self, stopped=False):
        docker_cmd = ['docker', 'ps', '--filter', f'name={self.container_name}', '-q']
        if stopped:
            docker_cmd.append('-a')
        return subprocess.check_output(docker_cmd).decode('utf-8')

    def get_image_exists(self):
        output = subprocess.check_output(['docker', 'images', self.image]).decode('utf-8')
        return self.container_name in output

    def remove_image(self):
        subprocess.call(['docker', 'rmi', self.image, '--force'], cwd=self.service_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self, **kwargs):
        for _ in self.stop_async(**kwargs):
            pass

    def stop_async(self, should_delete=False, remove_image=False, remove_volume=False):
        assert self._process_owner, 'Only process owner should be able to stop or start the fixture!'

        # killing the container is faster than down. but killing it will make some apps not flush their data
        # to the disk, so we give it a second.
        process = subprocess.Popen(['docker', 'stop', '--time', '10', self.container_name], cwd=self.service_dir,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        yield process
        process.wait()
        self.remove_container(remove_volumes=remove_volume)
        if remove_image:
            self.remove_image()
        if remove_volume:
            self.remove_volume()

    def remove_container(self, remove_volumes=False):
        # --volumes will remove only non-named volumes
        if remove_volumes is True:
            print(f'{COLOR.get("red", "<")}Deleting volume of container {self.container_name}...'
                  f'{COLOR.get("reset", ">")}')
        subprocess.call(['docker', 'rm', '--force', self.container_name] + (['--volumes'] if remove_volumes else []),
                        cwd=self.service_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def remove_volume(self):
        if self.get_is_container_up():
            print(f'Container {self.container_name} still in use, skipping remove data volume '
                  f'\'{self.container_name}_data\'')
            return  # docker volume rm will fail otherwise...
        print(f'{COLOR.get("red", "<")}Deleting volume of container {self.container_name}...'
              f'{COLOR.get("reset", ">")}')
        subprocess.call(['docker', 'volume', 'rm', f'{self.container_name}_data'], cwd=self.service_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def start_and_wait(self, **kwargs):
        """
        Take notice that the constructor already calls 'start' method. So use this function only
        after manual stop
        """
        self.start(**kwargs)
        self.wait_for_service()

    @retry(stop_max_attempt_number=3, wait_fixed=5)
    def get_file_contents_from_container(self, file_path):
        """
        Gets the contents of an internal file.
        :param file_path: the absolute path inside the container.
        :return: the contents
        """
        p = subprocess.Popen(['docker', 'exec', self.container_name, 'cat', file_path],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            (out, err) = p.communicate(timeout=60)
        except subprocess.TimeoutExpired as e:
            p.terminate()
            print(f'Got timeout expired on {file_path} - {e}')
            raise

        if p.returncode != 0:
            raise DockerException(f'Failed to run "cat" on {self.container_name}: {str(out)}\n{str(err)}')

        return out, err, p.returncode

    def run_command_in_container(self, command):
        """
        Gets any bash command to execute in this service's docker

        :param command:
        :return:
        """
        p = subprocess.Popen(['docker', 'exec', self.container_name, 'bash', '-c', command],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate(timeout=60)

        if p.returncode != 0:
            raise DockerException(f'Failed to run "{command}"" on {self.container_name}: {str(out)}\n{str(err)}')

        return out, err, p.returncode

    @abstractmethod
    def is_up(self):
        pass

    def wait_for_service(self, timeout=180):
        if timeout > 3:
            try:
                super().wait_for_service(timeout=3)
            except TimeoutException:
                try:
                    if subprocess.check_output(['docker', 'exec', '-it',
                                                self.container_name, '/bin/ls']).decode('utf-8') == '':
                        print('Mount failed - please check host sharing settings')
                except Exception:
                    pass
            timeout -= 3
        try:
            super().wait_for_service(timeout=timeout)
        except TimeoutException:
            raise TimeoutException(f'Service {self.container_name} failed to start')

    def _migrate_db(self):
        """
        This is called right before running the docker.
        This is a good place to put any DB upgrades.
        """

    @contextmanager
    def contextmanager(self, *, should_delete=True, take_ownership=False):
        if take_ownership:
            self.take_process_ownership()
        try:
            self.start_and_wait()
            yield self
        finally:
            self.stop(should_delete=should_delete)

    def set_system_config(self, system_config):
        if system_config:
            self._system_config = system_config
