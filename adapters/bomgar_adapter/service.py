import logging
logger = logging.getLogger(f"axonius.{__name__}")
import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, JsonStringFormat
from axonius.utils.parsing import format_ip
from axonius.utils.files import get_local_config_file
from bomgar_adapter.client import BomgarConnection
from bomgar_adapter.exceptions import BomgarException


class BomgarAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Bomgar Device Type')
        public_display_name = Field(str, 'Bomgar public display name')
        user_id = Field(int, 'Bomgar User ID')
        username = Field(str, 'Bomgar User Name')
        created_timestamp = Field(datetime.datetime, 'Created Timestamp')
        last_session_representative_username = Field(str, 'Bomgar Last Session Representative User Name')
        last_session_start = Field(datetime.datetime, 'Last Session Start Timestamp')
        last_session_start_method = Field(str, 'Last Session Start Method')
        public_ip = Field(str, 'Public IP', converter=format_ip, json_format=JsonStringFormat.ip)

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return f"{client_config['domain']}:{client_config['client_id']}"

    def _connect_client(self, client_config):
        try:
            connection = BomgarConnection(client_config["domain"], client_config["client_id"],
                                          self.decrypt_password(client_config["client_secret"]))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except BomgarException as e:
            message = f"Error connecting to client {self._get_client_id(client_config)}, reason: {str(e)}"
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        assert isinstance(client_data, BomgarConnection)
        with client_data:
            return client_data.get_clients_history()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "Domain",
                    "title": "Domain",
                    "type": "string"
                },
                {
                    "name": "client_id",
                    "title": "Client ID",
                    "type": "string"
                },
                {
                    "name": "client_secret",
                    "title": "Client Secret",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                "domain",
                "client_id",
                "client_secret"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for hostname, device_raw in devices_raw_data.items():
            device = self._new_device_adapter()
            device.hostname = device_raw['hostname']
            device.id = device_raw['hostname']
            device.figure_os(device_raw['operating_system'])
            device.created_timestamp = datetime.datetime.fromtimestamp(device_raw['created_timestamp'])
            device.device_type = device_raw['device_type']
            device.last_seen = datetime.datetime.fromtimestamp(device_raw['last_seen'])
            if device_raw['device_type'] == 'representative':
                device.public_display_name = device_raw.get('public_display_name')
                device.user_id = device_raw.get('user_id')
                device.username = device_raw.get('username')
            else:
                device.last_session_representative_username = device_raw.get('last_session_representative_username')
                device.last_session_start = datetime.datetime.fromtimestamp(device_raw.get('last_session_start'))
                device.last_session_start_method = device_raw.get('last_session_start_method')
            device.add_nic(None, [device_raw['private_ip']])
            device.public_ip = device_raw['public_ip']
            device.set_raw(device_raw)
            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
