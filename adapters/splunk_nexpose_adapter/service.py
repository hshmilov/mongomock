import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_exceptions import ClientConnectionException
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from splunk_nexpose_adapter.connection import SplunkConnection


class SplunkNexposeAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)
        self.max_log_history = int(self.config['DEFAULT']['max_log_history'])  # in days

    def _get_client_id(self, client_config):
        return '{}:{}'.format(client_config['host'], client_config['port'])

    def _connect_client(self, client_config):
        has_token = bool(client_config.get('token'))
        maybe_has_user = bool(client_config.get('username')) or bool(client_config.get('password'))
        has_user = bool(client_config.get('username')) and bool(client_config.get('password'))
        if has_token and maybe_has_user:
            msg = f"Different logins for Splunk [Nexpose] domain " \
                  f"{client_config.get('host')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        elif maybe_has_user and not has_user:
            msg = f"Missing credentials for Splunk [Nexpose] domain " \
                  f"{client_config.get('host')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        try:
            client_config['password'] = self.decrypt_password(client_config['password'])
            connection = SplunkConnection(**client_config)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Splunk domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Splunk connection

        :return: A json with all the attributes returned from the Splunk Server
        """
        with client_data:
            return list(client_data.get_nexpose_devices(f'-{self.max_log_history}d'))

    def _clients_schema(self):
        """
        The schema SplunkNexposeAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "host",
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": "port",
                    "title": "Port",
                    "type": "number"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "token",
                    "title": "API Token",
                    "type": "string"
                }
            ],
            "required": [
                "host",
                "port"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._new_device_adapter()
            device.hostname = device_raw.get('hostname', '')
            device.figure_os(device_raw.get('version', device_raw.get('os')))
            device.add_nic(device_raw.get('mac'), [device_raw.get('ip')])
            device.id = device_raw['asset_id']
            device.scanner = True
            device.set_raw(device_raw)
            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
