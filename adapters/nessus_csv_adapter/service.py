import logging
logger = logging.getLogger(f'axonius.{__name__}')
import csv
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import make_dict_from_csv
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.adapter_exceptions import GetDevicesError


class NessusCsvScan(SmartJsonClass):
    plugin_id = Field(str, "Plugin ID")
    plugin_name = Field(str, "Plugin Name")
    cve = Field(str, "CVE")
    cvss = Field(str, "CVSS")
    risk = Field(str, "Risk")
    protocol = Field(str, "Protocol")
    port = Field(str, "Port")


class NessusCsvAdapter(ScannerAdapterBase):
    """ An adapter for Tenable's Nessus Vulnerability scanning platform. """

    class MyDeviceAdapter(DeviceAdapter):
        scans = ListField(NessusCsvScan, "Scan Data")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        return make_dict_from_csv(self._grab_file_contents(client_data['csv']).decode('utf-8'))

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
            ],
            "required": [
                "user_id",
                "csv",
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        if "Host" not in raw_data.fieldnames:
            logger.error(f"Bad fields names{str(raw_data.fieldnames)}")
            raise GetDevicesError(f"Bad fields names{str(raw_data.fieldnames)}")
        raw_data = list(raw_data)
        ip_addresses = list(set([host_scan_raw.get("Host") or "" for host_scan_raw in raw_data]))
        ip_addresses_data_dict = {}
        if "" in ip_addresses:
            ip_addresses.remove("")
        for ip_address in ip_addresses:
            ip_addresses_data_dict[ip_address] = []
        for scan_raw in raw_data:
            try:
                ip_addresses_data_dict[scan_raw["Host"]].append(scan_raw)
            except Exception:
                logger.exception(f"Problems with scan_raw {scan_raw}")
        for ip_address in ip_addresses_data_dict:
            try:
                device = self._new_device_adapter()
                device.add_nic(None, [ip_address])
                device.scans = []
                device.software_cves = []
                scans_raw = ip_addresses_data_dict[ip_address]
                for scan_raw in scans_raw:
                    try:
                        new_scan = NessusCsvScan()
                        new_scan.plugin_name = scan_raw.get("Name")
                        new_scan.port = scan_raw.get("Port")
                        new_scan.protocol = scan_raw.get("Protocol")
                        new_scan.risk = scan_raw.get("Risk")
                        new_scan.cvss = scan_raw.get("CVSS")
                        new_scan.plugin_id = scan_raw.get("Plugin ID")
                        new_scan.cve = scan_raw.get("CVE")
                        device.add_vulnerable_software(scan_raw.get('CVE'))
                        device.scans.append(new_scan)
                    except Exception:
                        logger.exception(f"IP {ip_address} got problem adding scan_raw {scan_raw}")
                device.set_raw({})
                yield device
            except Exception:
                logger.exception(f"Problem adding device: {str(ip_address)}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
