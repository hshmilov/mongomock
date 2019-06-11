import time

from json.decoder import JSONDecodeError

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.shodan.consts import DEFAULT_DOMAIN


class ShodanConnection(RESTConnection):
    def __init__(self, *args, domain_prefered=DEFAULT_DOMAIN, **kwargs):
        super().__init__(*args, url_base_prefix='shodan', domain=domain_prefered,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def get_ip_info(self, ip):
        # According to Shodan documentation you can't make more than 1 requrests per second
        time.sleep(1)
        return self._get(f'host/{ip}?key={self._apikey}')

    def get_ip_info2(self, ip):
        time.sleep(1)
        response = self._get(f'host/{ip}?key={self._apikey}',
                             raise_for_status=False,
                             use_json_in_response=False,
                             return_response_raw=True)
        if response.status_code != 200:
            try:
                if 'error' in response.json():
                    return response.json()
            except JSONDecodeError as e:
                pass
        return self._handle_response(response)

    def get_cidr_info(self, cidr):
        time.sleep(1)
        return self._get(f'host/search?key={self._apikey}&query=net:{cidr}')['matches']

    def _connect(self):
        pass

    def get_device_list(self):
        pass
