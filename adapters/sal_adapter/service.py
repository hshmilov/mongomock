import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from sal_adapter.connection import SalConnection
from sal_adapter.client_id import get_client_id
from sal_adapter.structures import SalDeviceInstance, SalInventory, SalApplication
from sal_adapter.consts import INVENTORY_KEY

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class SalAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(SalDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _parse_float(value):
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _parse_int(value):
        try:
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value
        return None

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = SalConnection(domain=client_config['domain'],
                                   verify_ssl=client_config['verify_ssl'],
                                   https_proxy=client_config.get('https_proxy'),
                                   public_key=client_config['public_key'],
                                   private_key=client_config['private_key'])
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
        The schema SalAdapter expects from configs

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
                    'name': 'public_key',
                    'title': 'Public Key',
                    'type': 'string'
                },
                {
                    'name': 'private_key',
                    'title': 'Private Key',
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
                'domain',
                'public_key',
                'private_key',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _fill_sal_inventory_fields(self, inventory_raw: list, device: MyDeviceAdapter):
        try:
            if not isinstance(inventory_raw, list):
                logger.warning(f'Received invalid data for inventory {inventory_raw}')
                return

            inventories = []
            for inventory in inventory_raw or []:
                device_inventory = SalInventory()

                device_inventory.id = self._parse_int(inventory.get('id'))
                device_inventory.version = inventory.get('version')
                device_inventory.path = inventory.get('path')

                if isinstance(inventory.get('application'), dict):
                    device_application = SalApplication()
                    application = inventory.get('application')

                    device_application.id = self._parse_int(application.get('id'))
                    device_application.name = application.get('name')
                    device_application.bundle_id = application.get('bundle_id')
                    device_application.bundle_name = application.get('bundle_name')

                    device_inventory.application = device_application

                inventories.append(device_inventory)

            device.inventories = inventories
        except Exception:
            logger.exception(f'Failed creating inventory fields for inventory {inventory_raw}')

    def _fill_sal_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.machine_group = device_raw.get('machine_group')
            device.sal_version = device_raw.get('sal_version')
            device.deployed = self._parse_bool(device_raw.get('deployed'))
            device.broken_client = self._parse_bool(device_raw.get('broken_client'))
            device.hd_space = self._parse_int(device_raw.get('hd_space'))
            device.hd_total = self._parse_int(device_raw.get('hd_total'))
            device.hd_percent = self._parse_float(device_raw.get('hd_percent'))
            device.console_user = device_raw.get('console_user')
            device.machine_model_friendly = device_raw.get('machine_model_friendly')
            device.munki_version = device_raw.get('munki_version')
            device.manifest = device_raw.get('manifest')

            if device_raw.get(INVENTORY_KEY):
                self._fill_sal_inventory_fields(device_raw.get(INVENTORY_KEY), device)

        except Exception:
            logger.exception(f'Failed creating fields for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('hostname') or '')

            device.hostname = device_raw.get('hostname')
            device.device_serial = device_raw.get('serial')
            device.first_seen = parse_date(device_raw.get('first_checkin'))
            device.last_seen = parse_date(device_raw.get('last_checkin'))
            device.device_model = device_raw.get('machine_model')

            device.add_hd(total_size=self._parse_int(device_raw.get('hd_total')),
                          free_size=self._parse_int(device_raw.get('hd_space')))

            cpu_speed = self._parse_float(device_raw.get('cpu_speed'))
            device.add_cpu(name=device_raw.get('cpu_type'),
                           ghz=cpu_speed,
                           family=device_raw.get('os_family'))

            os_string = f'{device_raw.get("operating_system") or ""} {device_raw.get("os_family") or ""}'
            device.figure_os(os_string=os_string)

            self._fill_sal_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Sal Device for {device_raw}')
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
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Sal Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
