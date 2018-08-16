import subprocess

from services.docker_service import DockerService


class SeleniumService(DockerService):
    def is_up(self):
        return True

    def __init__(self):
        name = 'grid'
        super().__init__(name, '')

    def start(self,
              mode='',
              allow_restart=False,
              rebuild=False,
              hard=False,
              show_print=True,
              expose_port=False,
              extra_flags=None):
        extra_flags = ['-e', 'TZ="Asia/Jerusalem"', '--privileged']
        super().start(mode=mode,
                      allow_restart=allow_restart,
                      rebuild=rebuild,
                      hard=hard,
                      show_print=show_print,
                      expose_port=expose_port,
                      extra_flags=extra_flags)

    def get_dockerfile(self, mode=''):
        return ''

    def get_main_file(self):
        return ''

    def build(self, mode='', runner=None):
        docker_pull = ['docker', 'pull', self.image]
        if runner is None:
            print(' '.join(docker_pull))
            subprocess.check_output(docker_pull, cwd=self.service_dir)
        else:
            runner.append_single(self.container_name, docker_pull, cwd=self.service_dir)

    @property
    def volumes(self):
        return ['/dev/shm:/dev/shm']

    @property
    def exposed_ports(self):
        return [(4444, 24444), (5900, 25900)]

    @property
    def image(self):
        return 'elgalu/selenium'

    def wait_for_service(self, timeout=70):
        super().wait_for_service(timeout=timeout)
        p = subprocess.Popen(['docker', 'exec', self.container_name, 'wait_all_done', '30s'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
