import os
import subprocess
import sys
from abc import abstractmethod

from retrying import retry

from axonius.consts.plugin_consts import (AXONIUS_NETWORK, WEAVE_NETWORK,
                                          WEAVE_PATH)
from axonius.utils.debug import COLOR
from services.axon_service import TimeoutException
from services.docker_service import DockerService, retry_if_timeout

MAX_NUMBER_OF_RUN_TRIES = 2


def is_weave_up():
    """
    Executes "Weave status" (if we're running on a linux machine) and checks that weave is up.
    :return: bool that signifies if weave is up.
    """
    if 'linux' in sys.platform.lower():
        cmd = [WEAVE_PATH, 'status']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.wait() == 0

    return False


def get_dns_search_list():
    """
    Get's all the configured dns search list from /etc/resolv.conf and appends them to a list.
    Also handles case of multiple "search" lines in /etc/resolv.conf
    :return: A list of dns suffixes.
    """
    dns_search_list = []
    with open('/etc/resolv.conf', 'r') as resolv_file:
        for current_line in resolv_file.readlines():
            if 'search' in current_line:
                for search_path in current_line.split()[1:]:
                    dns_search_list.append(search_path.strip())

    return dns_search_list


class WeaveService(DockerService):

    def __init__(self, container_name: str, service_dir: str):
        super().__init__(container_name, service_dir)
        self._number_of_tries = 0

    @property
    def docker_network(self):
        return WEAVE_NETWORK if 'linux' in sys.platform.lower() and is_weave_up() else AXONIUS_NETWORK

    @abstractmethod
    def is_up(self):
        pass

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
        self._number_of_tries += 1
        if self._number_of_tries > MAX_NUMBER_OF_RUN_TRIES:
            raise Exception(f'Failed to run {self.container_name} after ')
        weave_is_up = is_weave_up()
        extra_flags = extra_flags or []

        if weave_is_up:
            dns_search_list = ['axonius.local']
            dns_search_list.extend(get_dns_search_list())
            extra_flags.extend([f'--dns-search={dns_search_entry}' for dns_search_entry in dns_search_list])

        my_env = os.environ.copy()
        if weave_is_up:
            my_env['DOCKER_HOST'] = 'unix:///var/run/weave/weave.sock'

        try:
            super().start(mode=mode, allow_restart=allow_restart, rebuild=rebuild, hard=hard, show_print=show_print,
                          expose_port=expose_port, extra_flags=extra_flags,
                          docker_internal_env_vars=docker_internal_env_vars, run_env=my_env)
        except subprocess.TimeoutExpired:
            print(
                'Restarting container due TimeoutExpired exception on start (probably due to weave docker run issue.)')
            self.restart(mode=mode, allow_restart=allow_restart, rebuild=rebuild, hard=hard, show_print=show_print,
                         expose_port=expose_port, extra_flags=extra_flags,
                         docker_internal_env_vars=docker_internal_env_vars, run_env=my_env)
        except Exception as exc:
            if 'could not create veth pair' in exc.args[1] or 'error setting up interface' in exc.args[1]:
                print('Restarting container due to weave network exception.')
                self.restart(mode=mode, allow_restart=allow_restart, rebuild=rebuild, hard=hard, show_print=show_print,
                             expose_port=expose_port, extra_flags=extra_flags,
                             docker_internal_env_vars=docker_internal_env_vars, run_env=my_env)
            else:
                raise

    def restart(self,
                mode='',
                allow_restart=False,
                rebuild=False,
                hard=False,
                show_print=True,
                expose_port=False,
                extra_flags=None,
                docker_internal_env_vars=None,
                run_env=None):
        """
        Weave has two bugs that causes us to restart the docker container if they appear:
        1. The docker daemon returns an id on docker run but the docker run process doesn't end (usually
           that container would also not have proper network).
        2. The docker daemon doesn't actually raise the container and we need to run start again.

        Gets the same params as start and calls it with allow_restart true on timeout.
        """
        container_id = self.get_container_id(True)
        if container_id.strip() != '':
            print(f'{COLOR.get("yellow", "<")}Restarting raised container \
            {self.container_name} due to weave false start...'
                  f'{COLOR.get("reset", ">")}')
            command = ['docker', 'restart', container_id[:-1]]

            my_env = os.environ.copy()

            if 'linux' in sys.platform.lower() and is_weave_up():
                my_env['DOCKER_HOST'] = 'unix:///var/run/weave/weave.sock'

            docker_run_process = subprocess.Popen(command, cwd=self.service_dir, stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE,
                                                  env=my_env)

            try:
                all_output = docker_run_process.communicate(timeout=self.run_timeout)
                all_output = ' '.join([current_output_stream.decode('utf-8') for current_output_stream in all_output])
            except subprocess.TimeoutExpired:
                print('Container restart timedout.')
                self.start(mode=mode, allow_restart=True, rebuild=rebuild, hard=hard, show_print=show_print,
                           expose_port=expose_port, extra_flags=extra_flags,
                           docker_internal_env_vars=docker_internal_env_vars, run_env=run_env)
                return

            if docker_run_process.returncode != 0:
                raise Exception(f'Failed to restart container {self.container_name} with id:{container_id}',
                                f'failure output is: {all_output}')
        else:
            print('Container was not started correctly trying again.')
            self.start(mode=mode, allow_restart=allow_restart, rebuild=rebuild, hard=hard, show_print=show_print,
                       expose_port=expose_port, extra_flags=extra_flags,
                       docker_internal_env_vars=docker_internal_env_vars, run_env=my_env)

    @retry(stop_max_attempt_number=5, retry_on_exception=retry_if_timeout, wait_fixed=30)
    def wait_for_service(self, timeout=250):
        if timeout > 3:
            try:
                super().wait_for_service(timeout=5)
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
            print('Restarting container due to wait TimeoutException on wait.')
            self.restart()
            raise
