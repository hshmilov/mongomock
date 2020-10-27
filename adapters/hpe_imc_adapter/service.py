import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from hpe_imc_adapter.connection import HpeImcConnection
from hpe_imc_adapter.client_id import get_client_id
from hpe_imc_adapter.structures import HpeImcDeviceInstance, HpeImcUserInstance, parse_status, parse_int, \
    parse_login_method, parse_bool

logger = logging.getLogger(f'axonius.{__name__}')


class HpeImcAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(HpeImcDeviceInstance):
        pass

    class MyUserAdapter(HpeImcUserInstance):
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
        connection = HpeImcConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      username=client_config['username'],
                                      password=client_config['password'])
        with connection:
            pass
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
        Get all devices from a specific  domain

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
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema HpeImcAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'HPE IMC Domain',
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
    def _fill_hpe_imc_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.label = device_raw.get('label')
            status_raw = parse_int(device_raw.get('status'))
            device.status_raw = status_raw
            device.status = parse_status(status_raw)
            device.contact = device_raw.get('contact')
            device.sys_oid = device_raw.get('sysOid')
            device.runtime = device_raw.get('runtime')
            login_method_raw = parse_int(device_raw.get('loginType'))
            device.login_method_raw = login_method_raw
            device.login_method = parse_login_method(login_method_raw)
            device.category_id = parse_int(device_raw.get('categoryId'))
            device.is_support_ping = parse_bool(device_raw.get('supportPing'))
            device.snmp_template_id = parse_int(device_raw.get('snmpTmplId'))
            device.telnet_template_id = parse_int(device_raw.get('telnetTmplId'))
            device.ssh_template_id = parse_int(device_raw.get('sshTmplId'))
            device.web_mgmt_port = parse_int(device_raw.get('webMgrPort')) or None  # 0 should be interpreted as None
            device.cfg_poll_interval = parse_int(device_raw.get('configPollTime'))
            device.status_poll_interval = parse_int(device_raw.get('statePollTime'))
            device.parent_id = parse_int(device_raw.get('parentId'))
            device.type_name = device_raw.get('typeName')
            device.bin_file = device_raw.get('version')
            device.children = parse_int(device_raw.get('childrenNum'))
            device.verge_net = parse_int(device_raw.get('vergeNet'))
            device.phy_name = device_raw.get('phyName')
            device.created_time = parse_date(device_raw.get('phyCreateTime'))
            device.phy_creator = device_raw.get('phyCreator')
            device.append_unicode = device_raw.get('appendUnicode')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('label') or '')
            mac = device_raw.get('mac') or None
            ip = device_raw.get('ip') or None
            mask = device_raw.get('mask')
            if mask and ip:
                subnet = [f'{ip}/{mask}']
            else:
                subnet = None
            device.add_nic(mac, ips=[ip], subnets=subnet)
            device.name = device_raw.get('label') or device_raw.get('phyName')
            device.physical_location = device_raw.get('location')
            device.hostname = device_raw.get('sysName') or None
            device.description = device_raw.get('sysDescription') or None
            device.first_seen = parse_date(device_raw.get('phyCreateTime'))
            device.last_seen = parse_date(device_raw.get('lastPoll'))
            try:
                device.figure_os(device_raw.get('sysDescription'), guess=True)
            except Exception as e:
                logger.warning(f'Failed to guess device OS: for {device_raw}: {str(e)}')
            self._fill_hpe_imc_device_fields(device_raw, device)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching HpeImc Device for {device_raw}')
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
                logger.exception(f'Problem with fetching HpeImc Device for {device_raw}')

    @staticmethod
    def _fill_hpe_imc_user_fields(user_raw: dict, user: MyUserAdapter):
        # only ss_type here
        try:
            user.ss_type = user_raw.get('ssType')
        except Exception:
            logger.exception(f'Failed parsing ss_type for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if not user_id:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = user_id + '_' + (user_raw.get('userName') or '')
            user.username = user_raw.get('certification')
            user.display_name = user_raw.get('userName')
            user.mail = user_raw.get('email')
            user.user_telephone_number = user_raw.get('phone')
            user.user_city = user_raw.get('address')

            self._fill_hpe_imc_user_fields(user_raw, user)

            user.set_raw(user_raw)

            return user
        except Exception:
            logger.exception(f'Problem with fetching HpeImc User for {user_raw}')
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
                logger.exception(f'Problem with fetching HpeImc User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
