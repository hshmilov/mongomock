import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none, parse_bool_from_raw
from axonius.clients.net_app.connection import NetAppConnection
from axonius.clients.net_app.consts import SECONDS_IN_DAY
from net_app_adapter.client_id import get_client_id
from net_app_adapter.structures import NetAppDeviceInstance, NetAppUserInstance, Version, \
    AccountApplication, HighAvailability


logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class NetAppAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(NetAppDeviceInstance):
        pass

    class MyUserAdapter(NetAppUserInstance):
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
        connection = NetAppConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      username=client_config['username'],
                                      password=client_config['password'])
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
        The schema NetAppAdapter expects from configs
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
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
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
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_device_high_availability(device_raw: dict, device: MyDeviceAdapter):
        try:
            high_availability = HighAvailability()
            high_availability.auto_giveback = parse_bool_from_raw(device_raw.get('auto_giveback'))
            high_availability.enabled = parse_bool_from_raw(device_raw.get('enabled'))

            if isinstance(device_raw.get('partners'), list):
                high_availability.partners = device_raw.get('partners')
            elif isinstance(device_raw.get('partners'), str):
                high_availability.partners = [device_raw.get('partners')]
            device.high_availability = high_availability
        except Exception:
            logger.exception(f'Failed creating HA (High Availability) for device {device_raw}')

    @staticmethod
    def _fill_device_version(device_raw: dict, device: MyDeviceAdapter):
        try:
            version = Version()
            version.generation = int_or_none(device_raw.get('generation'))
            version.minor = int_or_none(device_raw.get('minor'))
            version.major = int_or_none(device_raw.get('major'))
            version.full = device_raw.get('full')
            device.version = version
        except Exception:
            logger.exception(f'Failed creating Version for {device_raw}')

    @staticmethod
    def _add_nic_from_list(interfaces: list, device: MyDeviceAdapter):
        try:
            for interface in interfaces:
                if isinstance(interface, dict):
                    address = []
                    ip = interface.get('ip')
                    if ip and isinstance(ip, dict):
                        address = ip.get('address') or []
                        if isinstance(address, str):
                            address = [address]
                    name = interface.get('name')
                    device.add_nic(ips=address, name=name)
        except Exception:
            logger.exception(f'Failed adding nic from list for {interfaces}')

    @staticmethod
    def _add_service_processor(service_processor: dict, device: MyDeviceAdapter):
        mac = service_processor.get('mac_address') if isinstance(service_processor.get('mac_address'), str) else None

        def add_ip_interface(ip_interface: dict):
            ip = []
            netmask = []
            gateway = []
            try:
                if ip_interface.get('netmask') and isinstance(ip_interface.get('netmask'), str):
                    netmask.append(ip_interface.get('netmask'))
                if ip_interface.get('address') and isinstance(ip_interface.get('address'), str):
                    ip.append(ip_interface.get('address'))
                if ip_interface.get('gateway') and isinstance(ip_interface.get('gateway'), str):
                    gateway.append(ip_interface.get('gateway'))
                device.add_nic(mac=mac, ips=ip, gateway=gateway, subnets=netmask)
            except Exception:
                logger.exception(f'Failed adding ip interface for {ip_interface}')

        if isinstance(service_processor.get('ipv4_interface'), dict):
            add_ip_interface(service_processor.get('ipv4_interface'))
        if isinstance(service_processor.get('ipv6_interface'), dict):
            add_ip_interface(service_processor.get('ipv6_interface'))

    def _fill_netapp_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            try:
                membership = device_raw.get('membership')
                device.membership = membership
            except Exception:
                if membership is not None:
                    logger.exception(f'Failed parsing membership, got {membership} of type {type(membership)}')

            try:
                controller_raw = device_raw.get('controller')
                if isinstance(controller_raw, dict):
                    over_temperature = controller_raw.get('over_temperature')
                    device.over_temperature = over_temperature
            except Exception:
                if over_temperature is not None:
                    logger.exception(f'Failed parsing over temperature, got {over_temperature} of type '
                                     f'{type(over_temperature)}')

            if device_raw.get('ha') and isinstance(device.get('ha'), dict):
                self._fill_device_high_availability(device_raw.get('ha'), device)

            if device_raw.get('version') and isinstance(device_raw.get('version'), dict):
                self._fill_device_version(device_raw.get('version'), device)
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('uuid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.last_seen = parse_date(device_raw.get('date'))
            uptime_seconds = int_or_none(device_raw.get('uptime'))
            # convert seconds to days
            if uptime_seconds:
                device.uptime = int(uptime_seconds / SECONDS_IN_DAY)
            device.physical_location = device_raw.get('location')
            device.uuid = device_raw.get('uuid')
            device.device_serial = device_raw.get('serial_number')
            device.device_model = device_raw.get('model')

            if isinstance(device_raw.get('cluster_interfaces'), list):
                self._add_nic_from_list(device_raw.get('cluster_interfaces'), device)

            if isinstance(device_raw.get('management_interfaces'), list):
                self._add_nic_from_list(device_raw.get('management_interfaces'), device)

            if isinstance(device_raw.get('service_processor'), dict):
                self._add_service_processor(device_raw.get('service_processor'), device)

            self._fill_netapp_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching NetApp Device for {device_raw}')
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
                logger.exception(f'Problem with fetching NetApp Device for {device_raw}')

    @staticmethod
    def _fill_user_account_applications(applications: list, user: MyUserAdapter):
        try:
            user_applications = []
            for application in applications:
                if isinstance(application, dict):
                    user_application = AccountApplication()

                    user_application.second_authentication_method = application.get('second_authentication_method')
                    if isinstance(application.get('authentication_methods'), str):
                        user_application.authentication_methods = [application.get('authentication_methods')]
                    elif isinstance(application.get('authentication_methods'), list):
                        user_application.authentication_methods = application.get('authentication_methods')

                    try:
                        application_type = application.get('application')
                        user_application.application = application_type
                    except Exception:
                        if application_type is not None:
                            logger.exception(f'Failed parsing application type, got {application_type} of type '
                                             f'{type(application_type)}')

                    user_applications.append(user_application)

            user.applications = user_applications
        except Exception:
            logger.exception(f'Failed creating Account Application for {application}')

    def _fill_netapp_user_fields(self, user_raw: dict, user: MyUserAdapter):
        try:
            if user_raw.get('owner') and isinstance(user_raw.get('owner'), dict):
                user.svm_uuid = user_raw.get('owner').get('uuid')
                user.svm_name = user_raw.get('owner').get('name')

            try:
                scope = user_raw.get('scope')
                user.scope = scope
            except Exception:
                if scope is not None:
                    logger.exception(f'Failed parsing scope, got {scope} and type {type(scope)}')

            if user_raw.get('applications') and isinstance(user_raw.get('applications'), list):
                self._fill_user_account_applications(user_raw.get('applications'), user)

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = None
            if user_raw.get('owner') and isinstance(user_raw.get('owner'), dict):
                user_id = user_raw.get('owner').get('uuid')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('name') or '')

            name = user_raw.get('name')
            if isinstance(name, str) and '\\' in name:
                domain, username = name.split('\\', 1)
                user.domain = domain
                user.username = username
            else:
                user.username = name

            user.is_locked = parse_bool_from_raw(user_raw.get('locked'))

            if user_raw.get('role') and isinstance(user_raw.get('role'), dict):
                user.user_title = user_raw.get('role').get('name')

            self._fill_netapp_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching NetApp User for {user_raw}')
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
                logger.exception(f'Problem with fetching NetApp User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
