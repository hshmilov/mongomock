import time

from axonius.clients.rest.connection import RESTConnection


class ShodanConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='shodan', domain='api.shodan.io',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def get_ip_info(self, ip):
        # According to Shodan documentation you can't make more than 1 requrests per second
        time.sleep(1)
        return self._get(f'host/{ip}?key={self._apikey}')

    def get_cidr_info(self, cidr):
        time.sleep(1)
        return self._get(f'host/search?key={self._apikey}&query=net:{cidr}')['matches']

    def _connect(self):
        pass

    def get_device_list(self):
        pass
