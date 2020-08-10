import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from symantec_dcs_adapter.connection import SymantecDcsConnection
from symantec_dcs_adapter.client_id import get_client_id
from symantec_dcs_adapter.consts import DCS_DEFAULT_PORT, UMC_DEFAULT_PORT
from symantec_dcs_adapter.structures import SymantecDcsDeviceInstance, SecurityGroup

logger = logging.getLogger(f'axonius.{__name__}')


# pylint:disable=logging-format-interpolation


class SymantecDcsAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(SymantecDcsDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _parse_int(value):
        try:
            return int(value) if value else None
        except Exception as e:
            logger.warning(f'Failed to parse {value} as int: {str(e)}')
        return None

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('umc_domain'),
                                                port=client_config['umc_port'],
                                                https_proxy=client_config.get('https_proxy')) and \
            RESTConnection.test_reachability(client_config.get('domain'),
                                             port=client_config['port'],
                                             https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = SymantecDcsConnection(domain=client_config['domain'],
                                           umc_domain=client_config['umc_domain'],
                                           port=client_config['port'],
                                           umc_port=client_config['umc_port'],
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
    def _clients_schema():
        """
        The schema SymantecDcsAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'DCS Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'umc_domain',
                    'title': 'UMC Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'DCS Port',
                    'type': 'integer',
                    'default': DCS_DEFAULT_PORT
                },
                {
                    'name': 'umc_port',
                    'title': 'UMC Port',
                    'type': 'integer',
                    'default': UMC_DEFAULT_PORT
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
                'umc_domain',
                'port',
                'umc_port',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _fill_symantec_dcs_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.category_name = device_raw.get('categoryname')
            device.manager_name = device_raw.get('managername')
            device.agent_status = device_raw.get('agentstatus')
            device.guid = device_raw.get('guid')
            device.element_type = device_raw.get('elementtype')

            security_group = SecurityGroup()
            security_group.id = self._parse_int(device_raw.get('securitygrouprid'))
            security_group.user_name = device_raw.get('securitygroupusername')
            security_group.description = device_raw.get('securitygroupdescription')
            security_group.create_date = parse_date(device_raw.get('securitygroupcreatetime'))
            security_group.state = device_raw.get('securitygroupstate')
            security_group.name = device_raw.get('securitygroupname')
            device.security_group = security_group

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('rid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('guid') or '')

            device.name = device_raw.get('name')
            device.hostname = device_raw.get('hostname')
            device.domain = device_raw.get('domain_name')
            device.email = device_raw.get('email')
            device.description = device_raw.get('computer_descr')

            last_contact = parse_date(device_raw.get('lastcontact'))
            last_event = parse_date(device_raw.get('lastevent'))
            if last_contact and last_event:
                last_seen = max(last_contact, last_event)
            else:
                last_seen = last_contact or last_event
            device.last_seen = last_seen
            device.first_seen = parse_date(device_raw.get('servicestart'))

            os_string = device_raw.get('ostype')
            device.figure_os(os_string=os_string)

            ips = device_raw.get('ipaddress') or []
            if isinstance(ips, str):
                ips = [ips]
            macs = device_raw.get('macaddr') or []
            if isinstance(macs, str):
                macs = [macs]
            device.add_ips_and_macs(macs=macs,
                                    ips=ips)

            self._fill_symantec_dcs_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching SymantecDcs Device for {device_raw}')
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
                logger.exception(f'Problem with fetching SymantecDcs Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Manager, AdapterProperty.Agent]
