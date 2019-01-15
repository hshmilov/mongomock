from axonius.clients.rest.connection import RESTConnection


class ShodanConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='shodan', domain='api.shodan.io',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def get_ip_info(self, ip):
        return self._get(f'host/{ip}?key={self._apikey}')

    def _connect(self):
        pass

    def get_device_list(self):
        pass
