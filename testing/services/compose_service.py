import subprocess
import os
from abc import abstractmethod
from services.axon_service import AxonService
from services.compose_parser import ServiceYmlParser
from test_helpers.exceptions import ComposeException


class ComposeService(AxonService):
    def __init__(self, compose_file_path, override_compose_file_path=None, **kwargs):
        super().__init__(**kwargs)
        self._compose_file_path = compose_file_path
        self._override_compose_file_path = override_compose_file_path
        self.parsed_compose_file = ServiceYmlParser(compose_file_path)
        self.container_name = self.parsed_compose_file.container_name
        self.workdir = os.path.abspath(os.path.dirname(self._compose_file_path))
        self.log_dir = os.path.abspath(os.path.join("..", "logs", self.container_name))

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def start(self):
        logsfile = os.path.join(self.log_dir, "{0}_docker.log".format(self.container_name))

        docker_up = ['docker-compose', '-f', os.path.relpath(self._compose_file_path, self.workdir)]
        if self._override_compose_file_path is not None:
            docker_up.extend(['-f', os.path.relpath(self._override_compose_file_path, self.workdir)])
        docker_up.extend(['up', '-d'])
        subprocess.check_call(docker_up, cwd=self.workdir)

        # redirect logs to logfile. Make sure redirection lives as long as process lives
        if os.name == 'nt':  # windows
            os.system(f"cd {self.workdir}; start cmd docker-compose logs -f >> {logsfile} ")
        else:  # good stuff
            os.system(f"cd {self.workdir}; docker-compose logs -f >> {logsfile} &")

    def stop(self, should_delete=False):
        # killing the container is faster than down. Then we issue down to reverse any effects up had
        subprocess.call(['docker-compose', 'kill', '-S', 'SIGINT'], cwd=self.workdir,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.call(['docker-compose', 'down'], cwd=self.workdir)

        if should_delete:
            subprocess.call(['docker-compose', 'down', "--volumes"], cwd=self.workdir)

    def start_and_wait(self):
        """
        Take notice that the constructor already calls 'start' method. So use this function only
        after manual stop
        :return:
        """
        self.start()
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
