import time
import logging

from axonius.clients.rest.connection import RESTConnection, RESTException
from cisco_meraki_adapter.consts import DEVICE_TYPE, MDM_TYPE, CLIENT_TYPE, MDM_FIELDS, MAX_RATE_LIMIT_TRY


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

    def _meraki_get(self, path, url_params=None):
        for try_ in range(MAX_RATE_LIMIT_TRY):
            response = self._get(path, url_params=url_params,
                                 raise_for_status=False,
                                 return_response_raw=True,
                                 use_json_in_response=False
                                 )
            if response.status_code == 429:
                # Sleeping 2 seconds to be on the safe side
                time.sleep(2)
                continue
            break
        else:
            raise RESTException(f'Failed to fetch path {path} because rate limit')
        return self._handle_response(response)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._meraki_get('organizations')

    def _get_networks(self, organizations):
        for organization in organizations:
            try:
                if organization:
                    yield from self._meraki_get(f'organizations/{organization}/networks')
            except Exception:
                logger.exception(f'Got problem getting networks from org: {organization}')

    def _get_devices(self, networks_raw):
        for network_raw in networks_raw:
            try:
                if network_raw and network_raw.get('id'):
                    devices_network_raw = self._meraki_get('networks/' + network_raw.get('id') + '/devices')
                    for device_raw in devices_network_raw:
                        device_raw['network_name'] = network_raw.get('name')
                        yield device_raw
            except Exception:
                logger.warning(f'Problem getting devices in network {network_raw}', exc_info=True)

    def _get_clients_data_from_networks(self, networks_raw):
        clients_data_dict = dict()
        for network_raw in networks_raw:
            try:
                if network_raw and network_raw.get('id'):
                    clients_network_raw = self._meraki_get('networks/' + network_raw.get('id') +
                                                           f'/clients?timespan={86400 * 2}&perPage=1000')
                    for client_raw in clients_network_raw:
                        clients_data_dict[client_raw.get('id')] = client_raw
                        clients_data_dict[client_raw.get('id')]['network_id'] = network_raw.get('id')
            except Exception:
                logger.warning(f'Problem getting devices in network {network_raw}', exc_info=True)
        return clients_data_dict

    # pylint: disable=too-many-nested-blocks
    def _get_devices_and_clients(self, networks_raw, serial_statuses_dict, fetch_history=False):
        devices_raw = self._get_devices(networks_raw)
        clients_data_dict = self._get_clients_data_from_networks(networks_raw)
        for device_raw in devices_raw:
            try:
                device_status = {}
                if device_raw.get('serial') and serial_statuses_dict.get(device_raw.get('serial')):
                    device_status = serial_statuses_dict.get(device_raw.get('serial'))
                device_raw['device_status'] = device_status
                yield device_raw, DEVICE_TYPE
                if not device_raw.get('serial'):
                    continue
                serial = device_raw.get('serial')
                clients_device_raw = self._meraki_get(f'devices/{serial}/clients?timespan={86400 * 2}')
                logger.debug(f'Len is {len(clients_device_raw)}')
                for ind, client_raw in enumerate(clients_device_raw):
                    logger.debug(f'index is {ind}')
                    if fetch_history:
                        try:
                            client_id = client_raw.get('id')
                            network_id = None
                            if client_id and clients_data_dict.get(client_id):
                                network_id = clients_data_dict.get(client_id).get('network_id')
                            if client_id and network_id:
                                starting = int(time.time()) - 43200
                                client_raw['history_raw'] = self._meraki_get(
                                    f'networks/{network_id}/clients/{client_id}'
                                    f'/trafficHistory?perPage=1000&startingAfter={starting}')
                        except Exception:
                            logger.exception(f'Problem getting history for {client_raw}')
                    client_raw['extra_data'] = clients_data_dict.get(client_raw.get('id'))
                    client_raw['associated_device'] = serial
                    client_raw['name'] = device_raw.get('name')
                    client_raw['address'] = device_raw.get('address')
                    client_raw['network_name'] = device_raw.get('network_name')
                    client_raw['notes'] = device_raw.get('notes')
                    client_raw['tags'] = device_raw.get('tags')
                    client_raw['wan1Ip'] = device_raw.get('wan1Ip')
                    client_raw['wan2Ip'] = device_raw.get('wan2Ip')
                    client_raw['lanIp'] = device_raw.get('lanIp')
                    client_raw['public_ip'] = device_status.get('publicIp')
                    yield client_raw, CLIENT_TYPE
            except Exception:
                logger.exception(f'Problem with device {device_raw}')

    def _get_mdm_devices(self, networks_raw):
        for network_raw in networks_raw:
            try:
                if network_raw and network_raw.get('id'):
                    response = self._meraki_get('networks/' + network_raw.get('id') + '/sm/devices',
                                                url_params={'fields': MDM_FIELDS})
                    devices_network_raw = response['devices']
                    for device_raw in devices_network_raw:
                        device_raw['network_name'] = network_raw.get('name')
                        yield device_raw, MDM_TYPE
                    while response.get('batchToken'):

                        response = self._meraki_get('networks/' + network_raw.get('id') + '/sm/devices',
                                                    url_params={'batchToken': response.get('batchToken'),
                                                                'fields': MDM_FIELDS
                                                                })
                        devices_network_raw = response['devices']
                        for device_raw in devices_network_raw:
                            device_raw['network_name'] = network_raw.get('name')
                            yield device_raw, MDM_TYPE
            except Exception:
                logger.warning(f'Problem getting devices in network {network_raw}', exc_info=True)

    def _get_device_statuses(self, organizations):
        serial_statuses_dict = dict()
        for organization in organizations:
            try:
                device_statuses = self._meraki_get(f'organizations/{organization}/deviceStatuses')
                for device_status in device_statuses:
                    if isinstance(device_status, dict) and device_status.get('serial'):
                        serial_statuses_dict[device_status.get('serial')] = device_status
            except Exception:
                logger.exception(f'Problem with organization {organization}')
        return serial_statuses_dict

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_history=False):
        organizations = [str(organization_raw['id']) for organization_raw in self._meraki_get('organizations')
                         if organization_raw.get('id')]
        serial_statuses_dict = self._get_device_statuses(organizations)
        networks_raw = list(self._get_networks(organizations))
        yield from self._get_devices_and_clients(networks_raw, serial_statuses_dict, fetch_history)
        yield from self._get_mdm_devices(networks_raw)
