import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import is_valid_ip, is_private_ip, parse_bool_from_raw, int_or_none, normalize_timezone_date
from opendcim_adapter.client_id import get_client_id
from opendcim_adapter.connection import OpendcimConnection
from opendcim_adapter.structures import OpendcimDeviceInstance, OpendcimUserInstance

logger = logging.getLogger(f'axonius.{__name__}')


class OpendcimAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(OpendcimDeviceInstance):
        pass

    class MyUserAdapter(OpendcimUserInstance):
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
        connection = OpendcimConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        proxy_username=client_config.get('proxy_username'),
                                        proxy_password=client_config.get('proxy_password'),
                                        user_id=client_config.get('user_id'),
                                        apikey=client_config.get('apikey'))
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
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema OpendcimAdapter expects from configs

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
                    'name': 'user_id',
                    'title': 'User ID',
                    'type': 'string',
                },
                {
                    'name': 'apikey',
                    'title': 'API key',
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
                'verify_ssl',
                'user_id',
                'apikey',
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_opendcim_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            datacenter = device_raw.get('extra_datacenter')
            if isinstance(datacenter, dict):
                device.dc_id = datacenter.get('DataCenterID')
                device.dc_name = datacenter.get('Name')

            cabinet = device_raw.get('extra_cabinet')
            if isinstance(cabinet, dict):
                device.cabinet_id = cabinet.get('CabinetID')
                device.cabinet_location = cabinet.get('Location')

            device.api_port = int_or_none(device_raw.get('APIPort'))
            device.api_username = device_raw.get('APIUsername')
            device.asset_tag = device_raw.get('AssetTag')
            device.audit_stamp = parse_date(device_raw.get('AuditStamp'))
            device.device_type = device_raw.get('DeviceType')
            device.hypervisor = device_raw.get('Hypervisor')
            device.notes = device_raw.get('Notes')
            device.manufacturer_date = parse_date(normalize_timezone_date(device_raw.get('MfgDate')))
            device.opendcim_owner = int_or_none(device_raw.get('Owner'))
            device.parent_device_id = int_or_none(device_raw.get('ParentDevice'))
            device.number_of_ports = int_or_none(device_raw.get('Ports'))
            device.first_port_number = int_or_none(device_raw.get('FirstPortNum'))
            device.position = int_or_none(device_raw.get('Position'))
            device.psu_count = int_or_none(device_raw.get('PowerSupplyCount'))
            device.primary_contact = int_or_none(device_raw.get('PrimaryContact'))
            device.rear_chassis_slots = int_or_none(device_raw.get('RearChassisSlots'))
            device.rights = device_raw.get('Rights')
            device.snmp_community = device_raw.get('SNMPCommunity')
            device.snmp_failure_count = int_or_none(device_raw.get('SNMPFailureCount'))
            device.snmp_version = device_raw.get('SNMPVersion')
            device.last_reported_status = device_raw.get('Status')
            device.warranty_provider = device_raw.get('WarrantyCo')
            device.warranty_expires = parse_date(normalize_timezone_date(device_raw.get('WarrantyExpire')))
            device.v3_auth_protocol = device_raw.get('v3AuthProtocol')
            device.v3_priv_protocol = device_raw.get('v3PrivProtocol')
            device.v3_security_level = device_raw.get('v3SecurityLevel')
            device.prox_mox_realm = device_raw.get('ProxMoxRealm')
            device.escalation_id = int_or_none(device_raw.get('EscalationID'))
            device.escalation_time_id = int_or_none(device_raw.get('EscalationTimeID'))

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('DeviceID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            # We chose to use Label because it is required field in OpenDCIM and cannot be empty.
            device.id = str(device_id) + '_' + (device_raw.get('Label', ''))

            device.description = device_raw.get('Label')
            device.first_seen = parse_date(normalize_timezone_date(device_raw.get('InstallDate')))
            device.device_managed_by = device_raw.get('PrimaryContact')
            device.device_serial = device_raw.get('SerialNo')

            primary_ip = device_raw.get('PrimaryIP')
            if is_valid_ip(primary_ip):
                if is_private_ip(primary_ip):
                    device.add_nic(ips=[primary_ip])
                else:
                    device.add_public_ip(primary_ip)
            else:
                device.hostname = primary_ip

            self._fill_opendcim_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Opendcim Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Opendcim Device for {device_raw}')

    @staticmethod
    def _fill_opendcim_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.read_access = parse_bool_from_raw(user_raw.get('ReadAccess'))
            user.write_access = parse_bool_from_raw(user_raw.get('WriteAccess'))
            user.delete_access = parse_bool_from_raw(user_raw.get('DeleteAccess'))
            user.second_phone = user_raw.get('Phone2')
            user.third_phone = user_raw.get('Phone3')
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('PersonID')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('UserID', ''))

            user.username = user_raw.get('UserID')
            user.first_name = user_raw.get('FirstName')
            user.last_name = user_raw.get('LastName')
            user.mail = user_raw.get('Email')
            user.user_telephone_number = user_raw.get('Phone1')
            user.is_admin = parse_bool_from_raw(user_raw.get('AdminOwnDevices'))
            user.account_disabled = parse_bool_from_raw(user_raw.get('Disabled'))

            self._fill_opendcim_user_fields(user_raw, user)

            user.set_raw(user_raw)

            return user
        except Exception:
            logger.exception(f'Problem with fetching Opendcim User for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        for user_raw in users_raw_data:
            if not user_raw:
                continue
            try:
                # noinspection PyTypeChecker
                user = self._create_user(user_raw, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching Opendcim User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
