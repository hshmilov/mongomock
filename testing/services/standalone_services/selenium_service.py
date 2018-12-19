import os
import subprocess
import shlex
import time

from services.docker_service import DockerService, is_weave_up
from services.ports import DOCKER_PORTS


class SeleniumService(DockerService):
    def is_up(self):
        return True

    def __init__(self):
        super().__init__('grid', '')

        self.selenium_files_path = os.path.abspath(os.path.join(self.cortex_root_dir, 'testing', 'selenium_tests'))
        if not os.path.exists(self.selenium_files_path):
            os.makedirs(self.selenium_files_path)

        if os.name == 'nt':
            # docker doesn't play nice without this
            self.selenium_files_path = self.selenium_files_path.replace('\\', '/')

    def start(self,
              mode='',
              allow_restart=False,
              rebuild=False,
              hard=False,
              show_print=True,
              expose_port=False,
              extra_flags=None,
              env_vars=None):
        extra_flags = ['-e', 'TZ="Asia/Jerusalem"', '--privileged']

        if not is_weave_up():
            extra_flags.append('--link=gui:gui.axonius.local')

        super().start(mode=mode,
                      allow_restart=allow_restart,
                      rebuild=rebuild,
                      hard=hard,
                      show_print=show_print,
                      expose_port=expose_port,
                      extra_flags=extra_flags)
        cmd = 'docker exec grid wait_all_done 30s'
        subprocess.Popen(shlex.split(cmd)).communicate()
        time.sleep(60)  # bug in selenium time causes tests to fail on servers the first time after docker cleanup

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
        return ['/dev/shm:/dev/shm',
                f'{self.selenium_files_path}:/home/seluser/selenium_tests']

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS['selenium-hub'], 24444), (DOCKER_PORTS['selenium-vnc'], 25900)]

    @property
    def image(self):
        return 'elgalu/selenium'

    # pylint: disable=arguments-differ
    def wait_for_service(self, **kwargs):
        super().wait_for_service(**kwargs)
        p = subprocess.Popen(['docker', 'exec', self.container_name, 'wait_all_done', '30s'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
