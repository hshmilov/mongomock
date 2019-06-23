import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from jumpcloud_adapter.connection import JumpcloudConnection
from jumpcloud_adapter.client_id import get_client_id
from jumpcloud_adapter.consts import DEFAULT_JUMPCLOUD_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class JumpcloudAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        organization = Field(str, 'Organization')
        display_name = Field(str, 'Display Name')
        template_name = Field(str, 'Template Name')
        remote_ip = Field(str, 'Remote IP')
        is_active = Field(bool, 'Is Active')
        created = Field(datetime.datetime, 'Created')
        agent_version = Field(str, 'Agent Version')
        jumpcloud_tags = ListField(str, 'JumpCloud Tags')
        allow_ssh_root_login = Field(bool, 'Allow SSH Root Login')

    class MyUserAdapter(UserAdapter):
        activated = Field(bool, 'Activated')
        jumpcloud_tags = ListField(str, 'JumpCloud Tags')
        location = Field(str, 'Location')
        company = Field(str, 'Company')
        bad_login_attempts = Field(int, 'Bad Login Attempts')
        organization = Field(str, 'Organization')
        passwordless_sudo = Field(bool, 'Passwordless Sudo')
        password_expired = Field(bool, 'Password Expired')
        sudo = Field(bool, 'Sudo')

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
        connection = JumpcloudConnection(domain=client_config['domain'],
                                         verify_ssl=client_config['verify_ssl'],
                                         https_proxy=client_config.get('https_proxy'),
                                         apikey=client_config['apikey'])
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
        The schema JumpcloudAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'JumpCloud Domain',
                    'type': 'string',
                    'default': DEFAULT_JUMPCLOUD_DOMAIN
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
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('hostname') or '')
            device.hostname = device_raw.get('hostname')
            device.organization = device_raw.get('organization')
            device.created = parse_date(device_raw.get('created'))
            device.last_seen = parse_date(device_raw.get('lastContact'))
            device.figure_os((device_raw.get('os') or '') + ' ' + (device_raw.get('version') or ''))
            device.display_name = device_raw.get('displayName')
            device.template_name = device_raw.get('templateName')
            try:
                if device_raw.get('system_users') and isinstance(device_raw.get('system_users'), list):
                    device.last_used_users = device_raw.get('system_users')
            except Exception:
                logger.exception(f'Problem with users for {device_raw}')
            device.device_serial = device_raw.get('serialNumber')
            device.remote_ip = device_raw.get('remoteIP')
            try:
                if isinstance(device_raw.get('networkInterfaces'), list):
                    for nic in device_raw.get('networkInterfaces'):
                        try:
                            if nic.get('address') and not nic.get('name') == 'lo':
                                device.add_nic(ips=[nic.get('address')], name=nic.get('name'))
                        except Exception:
                            logger.exception(f'Problem adding nic {nic}')
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            device.is_active = bool(device_raw.get('active'))
            device.allow_ssh_root_login = bool(device_raw.get('allowSshRootLogin'))
            device.agent_version = device_raw.get('agentVersion')
            if device_raw.get('amazonInstanceID'):
                device.cloud_id = device_raw.get('amazonInstanceID')
                device.cloud_provider = 'AWS'
            if isinstance(device_raw.get('tags'), list):
                device.jumpcloud_tags = device_raw.get('tags')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Jumpcloud Device for {device_raw}')
            return None

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('_id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('email') or '')
            user.mail = user_raw.get('email')
            user.username = user_raw.get('username')
            user.first_name = user_raw.get('firstname')
            user.user_department = user_raw.get('department')
            user.location = user_raw.get('location')
            user.last_name = user_raw.get('lastname')
            user.activated = bool(user_raw.get('activated'))
            user.employee_id = user_raw.get('employeeIdentifier')
            user.employee_type = user_raw.get('employeeType')
            user.company = user_raw.get('company')
            user.description = user_raw.get('description')
            user.display_name = user_raw.get('displayname')
            user.password_never_expires = bool(user_raw.get('password_never_expires'))
            if isinstance(user_raw.get('badLoginAttempts'), int):
                user.bad_login_attempts = user_raw.get('badLoginAttempts')
            if isinstance(user_raw.get('tags'), list):
                user.jumpcloud_tags = user_raw.get('tags')
            user.user_title = user_raw.get('jobTitle')
            user.organization = user_raw.get('organization')
            user.user_created = parse_date(user_raw.get('created'))
            user.is_locked = bool(user_raw.get('account_locked'))
            user.passwordless_sudo = bool(user_raw.get('passwordless_sudo'))
            user.password_expired = bool(user_raw.get('password_expired'))
            user.sudo = user_raw.get('sudo') if isinstance(user_raw.get('sudo'), bool) else None
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Jumpcloud user for {user_raw}')
            return None

    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            yield from data.get_user_list()

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, raw_data):
        for user_raw in raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Manager, AdapterProperty.Agent]
