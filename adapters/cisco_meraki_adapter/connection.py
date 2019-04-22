import logging

from axonius.clients.rest.connection import RESTConnection, RESTException
from cisco_meraki_adapter.consts import DEVICE_TYPE, MDM_TYPE, CLIENT_TYPE, MDM_FIELDS

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoMerakiConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v0/',
                         headers={'Accept': 'application/json',
                                  'charset': 'utf-8',
                                  'Content-Type': 'application/json',
                                  },
                         **kwargs)
        self._permanent_headers['X-Cisco-Meraki-API-Key'] = self._apikey

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._get('organizations')

    def _get_networks(self, organizations):
        for organization in organizations:
            try:
                if organization:
                    yield from self._get(f'organizations/{organization}/networks')
            except Exception:
                logger.exception(f'Got problem getting networks from org: {organization}')

    def _get_devices(self, networks_raw):
        for network_raw in networks_raw:
            try:
                if network_raw and network_raw.get('id'):
                    devices_network_raw = self._get('networks/' + network_raw.get('id') + '/devices')
                    for device_raw in devices_network_raw:
                        device_raw['network_name'] = network_raw.get('name')
                        yield device_raw
            except Exception:
                logger.exception(f'Problem getting devices in network {network_raw}')

    def _get_devices_and_clients(self, networks_raw):
        devices_raw = self._get_devices(networks_raw)
        for device_raw in devices_raw:
            try:
                yield device_raw, DEVICE_TYPE
                if not device_raw.get('serial'):
                    continue
                serial = device_raw.get('serial')
                clients_device_raw = self._get(f'devices/{serial}/clients?timespan={86400 * 2}')
                for client_raw in clients_device_raw:
                    client_raw['associated_device'] = serial
                    client_raw['name'] = device_raw.get('name')
                    client_raw['address'] = device_raw.get('address')
                    client_raw['network_name'] = device_raw.get('network_name')
                    client_raw['notes'] = device_raw.get('notes')
                    client_raw['tags'] = device_raw.get('tags')
                    yield client_raw, CLIENT_TYPE
            except Exception:
                logger.exception(f'Problem with device {device_raw}')

    def _get_mdm_devices(self, networks_raw):
        for network_raw in networks_raw:
            try:
                if network_raw and network_raw.get('id'):
                    response = self._get('networks/' + network_raw.get('id') + '/sm/devices',
                                         url_params={'fields': MDM_FIELDS})
                    devices_network_raw = response['devices']
                    for device_raw in devices_network_raw:
                        device_raw['network_name'] = network_raw.get('name')
                        yield device_raw, MDM_TYPE
                    while response.get('batchToken'):

                        response = self._get('networks/' + network_raw.get('id') + '/sm/devices',
                                             url_params={'batchToken': response.get('batchToken'),
                                                         'fields': MDM_FIELDS
                                                         })
                        devices_network_raw = response['devices']
                        for device_raw in devices_network_raw:
                            device_raw['network_name'] = network_raw.get('name')
                            yield device_raw, MDM_TYPE
            except Exception:
                logger.exception(f'Problem getting devices in network {network_raw}')

    def get_device_list(self):
        organizations = [str(organization_raw['id']) for organization_raw in self._get('organizations')
                         if organization_raw.get('id')]
        networks_raw = list(self._get_networks(organizations))
        yield from self._get_devices_and_clients(networks_raw)
        yield from self._get_mdm_devices(networks_raw)
