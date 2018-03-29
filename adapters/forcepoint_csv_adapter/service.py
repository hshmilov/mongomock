import csv

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.parsing_utils import parse_date


class ForcepointCsvAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        client_version = Field(str, 'Client Version')
        client_status = Field(str, 'Client Status')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _connect_client(self, client_config):
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        return {"data": list(csv.reader(bytearray(client_data['csv']).decode('ascii').splitlines()))}

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "user_id",
                    "title": "CSV File ID",
                    "type": "string"
                },
                {
                    "name": "csv",
                    "title": "CSV File",
                    "description": "The binary contents of the csv",
                    "format": "bytes",
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "default": 0,
                    }
                },
            ],
            "required": [
                "user_id",
                "csv",
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        if raw_data['data'][0] != ["Hostname", "IP Address", "Logged-in Users", "Last Update", "Profile Name", "Synced",
                                   "Discovery Status", "Client Status", "Client Installation Version"]:
            return
        for host_name, ip_address,\
                logged_in_users,\
                last_update,\
                profile_name,\
                synced, discovery_status,\
                client_status,\
                version in raw_data['data'][1:]:
            device = self._new_device_adapter()
            device.hostname = host_name
            device.id = host_name
            device.client_status = client_status
            device.client_version = version
            device.add_nic(None, ip_address.split(','), self.logger)
            device.last_used_users = [logged_in_users]
            device.last_seen = parse_date(last_update)
            device.set_raw({"last_update": last_update,
                            "logged_in_users": logged_in_users,
                            "host_name": host_name,
                            "ip_address": ip_address,
                            "profile_name": profile_name,
                            "synced": synced, "discovery_status": discovery_status,
                            "client_status": client_status, "client_installation version": version})
            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Manager, AdapterProperty.Agent]
