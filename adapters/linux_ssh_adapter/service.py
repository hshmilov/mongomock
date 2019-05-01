import copy
import datetime
import logging

import gridfs
from bson import ObjectId

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.linux_ssh.consts import (DEFAULT_NETWORK_TIMEOUT,
                                              DEFAULT_POOL_SIZE, DEFAULT_PORT,
                                              HOSTNAME, IS_SUDOER, PASSWORD,
                                              PORT, PRIVATE_KEY, ACTION_SCHEMA,
                                              USERNAME)
from axonius.clients.linux_ssh.data import LinuxDeviceAdapter
from axonius.consts.plugin_consts import DEVICE_CONTROL_PLUGIN_NAME
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from linux_ssh_adapter.client_id import get_client_id
from linux_ssh_adapter.connection import LinuxSshConnection
from linux_ssh_adapter.execution import LinuxSshExectionMixIn

logger = logging.getLogger(f'axonius.{__name__}')


class LinuxSshAdapter(LinuxSshExectionMixIn, AdapterBase, Configurable):
    MyDeviceAdapter = LinuxDeviceAdapter

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return LinuxSshConnection.test_reachability(client_config[HOSTNAME], client_config.get(PORT, DEFAULT_PORT))

    def _prepare_client_config(self, client_config):
        client_config = copy.copy(client_config)
        if PORT not in client_config:
            client_config[PORT] = DEFAULT_PORT
        if PASSWORD not in client_config:
            client_config[PASSWORD] = ''
        if IS_SUDOER not in client_config:
            client_config[IS_SUDOER] = True
        key = client_config.get(PRIVATE_KEY)
        client_config[PRIVATE_KEY] = self._grab_file_contents(key) if key else None

        return client_config

    def _grab_file_contents(self, field_data, stored_locally=True):
        # XXX: Ugly hack to handle EC
        try:
            return super()._grab_file_contents(field_data, stored_locally)
        except gridfs.errors.NoFile:
            db_name = DEVICE_CONTROL_PLUGIN_NAME
            return gridfs.GridFS(self._get_db_connection()[db_name]).get(ObjectId(field_data['uuid'])).read()

    def _connect_client(self, client_config):
        try:
            client_config = self._prepare_client_config(client_config)
            with LinuxSshConnection(hostname=client_config[HOSTNAME],
                                    port=client_config[PORT],
                                    username=client_config[USERNAME],
                                    password=client_config[PASSWORD],
                                    key=client_config[PRIVATE_KEY],
                                    is_sudoer=client_config[IS_SUDOER],
                                    timeout=self._timeout) as connection:
                return connection
        except Exception as e:
            message = 'Error connecting to client {0}, reason: {1}'.format(
                client_config['host_name'], str(e)
            )
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
            yield from ((client_name, x) for x in client_data.get_commands(self._md5_files_list))

    @staticmethod
    def _clients_schema():
        """
        The schema LinuxSshAdapter expects from configs

        :return: JSON scheme
        """
        schema = copy.deepcopy(ACTION_SCHEMA)
        schema['items'].insert(0, {'name': HOSTNAME, 'title': 'Host Name', 'type': 'string'})
        schema['required'].insert(0, HOSTNAME)

        return schema

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
        items = [
            {'name': 'md5_files_list',
             'title': 'MD5 Files List',
             'type': 'string'},
            {'name': 'timeout',
             'title': 'Network Timeout',
             'type': 'integer',
             'default': DEFAULT_NETWORK_TIMEOUT},
            {'name': 'pool_size',
             'title': 'SSH Scan Pool Size',
             'type': 'integer',
             'default': DEFAULT_POOL_SIZE}
        ]
        return {
            'items': items,
            'required': ['pool_size', 'timeout'],
            'pretty_name': 'Linux SSH Configuration',
            'type': 'array',
        }

    @classmethod
    def _db_config_default(cls):
        return {'md5_files_list': None,
                'pool_size': DEFAULT_POOL_SIZE,
                'timeout': DEFAULT_NETWORK_TIMEOUT}

    def _on_config_update(self, config):
        self._md5_files_list = config['md5_files_list']
        self._pool_size = config['pool_size'] or DEFAULT_POOL_SIZE
        self._timeout = config['timeout'] or DEFAULT_NETWORK_TIMEOUT
