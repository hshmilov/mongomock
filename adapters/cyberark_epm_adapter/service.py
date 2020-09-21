import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.cyberark_epm.connection import CyberarkEpmConnection
from axonius.clients.cyberark_epm.consts import AuthenticationMethods, EXTRA_SET, EXTRA_POLICY
from axonius.devices.device_adapter import AGENT_NAMES
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from cyberark_epm_adapter.client_id import get_client_id
from cyberark_epm_adapter.structures import CyberarkEpmDeviceInstance, Set, Policy, Application

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class CyberarkEpmAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(CyberarkEpmDeviceInstance):
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
        connection = CyberarkEpmConnection(domain=client_config.get('domain'),
                                           auth_method=client_config.get('auth_method'),
                                           app_id=client_config.get('app_id'),
                                           verify_ssl=client_config.get('verify_ssl'),
                                           https_proxy=client_config.get('https_proxy'),
                                           proxy_username=client_config.get('proxy_username'),
                                           proxy_password=client_config.get('proxy_password'),
                                           username=client_config.get('username'),
                                           password=client_config.get('password'))
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
        The schema CyberarkEpmAdapter expects from configs

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
                    'name': 'auth_method',
                    'title': 'Authentication Method',
                    'type': 'string',
                    'enum': [auth_method.value for auth_method in AuthenticationMethods],
                    'default': AuthenticationMethods.EPM.value
                },
                {
                    'name': 'app_id',
                    'title': 'Application ID',
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
                'auth_method',
                'app_id',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_cyberark_epm_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.device_type = device_raw.get('ComputerType')
            device.status = device_raw.get('Status')

            if isinstance(device_raw.get(EXTRA_SET), dict) and device_raw.get(EXTRA_SET):
                set_obj_raw = device_raw.get(EXTRA_SET)
                set_obj = Set()
                set_obj.id = set_obj_raw.get('Id')
                set_obj.name = set_obj_raw.get('Name')
                set_obj.description = set_obj_raw.get('Description')
                set_obj.is_npvdi = parse_bool_from_raw(set_obj_raw.get('IsNPVDI'))
                device.set_obj = set_obj

            if isinstance(device_raw.get(EXTRA_POLICY), dict) and device_raw.get(EXTRA_POLICY):
                policy_raw = device_raw.get(EXTRA_POLICY)
                policy = Policy()
                policy.id = policy_raw.get('PolicyId')
                policy.policy_type = policy_raw.get('PollicyType')
                policy.name = policy_raw.get('PolicyName')
                policy.action = policy_raw.get('Action')
                policy.description = policy_raw.get('Description')
                policy.active = parse_bool_from_raw(policy_raw.get('Active'))
                policy.create_time = parse_date(policy_raw.get('CreateTime'))
                policy.update_time = parse_date(policy_raw.get('UpdateTime'))
                policy.priority = int_or_none(policy_raw.get('Priority'))

                if isinstance(policy_raw.get('Applications'), list):
                    applications = []
                    for application_raw in policy_raw.get('Applications'):
                        application = Application()
                        application.app_type = application_raw.get('Type')
                        application.description = application_raw.get('Description')
                        application.name = application_raw.get('FileName')
                        application.location = application_raw.get('Location')
                        application.owner = application_raw.get('Owner')
                        applications.append(application)

                    policy.applications = applications
                device.policy = policy

        except Exception:
            logger.exception(f'Failed creating instance for computer {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('AgentId')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('ComputerName') or '')

            device.hostname = device_raw.get('ComputerName')
            device.first_seen = parse_date(device_raw.get('InstallTime'))

            device.add_agent_version(agent=AGENT_NAMES.cyberark_epm,
                                     version=device_raw.get('AgentVersion'))

            device.figure_os(os_string=device_raw.get('platform'))

            try:
                device.pc_type = device_raw.get('ComputerType')
            except Exception:
                pass

            self._fill_cyberark_epm_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CyberarkEpm Device for {device_raw}')
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
                logger.exception(f'Problem with fetching CyberarkEpm Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
