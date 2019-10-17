
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from carbonblack_protection_adapter.connection import \
    CarbonblackProtectionConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackProtectionAdapter(AdapterBase, Configurable):

    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        connected = Field(bool, 'Connected')
        policy_name = Field(str, 'Policy Name')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['CarbonblackProtection_Domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('CarbonblackProtection_Domain'))

    def _connect_client(self, client_config):
        try:
            connection = CarbonblackProtectionConnection(
                domain=client_config['CarbonblackProtection_Domain'],
                verify_ssl=client_config['verify_ssl'], https_proxy=client_config.get('https_proxy'),
                apikey=client_config['apikey'], devices_per_page=self.__devices_per_page)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['CarbonblackProtection_Domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message[:300])

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific CarbonblackProtection domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a CarbonblackProtection connection

        :return: A json with all the attributes returned from the CarbonblackProtection Server
        """
        with client_data:
            yield from client_data.get_device_list(devices_per_page=self.__devices_per_page)

    def _clients_schema(self):
        """
        The schema CarbonblackProtectionAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'CarbonblackProtection_Domain',
                    'title': 'Carbon Black CB Protection Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'Https Proxy',
                    'type': 'string'
                }

            ],
            'required': [
                'CarbonblackProtection_Domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                uninstall = device_raw.get('uninstalled') or False
                if uninstall is True and not self.__fetch_uninstall:
                    continue
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Device with bad ID {device_id}')
                    continue
                hostname = device_raw.get('name')
                device.id = str(device_id) + (hostname or '')
                if hostname and '\\' in hostname:
                    split_hostname = hostname.split('\\')
                    device.hostname = split_hostname[1]
                    device.domain = split_hostname[0]
                    device.part_of_domain = True
                else:
                    device.hostname = hostname
                device.description = device_raw.get('description')
                device.figure_os((device_raw.get('osShortName') or '') + ' ' + (device_raw.get('osName') or ''))
                try:
                    ips = None
                    mac = device_raw.get('macAddress')
                    if not mac or mac == 'Unknown':
                        mac = None
                    if device_raw.get('ipAddress') and isinstance(device_raw.get('ipAddress'), str):
                        ips = device_raw.get('ipAddress').split(',')
                    if ips or mac:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception('Problem with adding nic to CarbonblackProtection device')
                try:
                    device.last_seen = parse_date(str(device_raw.get('lastPollDate')))
                except Exception:
                    logger.exception('Problem getting Last seen in CarbonBlackProtection')
                device.add_agent_version(agent=AGENT_NAMES.carbonblack_protection,
                                         version=device_raw.get('agentVersion'))
                device.policy_name = device_raw.get('policyName')
                device.last_used_users = str(device_raw.get('users') or '').split(',')
                device.connected = device_raw.get('connected')
                total_physical_memory = device_raw.get('memorySize')
                if total_physical_memory is not None:
                    device.total_physical_memory = int(total_physical_memory) / 1024.0
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception('Problem with fetching CarbonblackProtection Device')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_uninstall',
                    'title': 'Fetch Uninstall Devices',
                    'type': 'bool'
                },
                {
                    'name': 'devices_per_page',
                    'title': 'Fetch Devices Per Page',
                    'type': 'integer'
                }
            ],
            'required': [
                'fetch_uninstall',
                'devices_per_page'
            ],
            'pretty_name': 'Carbon Black CB Protection Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_uninstall': True,
            'devices_per_page': 10
        }

    def _on_config_update(self, config):
        self.__fetch_uninstall = config['fetch_uninstall']
        self.__devices_per_page = config['devices_per_page']
