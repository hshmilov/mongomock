"""
CSVAdapter.py: An adapter for CSV parsing.
"""
import csv

from axonius.adapter_base import AdapterBase
from axonius.device import Device


class CSVAdapter(AdapterBase):
    class MyDevice(Device):
        pass

    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _connect_client(self, client_config):
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        return {"data": list(csv.reader(bytearray(client_data['csv']).decode('ascii').splitlines()))}

    def _clients_schema(self):
        return {
            "properties": {
                "user_id": {
                    "type": "string"
                },
                "csv": {
                    "type": "array",
                    "title": "The binary contents of the csv",
                    "description": "bytes",
                    "items": {
                        "type": "integer",
                        "default": 0,
                    }
                },
            },
            "required": [
                "user_id",
                "csv",
            ],
            "type": "object"
        }

    def _parse_raw_data(self, raw_data):
        for asset_name, serial in raw_data['data']:
            device = self._new_device()
            device.name = asset_name
            device.id = serial
            device.set_raw({"name": asset_name, "id": serial})
            yield device

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
