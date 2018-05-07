import logging
logger = logging.getLogger(f"axonius.{__name__}")
import csv
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from axonius.utils.parsing import make_dict_from_csv


class ObserveitCsvAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        client_version = Field(str, 'Client Version')
        client_status = Field(str, 'Client Status')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _connect_client(self, client_config):
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        return {'csv': make_dict_from_csv(self._grab_file_contents(client_data['csv']).decode('utf-8')), 'domain': client_data['domain']}

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
                    "type": "file"
                },
                {
                    "name": "domain",
                    "title": "Domain Name",
                    "type": "string",

                },
            ],
            "required": [
                "user_id",
                "csv",
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        domain = raw_data['domain']
        # We need the domain in the adapter to get correlations
        if domain is None or domain == "":
            logger.error("No domain")
            return
        if "Endpoint Name" not in raw_data['csv'].fieldnames:
            logger.error(f"Bad fields names{str(raw_data.fieldnames)}")
            return
        for device_raw in raw_data['csv']:
            try:
                device = self._new_device_adapter()
                device.hostname = device_raw.get("Endpoint Name") + "." + domain
                device.id = device.hostname
                device.client_status = device_raw.get("Status")
                device.client_version = device_raw.get("Version")
                device.figure_os(device_raw.get("OS Type", "") + " " + device_raw.get("OS Version", ""))
                device.last_seen = parse_date(device_raw.get("Last Heartbeat Date", "") +
                                              " " + device_raw.get("Last Heartbeat Time", ""))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem adding device: {str(device_raw)}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
