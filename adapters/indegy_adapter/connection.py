import asyncio
import logging

from functools import partial
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.files import create_temp_file
from axonius.utils.json import from_json
from indegy_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class IndegyConnection(RESTConnection):
    """
    rest client for Indegy adapter

    Getting device data chain:
    1. query all indegy assets, endpoint:   /assets
    2. query each device interfaces, endpoint:  /assets/<asset_id>/connections
    3. query data for each interface, endpoint: /networkinterfaces/<interface_id>

    Using asyncio and aiohttp for getting devices quickly
    """

    def __init__(self, *args, cert_file, private_key, port, **kwargs):
        super().__init__(*args, url_base_prefix='v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         port=port,
                         **kwargs)

        self._cert_file = create_temp_file(cert_file)
        self._private_key_file = create_temp_file(private_key)

    def _connect(self):
        if self.add_ssl_cert(self._cert_file.name, self._private_key_file.name):
            response = self._get('robots')
        else:
            err = 'Private and public keys are not associated'
            logger.error(err)
            raise Exception(err)

    async def fill_interface_data(self, interface, session):
        """
        Get network interface data - (mac and ips)
        """
        if not interface.get('networkInterface'):
            return
        try:
            interface_data, response = await self._do_single_async_request('GET',
                                                                           {'name': 'networkinterfaces/{}'.format(
                                                                               interface.get('networkInterface'))},
                                                                           session)
            if interface_data:
                interface['interface_data'] = from_json(interface_data)
        except Exception:
            logger.exception(f'Error getting interface data for interface: %s', interface.get('networkInterface'))

    async def get_device_interfaces(self, text, response, session, device):
        """
        Get network interfaces for the given device
        """
        if response.status != 200 or not text:
            return None
        try:
            interfaces = from_json(text)
            await asyncio.gather(*[self.fill_interface_data(interface, session) for interface in interfaces])
            device['interfaces'] = interfaces
        except Exception:
            logger.exception(f'Error getting device interfaces. device: %s', device.get('id'))

    def get_device_list(self):
        assets = self._get('assets')
        async_requests = []
        for dev in assets:
            # A wrapper function for calling get_device_interfaces with device dict
            callback = partial(self.get_device_interfaces, device=dev)
            if dev.get('id') is None:
                logger.error(f'Error! got device with no id {dev}')
                continue
            async_requests.append({'name': 'assets/{}/connections'.format(dev.get('id')), 'callback': callback})
        for device, device_connections in zip(assets, self._async_get(async_requests, consts.DEVICES_POOL_SIZE)):
            if not self._is_async_response_good(device_connections):
                logger.error('Problem getting device interfaces, device id: %s, error: %s', device.get('id'),
                             device_connections)
            yield device
