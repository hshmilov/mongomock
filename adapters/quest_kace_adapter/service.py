import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from quest_kace_adapter.connection import QuestKaceConnection
from quest_kace_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class QuestKaceAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        asset_tag = Field(str, 'Asset Tag')
        chassis_type = Field(str, 'Chassis Type')
        agent_version = Field(str, 'Agent Version')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with QuestKaceConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                     password=client_config['password'],
                                     username=client_config['username'],
                                     orgname=client_config.get('orgname')) as connection:
                return connection
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
        The schema QuestKaceAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'QuestKace Domain',
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
                    'name': 'orgname',
                    'title': 'Organization Name',
                    'type': 'string'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('Id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('Name') or '')
            device.hostname = device_raw.get('Name')
            device.asset_tag = device_raw.get('Asset_tag')
            device.bios_serial = device_raw.get('Bios_serial_number')
            device.bios_version = device_raw.get('Bios_version')
            device.chassis_type = device_raw.get('Chassis_type')
            device.agent_version = device_raw.get('Client_version')
            if is_domain_valid(device_raw.get('Cs_domain')):
                device.domain = device_raw.get('Cs_domain')
            device.device_manufacturer = device_raw.get('Cs_manufacturer')
            device.device_model = device_raw.get('Cs_model')

            try:
                device.figure_os(device_raw.get('Os_name'))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            try:
                device.last_seen = parse_date(device_raw.get('Last_sync'))
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            try:
                mac = device_raw.get('Mac')
                if not mac:
                    mac = None
                ips = None
                ip = device_raw.get('Ip')
                if ip and isinstance(ip, str):
                    ips = ip.split(',')
                if mac or ips:
                    device.add_nic(mac=mac, ips=ips)
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            try:
                user = device_raw.get('User')
                if user and isinstance(user, str):
                    device.last_used_users = user.split(',')
            except Exception:
                logger.exception(f'Problem adding user to {device_raw}')
            try:
                software_list = device_raw.get('Software')
                if not isinstance(software_list, list):
                    software_list = []
                for sofware_data in software_list:
                    try:
                        # pylint: disable=line-too-long
                        if ('Update for' in sofware_data.get('DISPLAY_NAME') or 'Hotfix for' in sofware_data.get('DISPLAY_NAME'))\
                                and 'KB' in sofware_data.get('DISPLAY_NAME'):
                            device.add_security_patch(patch_description=sofware_data.get('DISPLAY_NAME'),
                                                      installed_on=parse_date(sofware_data.get('INSTALL_DATE')))
                        else:
                            device.add_installed_software(name=sofware_data.get('DISPLAY_NAME'),
                                                          version=sofware_data.get('DISPLAY_VERSION'))
                    except Exception:
                        logger.exception(f'Problem with software {sofware_data}')
            except Exception:
                logger.exception(f'Problem with sw for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Device42 Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
