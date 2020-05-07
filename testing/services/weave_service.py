import os
import shlex
import subprocess
import sys
import time
from abc import abstractmethod

import requests
from retrying import retry

from axonius.consts.system_consts import (AXONIUS_DNS_SUFFIX, AXONIUS_NETWORK,
                                          WEAVE_NETWORK, WEAVE_PATH, USING_WEAVE_PATH)
from axonius.consts.plugin_consts import UWSGI_RECOVER_SCRIPT_PATH
from axonius.utils.debug import COLOR
from services.axon_service import TimeoutException
from services.docker_service import DockerService, retry_if_timeout

MAX_NUMBER_OF_RUN_TRIES = 10
RETRY_SLEEP_TIME = 30
WEAVE_API_URL = 'http://127.0.0.1:6784'


def is_weave_up():
    """
    Executes "Weave status" (if we're running on a linux machine) and checks that weave is up.
    :return: bool that signifies if weave is up.
    """
    # This takes a second but is called multiple times when we raise the system, so we have to cache it.
    if 'linux' in sys.platform.lower():
        cmd = [WEAVE_PATH, 'status']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.wait() == 0

    return False


def is_using_weave():
    return USING_WEAVE_PATH.is_file()


def get_dns_search_list():
    """
    Gets all the configured dns search list from /etc/resolv.conf and appends them to a list.
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
        self.tried_signal_uwsgi = False

    @property
    def docker_network(self):
        return WEAVE_NETWORK if is_using_weave() and 'linux' in sys.platform.lower() and is_weave_up() \
            else AXONIUS_NETWORK

    @abstractmethod
    def is_up(self, *args, **kwargs):
        pass

    def is_unique_dns_registered(self):
        weave_dns_lookup_command = shlex.split(f'weave dns-lookup {self.fqdn}')
        dns_lookup_result = subprocess.check_output(weave_dns_lookup_command)
        return len(dns_lookup_result) > 0

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
        if self._number_of_tries > 2:
            time.sleep(RETRY_SLEEP_TIME)
        if self._number_of_tries > MAX_NUMBER_OF_RUN_TRIES:
            raise Exception(f'Failed to run {self.container_name} after ')

        extra_flags = extra_flags or []
        dns_search_list = [AXONIUS_DNS_SUFFIX]

        if 'linux' in sys.platform.lower():
            dns_search_list.extend(get_dns_search_list())
            extra_flags.extend([f'--dns-search={dns_search_entry}' for dns_search_entry in dns_search_list])

        my_env = os.environ.copy()
        if is_using_weave() and is_weave_up():
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
            if len(exc.args) >= 2 and \
                    ('could not create veth pair' in exc.args[1] or 'error setting up interface' in exc.args[1]):
                print(f'Restarting container due to weave network exception: {exc}')
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

            if 'linux' in sys.platform.lower() and is_using_weave() and is_weave_up():
                my_env['DOCKER_HOST'] = 'unix:///var/run/weave/weave.sock'

            docker_run_process = subprocess.Popen(command, cwd=self.service_dir, stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE,
                                                  env=my_env)

            try:
                all_output = docker_run_process.communicate(timeout=self.run_timeout)
                all_output = ' '.join([current_output_stream.decode('utf-8') for current_output_stream in all_output])
            except subprocess.TimeoutExpired:
                print('Container restart timedout.')
                self.start(mode=mode, allow_restart=True, rebuild=True, hard=hard, show_print=show_print,
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
                       docker_internal_env_vars=docker_internal_env_vars, run_env=run_env)

    @retry(stop_max_attempt_number=5, retry_on_exception=retry_if_timeout, wait_fixed=30)
    def wait_for_service(self, timeout=250):
        if timeout > 3:
            try:
                super().wait_for_service(timeout=5)
                self.tried_signal_uwsgi = False
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
            self.tried_signal_uwsgi = False
        except TimeoutException:
            # Sometimes uwsgi hangs at system startup, signaling it solves the problem
            # https://github.com/enowars/enochecker/pull/22
            if not self.tried_signal_uwsgi:
                print('Signaling uwsgi to wakeup!!!')
                super().run_command_in_container(f'python3 {UWSGI_RECOVER_SCRIPT_PATH}')
                self.tried_signal_uwsgi = True
            else:
                print('Restarting container due to wait TimeoutException on wait.')
                self.restart()
            raise

    def add_weave_dns_entry(self):
        """
        Add dns entry to weave network
        :return:
        """
        # Remove old dns entry from weave
        dns_remove_command = shlex.split(f'{WEAVE_PATH} dns-remove {self.id}')
        subprocess.check_call(dns_remove_command)

        # Check that we have removed the dns entries. If we still have a dns entry associated with that hostname,
        # it must be an old dead container. see:
        # * https://github.com/weaveworks/weave/issues/3432
        # * https://axonius.atlassian.net/browse/AX-4731
        dns_check_command = shlex.split(f'{WEAVE_PATH} dns-lookup {self.fqdn}')
        response = subprocess.check_output(dns_check_command).strip().decode('utf-8')

        if response:
            # We should not have any other ip associated with this hostname. Lets remove it.
            for ip in response.splitlines():
                print(f'Found stale weave-dns record: {self.fqdn} -> {ip}. Removing')
                for _ in range(3):
                    # Try 3 times, because weave is not always working
                    requests.delete(f'{WEAVE_API_URL}/name/*/{ip.strip()}?fqdn={self.fqdn}')
                    # We do not raise for status or fail, as this is too risky.

        # Add new unique dns entry to weave
        dns_add_command = shlex.split(
            f'{WEAVE_PATH} dns-add {self.id} -h {self.fqdn}')

        subprocess.check_call(dns_add_command)

        dns_check_command = shlex.split(f'{WEAVE_PATH} dns-lookup {self.fqdn}')
        response = subprocess.check_output(dns_check_command).strip()
        if not response:
            print(f'Error looking up dns {self.fqdn}. Retrying...', file=sys.stderr)
            raise ValueError(f'Error looking up dns {self.fqdn} after registration.')

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def connect_to_weave_network(self):
        """
        Connect existing docker to weave network by running weave attach
        :return:
        """
        if not is_weave_up():
            raise Exception(f'Weave is down')
        weave_attach_command = shlex.split(f'{WEAVE_PATH} attach {self.id}')
        subprocess.check_call(weave_attach_command)
        self.add_weave_dns_entry()
