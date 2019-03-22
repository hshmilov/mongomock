import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
from axonius.fields import ListField
from linux_ssh_adapter.client_id import get_client_id
from linux_ssh_adapter.connection import LinuxSshConnection
from linux_ssh_adapter.consts import (DEFAULT_PORT, HOSTNAME, IS_SUDOER,
                                      PASSWORD, PORT, PRIVATE_KEY, USERNAME)

logger = logging.getLogger(f'axonius.{__name__}')


class LinuxSshAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        md5_files_list = ListField(str, 'MD5 Files List')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return LinuxSshConnection.test_reachability(client_config[HOSTNAME], client_config.get(PORT, DEFAULT_PORT))

    def _connect_client(self, client_config):
        if PORT not in client_config:
            client_config[PORT] = DEFAULT_PORT
        if PASSWORD not in client_config:
            client_config[PASSWORD] = ''
        if IS_SUDOER not in client_config:
            client_config[IS_SUDOER] = True

        try:
            key = client_config.get(PRIVATE_KEY)
            if key:
                key = self._grab_file_contents(key)

            with LinuxSshConnection(hostname=client_config[HOSTNAME],
                                    port=client_config[PORT],
                                    username=client_config[USERNAME],
                                    password=client_config[PASSWORD],
                                    key=key,
                                    is_sudoer=client_config[IS_SUDOER]) as connection:
                return connection
        except Exception as e:
            message = 'Error connecting to client with host_name {0}, reason: {1}'.format(
                client_config['host_name'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific host_name

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from ((client_name, x) for x in client_data.get_commands(self.__md5_files_list))

    @staticmethod
    def _clients_schema():
        """
        The schema LinuxSshAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': HOSTNAME,
                    'title': 'Host Name',
                    'type': 'string'
                },
                {
                    'name': USERNAME,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password',
                    'default': ''
                },
                {
                    'name': PRIVATE_KEY,
                    'title': 'Private Key',
                    'description': 'SSH Private key for authentication',
                    'type': 'file'
                },
                {
                    'name': PORT,
                    'title': 'SSH Port',
                    'type': 'integer',
                    'default': DEFAULT_PORT,
                    'description': 'Protocol Port'
                },
                {
                    'name': IS_SUDOER,
                    'title': 'Sudoer',
                    'description': 'Use sudo to execute privileged commands. ' +
                                   'If left unchecked, privileged commands may fail.',
                    'type': 'bool',
                    'default': True
                },
            ],
            'required': [
                HOSTNAME,
                USERNAME,
                IS_SUDOER,
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        device = self._new_device_adapter()

        # we are running on the endpoint, so the last seen is right now
        device.last_seen = datetime.datetime.now()

        for client_name, command in devices_raw_data:
            command.to_axonius(client_name, device)
        yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Manager, AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'md5_files_list',
                    'title': 'MD5 Files List',
                    'type': 'string'
                }
            ],
            'required': [
            ],
            'pretty_name': 'Linux SSH Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'md5_files_list': None
        }

    def _on_config_update(self, config):
        md5_files_list = config['md5_files_list']
        if md5_files_list:
            self.__md5_files_list = md5_files_list.split(',')
        else:
            self.__md5_files_list = None
