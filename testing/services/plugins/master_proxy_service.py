import json
import os
from pathlib import Path

import requests
from urllib3 import ProxyManager

from axonius.consts import plugin_consts
from axonius.consts.system_consts import NODE_MARKER_PATH
from scripts.instances.instances_consts import (AXONIUS_SETTINGS_HOST_PATH,
                                                PROXY_DATA_HOST_PATH)
from services.ports import DOCKER_PORTS
from services.weave_service import WeaveService

CONTAINER_NAME = 'master-proxy'
CONF_TEMPLATE_FILE = Path('tinyproxy.conf.in')
CONF_FILE = Path('tinyproxy.conf')
MASTER_PROXY_LOGFILE = 'master-proxy.rawtext.log'

CREDS = 'creds'
VERIFY = 'verify'


def read_proxy_data():
    try:
        port = DOCKER_PORTS['master-proxy']
        if NODE_MARKER_PATH.is_file():
            print('running on node, work with master-proxy')
            return {CREDS: f'localhost:{port}', VERIFY: False}

        proxy_data_file = PROXY_DATA_HOST_PATH
        if proxy_data_file.is_file():
            proxy_data = proxy_data_file.read_text().strip()
            as_dict = json.loads(proxy_data)
            proxy_creds = as_dict.get(CREDS, '')
            print(f'Got proxy line={proxy_creds}')

            # invoking this one only to validate that the proxy string format is a valid proxy string
            ProxyManager(f'http://{proxy_creds}')
            return as_dict

        print(f'no proxy data found in {proxy_data_file}')
        return None

    except Exception as e:
        print(f'Failed to process proxy line {e}')
        return None


class MasterProxyService(WeaveService):

    def start(self, *args, **kwargs):  # pylint: disable=arguments-differ
        if NODE_MARKER_PATH.is_file():
            print(f'master-proxy should not run on node')
        else:
            # process template
            template = (Path(self.service_dir) / CONF_TEMPLATE_FILE).read_text()
            os.makedirs(self.log_dir, exist_ok=True)
            (Path(self.log_dir) / MASTER_PROXY_LOGFILE).touch(exist_ok=True)
            proxy_data = read_proxy_data()
            if proxy_data and proxy_data.get(CREDS):
                proxy = proxy_data[CREDS]
                template += f'\nupstream {proxy}\n'

            template += f'\nLogFile "/home/axonius/logs/{MASTER_PROXY_LOGFILE}"\n'
            (Path(self.service_dir) / CONF_FILE).write_text(template)

            super().start(*args, **kwargs)

    def is_up(self):
        try:
            response = requests.get('https://manage.chef.io',
                                    proxies={'https': f'https://127.0.0.1:{self.port()}'},
                                    timeout=(10, 60))
            if response.status_code == 200:
                print(f'proxy started ok')
                return True
            print(f'ERROR - failed to start {CONTAINER_NAME} - {response}')
        except Exception as e:
            print(f'ERROR - failed to start proxy - {e}')

        # can't let system startup fail in offline installations!
        return True

    def __init__(self):
        super().__init__(CONTAINER_NAME, service_dir='services/plugins/master_proxy')

    @staticmethod
    def port():
        return DOCKER_PORTS[CONTAINER_NAME]

    @property
    def exposed_ports(self):
        return [(self.port(), self.port())]

    @property
    def volumes_override(self):

        return [f'{self.service_dir}/{CONF_FILE}:/etc/tinyproxy/tinyproxy.conf',
                f'{AXONIUS_SETTINGS_HOST_PATH}:{plugin_consts.AXONIUS_SETTINGS_PATH}']

    def get_main_file(self):
        return ''

    def get_uwsgi_file(self):
        return ''

    @property
    def _additional_parameters(self):
        return ['ANY']
