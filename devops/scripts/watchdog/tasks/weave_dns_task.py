import subprocess
import time
import re
from typing import List, Tuple

import docker
from SE.se import AXONIUS_SH
from axonius.consts.system_consts import WEAVE_PATH, AXONIUS_DNS_SUFFIX
from scripts.watchdog.watchdog_task import WatchdogTask
from services.axonius_service import AxoniusService
from services.weave_service import is_weave_up

SLEEP_SECONDS = 60
CORTEX_CWD = '/home/ubuntu/cortex'
SCRIPT_TIMEOUT = 60
WEAVE_IP_REGEX = r'(.*)/\d+'


class WeaveDNSTask(WatchdogTask):

    def run(self):
        while True:
            if is_weave_up():
                self.check_weave_dns_status()
            time.sleep(SLEEP_SECONDS)

    def get_weave_containers(self) -> List[Tuple]:
        """
        return a list of docker containers with a weave interface
        """
        try:
            weave_containers_output = self.exec_command_wrapper([WEAVE_PATH, 'ps'])
            if not weave_containers_output:
                return []
        except Exception as e:
            self.report_error(f'Error listing weave containers: {e}')
            return []
        weave_containers = []
        weave_containers_output = weave_containers_output.split('\n')[1:]
        for line in weave_containers_output:
            if not line:
                continue
            try:
                container_id, container_mac, container_ip = line.split()
                container_ip_res = re.search(WEAVE_IP_REGEX, container_ip)
                container_ip = container_ip_res.group(1) if container_ip_res else None
                weave_containers.append((container_id, container_mac, container_ip))
            except Exception:
                self.report_error(f'Error parsing weave ps line: {line}')
        return weave_containers

    def check_weave_dns_status(self):
        """
        Fix docker containers with weave interface and no dns record
        """
        try:
            weave_containers = self.get_weave_containers()
            all_mappings = self.map_short_name_to_adapter_or_plugin_name()
            with docker.APIClient() as client:
                for container_id, container_mac, container_ip in weave_containers:
                    try:
                        if self.check_name_registered_in_weave(container_id):
                            continue
                        fixed = self.fix_container_dns(client=client,
                                                       container_id=container_id,
                                                       container_ip=container_ip,
                                                       all_mappings=all_mappings)
                        if fixed:
                            self.report_info(f'Weave DNS record for {container_id} was fixed')
                    except Exception as e:
                        self.report_error(f'Error while registering dns for {container_id} - {str(e)}')
        except Exception as e:
            self.report_error(f'Error while checking weave dns status: {e}')

    # pylint: disable=W0212
    def fix_container_dns(self, client: docker.APIClient,
                          container_id: str, container_ip: str, all_mappings: dict) -> bool:
        """
        Fix docker container with weave interface and no dns record by the following steps:
        1. re register the plugin
        2. manually add dns record using weave dns-add
        3. restart the docker container
        :return: True on success
        """
        dns_registered = False
        plugin_name = client.containers(filters={'id': container_id})
        if not plugin_name:
            return False
        plugin_name = plugin_name[0]['Names'][0][1:]
        self.report_info(f'Fixing weave DNS record for {container_id}:{plugin_name}')

        # 1. re register the plugin
        try:
            service = AxoniusService()
            short_plugin_name = all_mappings[plugin_name] if plugin_name in all_mappings else \
                service._get_docker_service('plugins', plugin_name.replace('-', '_')).container_name

            self.report_info(f'Re registering {container_id}:{plugin_name}')
            dns_registered = self.re_register_container(container_id, plugin_name, short_plugin_name)
            if dns_registered:
                return True
        except Exception as e:
            self.report_error(f'Error while re registering {container_id}:{plugin_name} - {e}')

        # if register didnt work (sometimes happens with core services such as
        # mongo, master-proxy, etc) we try to add the dns manually
        # 2. manually add dns record using weave dns-add
        try:
            if container_ip:
                self.report_info(f'Manually adding dns record for {container_id}:{plugin_name}')
                dns_registered = self.add_weave_dns(container_id, container_ip, plugin_name)
                if dns_registered:
                    return True
        except Exception as e:
            self.report_error(f'Error adding dns record to {container_id}:{plugin_name} - {e}')

        # This should almost never happen, as last resort we restart the service...
        # 3. restart the docker container
        self.report_error(
            f'Couldn\'t set dns record to {short_plugin_name} - {container_id}')
        self.report_error(f'Restarting {short_plugin_name}')
        try:
            dns_registered = self.restart_container(container_id, plugin_name, short_plugin_name)
        except Exception as e:
            self.report_error(f'Error while restarting {container_id}:{plugin_name} - {e}')
        return dns_registered

    def check_name_registered_in_weave(self, container_id: str) -> bool:
        """
        check if the container is registered on weave dns
        :param container_id: container id to check
        :return: True if registered
        """
        command_output = self.exec_command_wrapper([WEAVE_PATH, 'status', 'dns'])
        for weave_record in command_output.strip().split('\n'):
            if container_id in weave_record:
                return True
        return False

    def re_register_container(self, container_id: str, plugin_name: str, short_plugin_name: str) -> bool:
        """
        Re register container plugin
        :return: True on success
        """
        # Weave is stupid and sometimes new a few tries until successful register
        for try_num in range(3):
            self.exec_command_wrapper([
                AXONIUS_SH,
                'adapter' if 'adapter' in plugin_name else 'service',
                short_plugin_name.replace('-', '_'),
                'register'
            ])
            if self.check_name_registered_in_weave(container_id):
                return True
        return False

    def add_weave_dns(self, container_id: str, container_ip: str, plugin_name: str):
        """
        Manually add dns record to weave dns
        :return:
        """
        output = self.exec_command_wrapper([WEAVE_PATH,
                                            'dns-add',
                                            container_ip,
                                            container_id,
                                            '-h',
                                            plugin_name + '.' + AXONIUS_DNS_SUFFIX])
        if output != '' or not self.check_name_registered_in_weave(container_id):
            return False
        return True

    def restart_container(self, container_id: str, plugin_name: str, short_plugin_name: str):
        """
        Restart the docker container
        """
        self.exec_command_wrapper([AXONIUS_SH,
                                   'adapter' if 'adapter' in plugin_name else 'service',
                                   short_plugin_name.replace('-', '_'),
                                   'up',
                                   '--restart'
                                   ])
        if not self.check_name_registered_in_weave(container_id):
            return False
        return True

    @staticmethod
    def map_short_name_to_adapter_or_plugin_name():
        service = AxoniusService()
        return {x[1]().container_name: x[0] for x in service.get_all_adapters() + service.get_all_plugins()
                + service.get_all_standalone_services()}

    @staticmethod
    def exec_command_wrapper(command: List[str], cmd_timeout: int = SCRIPT_TIMEOUT, **kwargs):
        # Running the command.
        subprocess_handle = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=CORTEX_CWD,
                                             **kwargs)

        # Checking if return code is zero, if not, it will raise an exception
        try:
            command_stdout, command_stderr = subprocess_handle.communicate(
                timeout=cmd_timeout)
        except subprocess.TimeoutExpired:
            # The child process is not killed if the timeout expires, so in order to cleanup properly a well-behaved
            # application should kill the child process and finish communication (from python documentation)
            subprocess_handle.kill()
            command_stdout, command_stderr = subprocess_handle.communicate()
            command_stdout = command_stdout.decode('utf-8')
            command_stderr = command_stderr.decode('utf-8')
            raise Exception(f'Execution timeout! output: {command_stdout}, \nstderr: {command_stderr}')

        except Exception as e:
            raise Exception(f'Generic error: {str(e)}')

        if subprocess_handle.returncode != 0:
            raise Exception(f'Error - Return code is {subprocess_handle.returncode}\n'
                            f'stdout: {command_stdout}\nstderr: {command_stderr}')

        return command_stdout.decode('utf-8') + command_stderr.decode('utf-8')


# pylint: disable=C0103
if __name__ == '__main__':
    gw = WeaveDNSTask()
    gw.start()
