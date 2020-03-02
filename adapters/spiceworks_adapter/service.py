import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from spiceworks_adapter.structures import SpiceworkDevice
from spiceworks_adapter.client_id import get_client_id
from spiceworks_adapter.connection import SpiceworksConnection

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class SpiceworksAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(SpiceworkDevice):
        pass

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
        connection = SpiceworksConnection(domain=client_config['domain'],
                                          username=client_config['username'],
                                          password=client_config['password'])
        with connection:
            pass  # check the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException:
            message = f'Error connecting to client with domain {client_config["domain"]}'
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
        The schema SpiceworksAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Spiceworks Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'username',
                'password'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-instance-attributes,too-many-statements
    @staticmethod
    def _fill_spiceworks_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.asset_tag = device_raw.get('asset_tag')
            device.auto_tag = device_raw.get('auto_tag')
            device.avatar_id = device_raw.get('avatar_id')
            device.b_asset_tag = device_raw.get('b_asset_tag')
            device.b_description = device_raw.get('b_description')
            device.b_device_type = device_raw.get('b_device_type')
            device.b_location = device_raw.get('b_location')
            device.b_manufacturer = device_raw.get('b_manufacturer')
            device.b_model = device_raw.get('b_model')
            device.b_name = device_raw.get('b_name')
            device.b_primary_owner_name = device_raw.get('b_primary_owner_name')
            device.b_serial_number = device_raw.get('b_serial_number')
            device.bios_date = parse_date(device_raw.get('bios_date'))
            device.c_purchase_date = parse_date(device_raw.get('c_purchase_date'))
            device.c_purchase_price = device_raw.get('c_purchase_price')
            device.created_on = parse_date(device_raw.get('created_on'))
            device.device_type = device_raw.get('device_type')
            device.domain_name = device_raw.get('dn')
            device.domain_role = device_raw.get('domain_role')
            device.error_alert_count = device_raw.get('error_alert_count')
            device.exclude_tag = device_raw.get('exclude_tag')
            device.install_date = parse_date(device_raw.get('install_date'))
            device.ip_comparable = device_raw.get('ip_comparable')
            device.last_backup_time = device_raw.get('last_backup_time')
            device.last_boot_up_time = device_raw.get('last_boot_up_time')
            device.last_qrcode_time = device_raw.get('last_qrcode_time')
            device.last_scan_time = device_raw.get('last_scan_time')
            device.location = device_raw.get('location')
            device.management_oid = device_raw.get('management_oid')
            device.manually_added = device_raw.get('manually_added')
            device.mdm_service_id = device_raw.get('mdm_service_id')
            device.memory = device_raw.get('memory')
            device.number_of_licensed_users = device_raw.get('number_of_licensed_users')
            device.number_of_processors = device_raw.get('number_of_processors')
            device.offline_at = parse_date(device_raw.get('offline_at'))
            device.online_at = parse_date(device_raw.get('online_at'))
            device.open_ticket_count = device_raw.get('open_ticket_count')
            device.page_count = device_raw.get('page_count')
            device.port_scan_results = device_raw.get('port_scan_results')
            device.processor_architecture = device_raw.get('processor_architecture')
            device.processor_type = device_raw.get('processor_type')
            device.product_categories = device_raw.get('product_categories')
            device.product_info_id = device_raw.get('product_info_id')
            device.raw_manufacturer = device_raw.get('raw_manufacturer')
            device.raw_model = device_raw.get('raw_model')
            device.raw_operating_system = device_raw.get('raw_operating_system')
            device.raw_processor_type = device_raw.get('raw_processor_type')
            device.raw_serial_number = device_raw.get('raw_serial_number')
            device.reported_by_id = device_raw.get('reported_by_id')
            device.scan_preferences = device_raw.get('scan_preferences')
            device.scan_state = device_raw.get('scan_state')
            device.server_name = device_raw.get('server_name')
            device.service_pack_major_version = device_raw.get('service_pack_major_version')
            device.service_pack_minor_version = device_raw.get('service_pack_minor_version')
            device.site_id = device_raw.get('site_id')
            device.spice_version = device_raw.get('spice_version')
            device.swid = device_raw.get('swid')
            device.user_id = device_raw.get('user_id')
            device.user_tag = device_raw.get('user_tag')
            device.version = device_raw.get('version')
            device.virtual_machine = device_raw.get('vm')
            device.vpro_level = device_raw.get('vpro_level')
            device.warning_alert_count = device_raw.get('warning_alert_count')
            device.windows_product_id = device_raw.get('windows_product_id')
            device.windows_user = device_raw.get('windows_user')
            device.user_primary = device_raw.get('user_primary')

            return device
        except Exception:
            logger.exception(f'Failed to parse spiceworks instance info for device {device_raw}')
            return None

    def _fill_device_fields(self, device, device_raw):
        try:
            device_id = device_raw.get('id')
            if not device_id:
                message = f'Bad device with no ID {device_raw}'
                logger.warning(message)
                raise Exception(message)
            device.id = str(device_id) + '_' + device_raw.get('mac_address')
            device.name = device_raw.get('name')
            device.domain = device_raw.get('domain')
            device.bios_version = device_raw.get('bios_version')
            device.uuid = device_raw.get('uuid')
            device.description = device_raw.get('description')
            device.device_serial = device_raw.get('serial_number')
            device.current_logged_user = device_raw.get('current_user')
            device.last_seen = parse_date(device_raw.get('updated_on'))
            device.device_manufacturer = device_raw.get('manufacturer')
            device.device_model = device_raw.get('model')
            device.uptime = parse_date(device_raw.get('up_time'))

            last_used_users = device_raw.get('primary_owner_name')
            if not last_used_users:
                last_used_users = []
            if isinstance(last_used_users, str):
                last_used_users = [last_used_users]
            if last_used_users:
                for user in last_used_users:
                    if user:
                        device.last_used_users.append(user)

            try:
                os_str = (device_raw.get('operating_system') or '') + ' ' \
                    + (device_raw.get('os_serial_number') or '') + ' ' \
                    + (device_raw.get('os_architecture') or '')
                device.figure_os(os_str)
                device.os.kernel_version = device_raw.get('kernel')
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')

            try:
                device.add_ips_and_macs(ips=[device_raw.get('ip_address')], macs=[device_raw.get('mac_address')])
            except Exception:

                logger.exception(f'Failed to parse IP for device {device_raw}')

            try:
                self._fill_spiceworks_fields(device_raw, device)
            except Exception:
                logger.exception(f'Failed to fill Spicework fields for {device_raw}')

        except Exception:
            logger.exception(f'Failed to parse device id for {device_raw}')
            raise

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            self._fill_device_fields(device, device_raw)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Spiceworks Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                device = self._create_device(device_raw)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
