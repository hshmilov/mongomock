import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.utils.parsing import parse_unix_timestamp
from dynatrace_adapter.connection import DynatraceConnection
from dynatrace_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class DynatraceAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        discoverd_name = Field(str, 'Discoverd Name')
        management_zones = ListField(str, 'Management Zone')
        consumed_host_units = Field(float, 'Consumed Host Units')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = DynatraceConnection(premise_domain=client_config.get('premise_domain'),
                                         environment_id=client_config['environment_id'],
                                         verify_ssl=client_config['verify_ssl'],
                                         apikey=client_config['apikey'],
                                         https_proxy=client_config.get('https_proxy'))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema DynatraceAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'premise_domain',
                    'title': 'Dynatrace Domain (For On-Premise)',
                    'type': 'string'
                },
                {
                    'name': 'environment_id',
                    'title': 'Environment ID',
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
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'environment_id',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('entityId')
            if not device_id:
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('displayName') or '')
            device.name = device_raw.get('displayName')
            device.discoverd_name = device_raw.get('discoveredName')
            try:
                if device_raw.get('lastSeenTimestamp') and isinstance(device_raw.get('lastSeenTimestamp'), int):
                    device.last_seen = parse_unix_timestamp(device_raw.get('lastSeenTimestamp'))
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            try:
                if device_raw.get('firstSeenTimestamp') and isinstance(device_raw.get('firstSeenTimestamp'), int):
                    device.first_seen = parse_unix_timestamp(device_raw.get('firstSeenTimestamp'))
            except Exception:
                logger.exception(f'Problem getting first seen for {device_raw}')
            try:
                if device_raw.get('ipAddresses') and isinstance(device_raw.get('ipAddresses'), list):
                    device.add_nic(None, device_raw.get('ipAddresses'))
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            try:
                device.figure_os((device_raw.get('osType') or '') + ' ' + (device_raw.get('osVersion') or '')
                                 + ' ' + (device_raw.get('osArchitecture') or ''))
            except Exception:
                logger.exception(f'Problem adding os to {device_raw}')
            try:
                device.total_number_of_cores = device_raw.get('cpuCores')
            except Exception:
                logger.exception(f'Problem adding cores to {device_raw}')
            try:
                if isinstance(device_raw.get('managementZones'), list):
                    for management_zone_raw in device_raw.get('managementZones'):
                        if management_zone_raw.get('name'):
                            device.management_zones.append(management_zone_raw.get('name'))
            except Exception:
                logger.exception(f'Problem adding management zones to {device_raw}')
            try:
                if device_raw.get('consumedHostUnits'):
                    device.consumed_host_units = device_raw.get('consumedHostUnits')
            except Exception:
                logger.exception(f'Problem getting consumed host units for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Dynatrace Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
