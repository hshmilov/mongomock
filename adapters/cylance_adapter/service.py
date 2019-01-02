import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import DEFAULT_MAC_EXTENSIONS, parse_date
from cylance_adapter.connection import CylanceConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CylanceAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        is_safe = Field(str, 'Is Safe')
        device_state = Field(str, 'Device State', enum=['Online', 'Offline'])

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = CylanceConnection(domain=client_config['domain'],
                                           app_id=client_config['app_id'], app_secret=client_config['app_secret'],
                                           tid=client_config['tid'], https_proxy=client_config.get('https_proxy'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Cylance domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Cylance connection

        :return: A json with all the attributes returned from the Cylance Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema CylanceAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cylance Domain',
                    'type': 'string'
                },
                {
                    'name': 'app_id',
                    'title': 'Application Id',
                    'type': 'string'
                },
                {
                    'name': 'app_secret',
                    'title': 'Application Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'tid',
                    'title': 'Tenant API Key',
                    'type': 'string'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'app_id',
                'app_secret',
                'tid'
            ],
            'type': 'array'
        }

    # pylint: disable=R1702,R0912,R0915
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id', '')
                if device_id is None or device_id == '':
                    logger.warning(f'No id of device {device_raw}')
                    continue
                device.id = device_id + (device_raw.get('host_name') or '')
                device.figure_os((device_raw.get('operatingSystem') or '') + ' ' + (device_raw.get('os_version') or ''))
                hostname = device_raw.get('host_name') or ''
                try:
                    # Special condition to OS X
                    device_os = device.os
                    if device_os:
                        if device_os.type == 'OS X':
                            if str(hostname).lower().endswith('.local'):
                                hostname = str(hostname)[:-len('.local')]
                            for default_name in DEFAULT_MAC_EXTENSIONS:
                                if str(hostname).upper().startswith(default_name):
                                    hostname = device_raw.get('name') or ''
                                    break
                except Exception:
                    logger.debug(f'Problem in MAX OS hostname parsing for {device_raw}')
                if len(hostname) > 0:
                    device.hostname = hostname
                try:
                    if hostname and 'workgroup' not in hostname.lower() and 'local' not in hostname.lower():
                        device.domain = '.'.join(hostname.split('.')[1:])
                except Exception:
                    logger.exception(f'Problem getting domain in {device_raw}')
                try:
                    mac_addresses = device_raw.get('mac_addresses')
                    ip_addresses = device_raw.get('ip_addresses')
                    if mac_addresses is None or mac_addresses == []:
                        if ip_addresses is not None and ip_addresses != []:
                            device.add_nic(None, list(ip_addresses))
                    else:
                        for mac_address in mac_addresses:
                            device.add_nic(mac_address, list(ip_addresses))
                except Exception:
                    logger.exception(f'Problem with adding nic to Cylance device {device_raw}')
                device.agent_version = device_raw.get('agent_version', '')
                try:
                    if device_raw.get('date_offline'):
                        device.last_seen = parse_date(str(device_raw.get('date_offline')))
                    elif device_raw.get('state') == 'Online':
                        device.last_seen = datetime.datetime.now()
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                is_safe_raw = device_raw.get('is_safe')
                if is_safe_raw is not None and is_safe_raw != '':
                    device.is_safe = str(is_safe_raw)
                device.last_used_users = str(device_raw.get('last_logged_in_user', '')).split(',')
                device.device_state = str(device_raw.get('state'))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Cylance Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
