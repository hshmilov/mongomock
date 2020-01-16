import time
import requests
import urllib3
import docker

from axonius.consts.system_consts import NODE_MARKER_PATH
from scripts.instances.network_utils import run_proxy_socat
from scripts.watchdog.watchdog_task import WatchdogTask
from services.ports import DOCKER_PORTS

SLEEP_SECONDS = 60 * 5
URL_TO_CHECK = 'https://manage.chef.io'


class SocatAliveTask(WatchdogTask):
    def run(self):

        urllib3.disable_warnings()

        while True:
            try:
                if NODE_MARKER_PATH.is_file():
                    try:
                        self.report_info(f'node flow')
                        port = DOCKER_PORTS['master-proxy']
                        proxies = {'https': f'https://localhost:{port}'}
                        response = requests.get(URL_TO_CHECK, verify=False, timeout=(10, 20), proxies=proxies)
                        if response.status_code != 200:
                            self.report_error(f'bad status code {response}')
                            raise Exception('status code')
                        self.report_error(f'socat-proxy is working on node')
                    except Exception as e:
                        self.report_error(f'restarting the proxy-socat because of {e}')
                        environment = {'DOCKER_HOST': 'unix:///var/run/weave/weave.sock'}
                        client = docker.from_env(environment=environment)
                        names = [x.name for x in client.containers.list()]
                        if 'proxy-socat' in names:
                            socat = client.containers.get('proxy-socat')
                            socat.restart()
                        else:
                            run_proxy_socat()
                else:
                    self.report_info(f'master flow')

                time.sleep(SLEEP_SECONDS)
            except Exception as e:
                self.report_error(f'error in watchdog {e}')


if __name__ == '__main__':
    gw = SocatAliveTask()
    gw.start()
