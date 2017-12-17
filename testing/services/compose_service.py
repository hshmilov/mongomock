import subprocess
import os
from abc import abstractmethod
import services.axon_service


class ComposeService(services.axon_service.AxonService):
    def __init__(self, compose_file_path, container_name, should_start=True, *vargs, **kwargs):
        super().__init__(*vargs, **kwargs)
        self._compose_file_path = compose_file_path
        self.container_name = container_name

        if should_start:
            self.start()

        self.log_dir = os.path.join("..", "logs", self.container_name)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def start(self):
        self.stop(should_delete=False)
        subprocess.check_call(['docker-compose', 'up', '-d'],
                              cwd=os.path.dirname(self._compose_file_path))

    def stop(self, should_delete=True):
        stdlog = open(os.path.join("..", "logs", "{0}_docker_std_logs.log".format(self.container_name)), "a")
        errlog = open(os.path.join("..", "logs", "{0}_docker_err_logs.log".format(self.container_name)), "a")

        subprocess.call(['docker-compose', 'logs'],
                        cwd=os.path.dirname(self._compose_file_path), stderr=errlog, stdout=stdlog)
        subprocess.call(['docker-compose', 'stop'],
                        cwd=os.path.dirname(self._compose_file_path))

        if should_delete:
            subprocess.call(['docker-compose', 'down', "--volumes"],
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
