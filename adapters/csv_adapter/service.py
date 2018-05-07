import csv
import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file


class CsvAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _connect_client(self, client_config):
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        csv_data = self._grab_file_contents(client_data['csv']).decode('utf-8')
        return csv.DictReader(csv_data.splitlines(), dialect=csv.Sniffer().sniff(csv_data[:1024]))

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "user_id",
                    "title": "User ID",
                    "type": "string"
                },
                {
                    "name": "csv",
                    "title": "CSV File",
                    "description": "The binary contents of the csv",
                    "type": "file"
                },
            ],
            "required": [
                "user_id",
                "csv",
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        if "Serial" not in raw_data.fieldnames:
            logger.error(f"Bad fields names{str(raw_data.fieldnames)}")
            return
        for device_raw in raw_data:
            try:
                device = self._new_device_adapter()
                serial = device_raw.get("Serial")
                device.id = serial
                if device.id is None or device.id == "":
                    continue
                device.device_serial = serial
                device.name = device_raw.get("Name")
                mac_addresses = device_raw.get("MAC Address", "").split(',')
                for mac_address in mac_addresses:
                    if mac_address != "":
                        device.add_nic(mac_address, None)
                os = device_raw.get("OS")
                if os is not None:
                    device.figure_os(os)
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem adding device: {str(device_raw)}")

    def _correlation_cmds(self):
        """
        Figure out the Serial on the computer
        """
        return {
            "Windows": 'wmic bios get serialnumber',
            "OS X": 'system_profiler SPHardwareDataType | grep "Serial"'
        }

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        correlation_cmd_result = correlation_cmd_result.strip()
        if os_type == 'Windows':
            return correlation_cmd_result.splitlines()[1].strip()
        elif os_type == 'OS X':
            return correlation_cmd_result[correlation_cmd_result.index(':') + 1:].strip()

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
