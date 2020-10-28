import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.flexnet.connection import FlexnetConnection
from axonius.clients.flexnet.consts import INVENTORY_TYPE, DEVICE_TYPE, TYPE_FIELD, ASSET_FIELD
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none, float_or_none
from flexnet_adapter.client_id import get_client_id
from flexnet_adapter.structures import FlexnetDeviceInstance, Asset

logger = logging.getLogger(f'axonius.{__name__}')


class FlexnetAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(FlexnetDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = FlexnetConnection(domain=client_config.get('domain'),
                                       verify_ssl=client_config.get('verify_ssl'),
                                       https_proxy=client_config.get('https_proxy'),
                                       proxy_username=client_config.get('proxy_username'),
                                       proxy_password=client_config.get('proxy_password'),
                                       refresh_token=client_config.get('refresh_token'),
                                       organization_id=client_config.get('organization_id'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema FlexnetAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'refresh_token',
                    'title': 'Refresh Token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'organization_id',
                    'title': 'Organization ID',
                    'type': 'string',
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
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'refresh_token',
                'organization_id',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_flexnet_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            assets = device_raw.get(ASSET_FIELD)
            device.assets = []
            if isinstance(assets, list):
                for asset_raw in assets:
                    asset = Asset()
                    asset.department = asset_raw.get('department')
                    metadata = asset_raw.get('metadata')
                    if isinstance(metadata, dict):
                        asset.name = metadata.get('assetName')
                        asset.status = metadata.get('status')
                        asset.tag = metadata.get('assetTag')
                        asset.asset_id = int_or_none(metadata.get('assetId'))
                        asset.asset_type = metadata.get('assetType')
                        asset.category = metadata.get('category')
                        asset.company = metadata.get('assetCompany')
                        asset.expiration_date = parse_date(metadata.get('expiryDate'))
                        asset.installation_date = parse_date(metadata.get('installedOn'))
                        asset.manufacturer = metadata.get('manufacturer')
                        asset.model_number = metadata.get('modelNumber')
                        asset.serial_number = metadata.get('serialNumber')
                    device.assets.append(asset)

            device.device_kind = device_raw.get(TYPE_FIELD)
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('computerId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('computerName') or '')

            device.hostname = device_raw.get('computerName')
            device.figure_os(os_string=device_raw.get('os'))
            ip_address = device_raw.get('ipAddress')
            if isinstance(ip_address, str):
                ip_address = [ip_address]
            device.add_ips_and_macs(ips=ip_address)
            device.device_serial = device_raw.get('serialNo')
            softwares = device_raw.get('softwareTitles')
            if isinstance(softwares, list):
                for software in softwares:
                    if not isinstance(software, dict):
                        continue
                    device.add_installed_software(version=software.get(
                        'version'), name=software.get('softwareTitleName'))

            self._fill_flexnet_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Flexnet Device for {device_raw}')
            return None

    @staticmethod
    def _create_inventory(device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('hostId') or '')

            device.hostname = device_raw.get('hostId')
            device.last_seen = parse_date(device_raw.get('lastInventoryDate'))
            device.name = device_raw.get('name')
            device.figure_os(os_string=device_raw.get('os'))
            ip_address = device_raw.get('ipAddress')
            if isinstance(ip_address, str):
                ip_address = [ip_address]
            device.add_ips_and_macs(ips=ip_address)
            device.device_serial = device_raw.get('serialNumber')
            device.device_manufacturer = device_raw.get('manufacturer')
            device.device_model = device_raw.get('model')
            device.owner = device_raw.get('assignedTo')
            device.physical_location = device_raw.get('location')
            device.total_physical_memory = float_or_none(device_raw.get('ram'))
            try:
                device.device_type = device_raw.get('deviceType')
            except Exception as e:
                logger.warning(f'Couldn\'t parse device type: {device_raw.get("deviceType")}')

            device.device_kind = device_raw.get(TYPE_FIELD)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Flexnet Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                if not device_raw.get(TYPE_FIELD):
                    logger.error(f'Device is missing type: {device_raw}')
                    continue
                if device_raw.get(TYPE_FIELD) == DEVICE_TYPE:
                    device = self._create_device(device_raw, self._new_device_adapter())
                elif device_raw.get(TYPE_FIELD) == INVENTORY_TYPE:
                    device = self._create_inventory(device_raw, self._new_device_adapter())
                else:
                    continue
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Flexnet Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
