# pylint: disable=import-error
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from paloalto_cortex_adapter.connection import PaloAltoCortexConnection
from paloalto_cortex_adapter.client_id import get_client_id
from paloalto_cortex_adapter.consts import CLOUD_URL, DEFAULT_NUMBER_OF_WEEKS_AGO_TO_FETCH
from paloalto_cortex_adapter.structures import GlobalProtectDevice

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


# pylint: disable=too-many-instance-attributes, superfluous-parens
class PaloaltoCortexAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(GlobalProtectDevice):
        pass

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

    @staticmethod
    def _fill_global_protect_fields(device_raw: dict, device_instance: MyDeviceAdapter):
        try:
            device_instance.serial_number = device_raw.get('endpoint_serial_number')
            device_instance.customer_id = device_raw.get('customer_id')
            device_instance.connect_method = device_raw.get('connect_method')
            device_instance.host_id = device_raw.get('host_id')
            device_instance.event_status = device_raw.get('status')
            device_instance.vendor_name = device_raw.get('customer_id')
        except Exception:
            logger.exception(f'Failed to fill Global Protect instance info for device {device_raw}')

    def _create_global_protect_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = (device_raw.get('customer_id') or '') + (device_raw.get('endpoint_serial_number') or '')
            if not device_id:
                logger.error(f'Bad device with no ID {device_raw}')
                return None
            device.id = f'global_protect_{device_id}'
            device.hostname = device_raw.get('host_id')

            ips = []
            if device_raw.get('private_ip'):
                ips.append(device_raw.get('private_ip'))
            if device_raw.get('private_ipv6'):
                ips.append(device_raw.get('private_ipv6'))
            if device_raw.get('public_ip'):
                ips.append(device_raw.get('public_ip'))
            if device_raw.get('public_ipv6'):
                ips.append(device_raw.get('public_ipv6'))
            device.add_nic(ips=ips)

            src_user = device_raw.get('source_user')
            if src_user:
                device.last_used_users.append(src_user)

            os_string = (device_raw.get('endpoint_os_type') or '') + ' ' + \
                        (device_raw.get('endpoint_os_version') or '')
            device.figure_os(os_string)

            self._fill_global_protect_fields(device_raw, device)

            # NOTICE! 'serial' is not the serial of the device. Its the serial of the firewall!
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Paloalto Cortex Global Protect Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        try:
            for device_raw in devices_raw_data:
                device = self._create_global_protect_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
        except Exception:
            logger.error(f'Failed to create device for {device_raw}')

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'weeks_ago_to_fetch',
                    'title': 'Number of weeks to fetch',
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
