import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from icinga_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class IcingaConnection(RESTConnection):
    """ rest client for Icinga adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('v1', do_basic_auth=True)

    def get_device_list(self):
        try:
            async_requests = []
            hosts = self._get('v1/objects/hosts', do_basic_auth=True)
            hosts_data = hosts.get('results')
            valid_hosts = []
            for host in hosts_data:
                if host.get('attrs'):
                    host_name = host.get('attrs').get('__name')
                    if host_name:
                        async_requests.append(
                            {'name': 'v1/objects/services', 'url_params': f'match("{host_name}",host.name)',
                             'do_basic_auth': True})
                        valid_hosts.append(host)
            for host, services in zip(valid_hosts, self._async_get(async_requests, consts.DEVICES_POOL_SIZE)):
                if self._is_async_response_good(services):
                    host['services'] = services
                yield host
        except RESTException as e:
            logger.exception(f'Error getting devices from icinga: {e}')
