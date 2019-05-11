import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid, parse_unix_timestamp
from axonius.utils.files import get_local_config_file
from datto_rmm_adapter.connection import DattoRmmConnection
from datto_rmm_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class DattoRmmAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        online = Field(bool, 'Online')
        deleted = Field(bool, 'Deleted')
        last_audit_date = Field(datetime.datetime, 'Last Audit Date')
        creation_date = Field(datetime.datetime, 'Creation Date')
        device_class = Field(str, 'Device Class')
        display_version = Field(str, 'Display Version')
        cag_version = Field(str, 'Cag Version')
        antivirus_product = Field(str, 'Antivirus Product')
        antivirus_status = Field(str, 'Antivirus Status')
        device_type = Field(str, 'Device Type')
        device_category = Field(str, 'Device Category')
        patch_status = Field(str, 'Patch Status')
        site_name = Field(str, 'Site Name')
        software_status = Field(str, 'Software Status')

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
        connection = DattoRmmConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        apikey=client_config['apikey'],
                                        api_secretkey=client_config['api_secretkey'])
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
        The schema DattoRmmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'DattoRmm Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string'
                },
                {
                    'name': 'api_secretkey',
                    'title': 'API Secret Key',
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
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'api_secretkey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('hostname') or '')
            device.hostname = device_raw.get('hostname')
            device.site_name = device_raw.get('siteName')
            device.uuid = device_raw.get('uid')
            av_data = device_raw.get('antivirus')
            device.warranty_date = parse_date(device_raw.get('warrantyDate'))
            if av_data and isinstance(av_data, dict):
                device.antivirus_product = av_data.get('antivirusProduct')
                device.antivirus_status = av_data.get('antivirusStatus')
            type_data = device_raw.get('deviceType')
            if type_data and isinstance(type_data, dict):
                device.device_type = type_data.get('type')
                device.device_category = type_data.get('category')
            patch_data = device_raw.get('patchManagement')
            if patch_data and isinstance(patch_data, dict):
                device.patch_status = patch_data.get('patchStatus')
            if device_raw.get('intIpAddress'):
                device_raw.add_nic(ips=[device_raw.get('intIpAddress')])
            if device_raw.get('extIpAddress'):
                device.add_public_ip(device_raw.get('extIpAddress'))
            domain = device_raw.get('domain')
            if is_domain_valid(domain):
                device.domain = domain
            if device_raw.get('lastLoggedInUser'):
                device.last_used_users = [device_raw.get('lastLoggedInUser')]
            device.last_seen = parse_unix_timestamp(device_raw.get('lastSeen'))
            device.set_boot_time(boot_time=parse_unix_timestamp(device_raw.get('lastReboot')))
            device.online = bool(device_raw.get('online'))
            device.last_audit_date = parse_unix_timestamp(device_raw.get('lastAuditDate'))
            device.description = device_raw.get('description')
            device.creation_date = parse_unix_timestamp(device_raw.get('creationDate'))
            device.deleted = bool(device_raw.get('deleted'))
            device.figure_os(device_raw.get('operatingSystem'))
            device.device_class = device_raw.get('deviceClass')
            device.cag_version = device_raw.get('cagVersion')
            device.software_status = device_raw.get('softwareStatus')
            device.display_version = device_raw.get('displayVersion')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching DattoRmm Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
