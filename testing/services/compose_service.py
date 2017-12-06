import subprocess
import os
from abc import abstractmethod
import datetime

import services.axon_service


class ComposeService(services.axon_service.AxonService):
    def __init__(self, compose_file_path, container_name):
        super().__init__()
        self._compose_file_path = compose_file_path
        self.container_name = container_name
        self.start()

    def start(self):
        self.stop()
        subprocess.check_call(['docker-compose', 'up', '-d'],
                              cwd=os.path.dirname(self._compose_file_path))

    def stop(self, should_delete=True):
        # No need to stop if its not there.
        p = subprocess.Popen(
            ['docker', 'ps', '--filter', 'name={0}'.format(self.container_name)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        if self.container_name in out.decode("utf-8"):
            p = subprocess.Popen(['docker', 'logs', self.container_name],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = p.communicate()
            with open(os.path.join("..", "logs", "{0}_docker_logs.txt".format(self.container_name)), "a") as f:
                f.write("====== START docker logs {0} ===========".format(self.container_name))
                f.write("out:")
                f.write(out.decode("utf-8"))
                f.write("err:")
                f.write(err.decode("utf-8"))
                f.write("====== END   docker logs {0} ===========".format(self.container_name))

            p = subprocess.call(['docker-compose', 'stop'],
                                cwd=os.path.dirname(self._compose_file_path))

            if should_delete:
                p = subprocess.call(['docker-compose', 'rm', "-f"],
                                    cwd=os.path.dirname(self._compose_file_path))

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

        return (out, err, p.returncode)

    @abstractmethod
    def is_up(self):
        pass
