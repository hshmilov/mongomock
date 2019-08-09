import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from paloalto_cortex_adapter import consts
from paloalto_cortex_adapter.connection import PaloAltoCortexConnection
from paloalto_cortex_adapter.client_id import get_client_id
from paloalto_cortex_adapter.consts import CLOUD_URL, DEFAULT_NUMBER_OF_WEEKS_AGO_TO_FETCH

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-instance-attributes, superfluous-parens
class PaloaltoCortexAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        pan_source = Field(str, 'Source', enum=[dt.value for dt in consts.DeviceType])
        agent_id = Field(str, 'Agent ID')
        customer_id = Field(str, 'Customer ID')
        traps_id = Field(str, 'Traps ID')
        protection_status = Field(bool, 'Protection Status')
        policy_tag = Field(str, 'Policy Tag')
        is_vdi = Field(bool, 'Is VDI')

    def __init__(self, *args, **kwargs):
        super().__init__(
            config_file_path=get_local_config_file(__file__), *args, **kwargs
        )

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(CLOUD_URL)

    @staticmethod
    def get_connection(client_config):
        connection = PaloAltoCortexConnection(
            apikey=client_config['apikey'],
            https_proxy=client_config.get('https_proxy'),
        )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = f'Error connecting to client, reason: {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(self.__weeks_ago_to_fetch)

    @staticmethod
    def _clients_schema():
        """
        The schema PaloaltoCortex expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'apikey',
            ],
            'type': 'array'
        }

    def _create_traps_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('agentId')
            endpoint_header = device_raw.get('endPointHeader') or {}
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (endpoint_header.get('deviceName') or '')
            device.pan_source = consts.DeviceType.Traps.value
            device.agent_id = device_raw.get('agentId')
            device.customer_id = device_raw.get('customerId')
            device.traps_id = device_raw.get('trapsId')
            device.last_seen = parse_date(device_raw.get('generatedTime'))

            # Endpoint header fields
            device.hostname = endpoint_header.get('deviceName')
            device.domain = endpoint_header.get('deviceDomain')
            agent_ip = endpoint_header.get('agentIp')
            if not isinstance(agent_ip, list):
                agent_ip = [agent_ip]
            device.add_nic(ips=agent_ip)
            device.add_agent_version(agent=AGENT_NAMES.paloalto_cortex, version=endpoint_header.get('agentVersion'))
            device.policy_tag = endpoint_header.get('policyTag')
            device.protection_status = not (endpoint_header.get('protectionStatus') == 0)
            device_os_type = {
                1: 'Windows',
                2: 'OSX',
                3: 'Android',
                4: 'Linux'
            }.get(endpoint_header.get('osType'))

            device.figure_os((device_os_type or '') + ' ' + (endpoint_header.get('osVersion') or ''))
            device.os.bitness = 64 if endpoint_header.get('is64') == 1 else 32
            device.is_vdi = not (endpoint_header.get('isVdi') == 0)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Paloalto Cortex Traps Device for {device_raw}')
            return None

    def _create_global_protect_device(self, device_raw: dict):
        try:
            device = self._new_device_adapter()
            device.pan_source = consts.DeviceType.GlobalProtect.value
            machine_name = device_raw.get('machinename')
            if not machine_name:
                logger.error(f'Error - no machien name in GlobalProtect agent: {device_raw}')
                return None
            device.id = f'global_protect_{machine_name}'
            device.hostname = machine_name
            for interface in (device_raw.get('interfaces') or []):
                try:
                    mac = interface.get('mac')
                    ips = []
                    if interface.get('ip'):
                        ips.append(interface.get('ip'))
                    if interface.get('ip6'):
                        ips.append(interface.get('ip6'))

                    device.add_nic(mac=mac, ips=ips)
                except Exception:
                    logger.exception(f'Failed adding interface {str(interface)}')
            src_user = device_raw.get('srcuser')
            if src_user:
                device.last_used_users.append(src_user)
            device.customer_id = device_raw.get('customer-id')
            device.figure_os(device_raw.get('os'))

            # NOTICE! 'serial' is not the serial of the device. Its the serial of the firewall!
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Paloalto Cortex Global Protect Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:

            device = None
            if device_type == consts.DeviceType.Traps:
                device = self._create_traps_device(device_raw)
            elif device_type == consts.DeviceType.GlobalProtect:
                device = self._create_global_protect_device(device_raw)
            else:
                logger.error(f'Error - got unknown device type')

            if device:
                yield device

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'weeks_ago_to_fetch',
                    'title': 'Number of weeks ago to fetch',
                    'type': 'integer'
                }
            ],
            'required': [],
            'pretty_name': 'Palo Alto Networks Cortex Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'weeks_ago_to_fetch': DEFAULT_NUMBER_OF_WEEKS_AGO_TO_FETCH
        }

    def _on_config_update(self, config):
        self.__weeks_ago_to_fetch = config.get('weeks_ago_to_fetch') or DEFAULT_NUMBER_OF_WEEKS_AGO_TO_FETCH

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]  # Traps
