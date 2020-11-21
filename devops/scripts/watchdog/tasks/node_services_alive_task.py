import time
from pathlib import Path

import urllib3
import docker
import requests

from axonius.consts.plugin_consts import MASTER_PROXY_PLUGIN_NAME
from axonius.consts.system_consts import NODE_MARKER_PATH
from axonius.utils.host_utils import check_installer_locks
from scripts.watchdog.watchdog_task import WatchdogTask
from services.ports import DOCKER_PORTS
from services.standalone_services.node_proxy_service import NodeProxyService
from services.standalone_services.tunneler_service import TunnelerService

SLEEP_SECONDS = 60 * 1
URL_TO_CHECK = 'https://manage.chef.io'


def check_url():
    port = DOCKER_PORTS[MASTER_PROXY_PLUGIN_NAME]
    proxies = {'https': f'https://master-proxy.axonius.local:{port}'}
    response = requests.get(URL_TO_CHECK, verify=False, timeout=(10, 20), proxies=proxies)
    return response


def get_container_status(service):
    client = docker.from_env()
    service_container = client.containers.get(service.name)

    return service_container.status if service_container else None


def start_service(service, *args, **kwargs):
    service.take_process_ownership()
    service.start(*args, **kwargs)
    service.start(*args, **kwargs)


class NodeServicesAliveTask(WatchdogTask):
    def __init__(self, tunneler_service, proxy_service):
        super().__init__()
        self.tunneler_service = tunneler_service
        self.proxy_service = proxy_service

    def _restart_proxy_if_needed(self):
        try:
            try:
                url_check_result = check_url()
                if url_check_result.status_code != 200:
                    self.report_error(f'bad status code {url_check_result}')
                    raise Exception('status code')
                self.report_info(f'{self.proxy_service.name} is working on node')
            except Exception as ex:
                self.report_error(f'restarting the {self.proxy_service.name} because of {ex}')
                start_service(self.proxy_service, mode='prod', allow_restart=True, show_print=False)
                self.report_info(f'{self.proxy_service.name} restarted successfully.')
        except Exception as ex:
            self.report_error(f'restarting the {self.proxy_service.name} failed because of {ex}')

    def _restart_tunneler_if_needed(self):
        try:
            ssh_status = self.tunneler_service.check_ssh()
            if 'Permission denied, please try again.' not in ssh_status.output.decode('utf-8'):
                self.report_error(f'bad ssh status ssh is down')
                raise Exception(f'ssh is down {ssh_status}  ')
            self.report_info(f'{self.tunneler_service.name} is working on node')
        except Exception as ex:
            self.report_error(f'restarting the {self.tunneler_service.name} because of {ex}')
            start_service(self.tunneler_service, mode='prod', allow_restart=True, show_print=False)
            self.report_info(f'{self.tunneler_service.name} restarted successfully.')

    def run(self):
        urllib3.disable_warnings()

        while True:
            try:
                time.sleep(SLEEP_SECONDS)

                if NODE_MARKER_PATH.is_file():
                    if check_installer_locks():
                        self.report_info('system upgrade / restore is in progress...')
                        continue

                    self.report_info(f'node flow')
                    self._restart_proxy_if_needed()
                    self._restart_tunneler_if_needed()
                else:
                    self.report_info(f'master flow')
            except Exception as e:
                self.report_error(f'error in watchdog {e}')


def main():
    node_services_alive_watchdog = NodeServicesAliveTask(TunnelerService(), NodeProxyService())
    node_services_alive_watchdog.start()


if __name__ == '__main__':
    main()
