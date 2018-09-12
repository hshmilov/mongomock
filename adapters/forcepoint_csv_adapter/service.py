import logging
logger = logging.getLogger(f'axonius.{__name__}')
import csv
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from axonius.adapter_exceptions import GetDevicesError
from axonius.utils.parsing import make_dict_from_csv


class ForcepointCsvAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        client_version = Field(str, 'Client Version')
        client_status = Field(str, 'Client Status')
        endpoint_server = Field(str, 'Endpoint Server')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        filedata = self._grab_file_contents(client_data['csv'])
        csv_data = filedata.decode('utf-8')
        return make_dict_from_csv(csv_data)

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
                    "type": "file",

                },
            ],
            "required": [
                "user_id",
                "csv",
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        if "Hostname" not in raw_data.fieldnames:
            logger.error(f"Bad fields names{str(raw_data.fieldnames)}")
            raise GetDevicesError(f"Bad fields names{str(raw_data.fieldnames)}")
        for device_raw in raw_data:
            try:
                device = self._new_device_adapter()
                device.hostname = device_raw.get("Hostname")
                device.id = device.hostname
                device.client_status = device_raw.get("Client Status")
                device.client_version = device_raw.get("Client Installation Version")
                device.endpoint_server = device_raw.get("Endpoint Server")
                device.add_nic(None, device_raw.get("IP Address", "").split(','))
                device.last_used_users = device_raw.get("Logged-in Users", "").split(',')
                device.last_seen = parse_date(str(device_raw.get("Last Update", "")))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem adding device: {str(device_raw)}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
