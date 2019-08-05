import os
import subprocess
import time

from services.weave_service import is_weave_up, WeaveService
from services.ports import DOCKER_PORTS
from axonius.consts.system_consts import AXONIUS_DNS_SUFFIX


# pylint: disable=too-many-locals
class SeleniumService(WeaveService):
    def is_up(self, *args, **kwargs):
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
              docker_internal_env_vars=None,
              run_env=None):
        extra_flags = [
            '-e', 'TZ="Asia/Jerusalem"', '--privileged',
            '-e', 'SCREEN_WIDTH=1360', '-e', 'SCREEN_HEIGHT=1020'
        ]

        if not is_weave_up():
            extra_flags.append(f'--link=gui:gui.{AXONIUS_DNS_SUFFIX}')

        start_time = time.time()

        super().start(mode=mode,
                      allow_restart=allow_restart,
                      rebuild=rebuild,
                      hard=hard,
                      show_print=show_print,
                      expose_port=expose_port,
                      extra_flags=extra_flags,
                      docker_internal_env_vars=docker_internal_env_vars,
                      run_env=run_env)
        subprocess.check_output(['docker', 'exec', self.container_name, 'wait_all_done', '60s'])
        print(f'Selenium start ended successfully after {time.time() - start_time}.')
        time.sleep(60)  # bug in selenium time causes tests to fail on servers the first time after docker cleanup

    def get_dockerfile(self, *args, **kwargs):
        return ''

    def get_main_file(self):
        return ''

    def build(self, mode='', runner=None, docker_internal_env_vars=None, **kwargs):
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
    def wait_for_service(self, *args, **kwargs):
        super().wait_for_service(*args, **kwargs)
        subprocess.check_output(['docker', 'exec', self.container_name, 'wait_all_done', '60s'])
