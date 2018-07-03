import logging
logger = logging.getLogger(f"axonius.{__name__}")
import xml.etree.ElementTree as ET

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import AdapterException, ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, format_ip, JsonStringFormat
from axonius.utils.files import get_local_config_file
from juniper_adapter import consts
from juniper_adapter.client import JuniperClient
from axonius.fields import Field, ListField
from collections import defaultdict


class JuniperAdapter(AdapterBase):
    """
    Connects axonius to Juniper devices
    """

    class MyDeviceAdapter(DeviceAdapter):
        interfaces = ListField(str, 'Interface')
        device_type = Field(str, 'Device Type')
        related_ips = ListField(str, 'Realated IPs', converter=format_ip, json_format=JsonStringFormat.ip,
                                description='A list of ips that are routed through the device')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": consts.JUNIPER_HOST,
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": consts.USER,  # The user needs System Configuration Read Privileges.
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": consts.PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                consts.USER,
                consts.PASSWORD,
                consts.JUNIPER_HOST,
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        raw_arp_devices = {}
        for device_type, juno_device in raw_data:
            if device_type == 'Juniper Device':
                try:
                    device = self._new_device_adapter()
                    device.device_type = device_type
                    device.name = juno_device.name
                    device.device_serial = str(juno_device.serialNumber)
                    device.id = device.device_serial
                    device.figure_os("junos")
                    device.device_model_family = str(juno_device.deviceFamily)
                    device.device_model = f"{str(juno_device.platform)} {str(juno_device.OSVersion)}"
                    ip_address = str(juno_device.ipAddr)
                    device.add_nic(None, [ip_address] if ip_address is not None else None)
                    device.set_raw({})
                    yield device
                except Exception:
                    logger.exception(f"Got problems with {juno_device.name}")

            elif device_type == 'Arp Device':
                xml_juno_device = ET.fromstring(juno_device)
                if 'rpc-reply' not in xml_juno_device.tag or 'arp-table-information' not in xml_juno_device[0].tag:
                    logger.error(f"Bad rpc reply from {juno_device}")
                    continue
                for xml_arp_item in xml_juno_device[0]:
                    try:
                        if 'arp-table-entry' not in xml_arp_item.tag:
                            continue
                        mac_address = None
                        ip_address = None
                        name = None
                        interface = None
                        for xml_arp_property in xml_arp_item:
                            if 'mac-address' in xml_arp_property.tag:
                                mac_address = xml_arp_property.text
                            if 'ip-address' in xml_arp_property.tag:
                                ip_address = xml_arp_property.text
                            if 'hostname' in xml_arp_property.tag:
                                name = xml_arp_property.text
                            if 'interface-name' in xml_arp_property.tag:
                                interface = xml_arp_property.text
                        if mac_address is None:
                            continue
                        if mac_address not in raw_arp_devices:
                            raw_arp_devices[mac_address] = defaultdict(set)
                        raw_arp_devices[mac_address]['mac_address'] = mac_address
                        if ip_address is not None:
                            raw_arp_devices[mac_address]['related_ips'].add(ip_address)
                        if interface is not None:
                            raw_arp_devices[mac_address]['interface'].add(interface)
                        if name is not None:
                            raw_arp_devices[mac_address]['name'].add(name)
                    except Exception:
                        logger.exception(f"Got bad arp item with missing data in {arp_item}")
        for raw_arp_device in raw_arp_devices.values():
            try:
                device = self._new_device_adapter()
                device.id = raw_arp_device['mac_address']
                device.add_nic(raw_arp_device['mac_address'], None)
                device.device_type = 'Arp Device'
                try:
                    device.related_ips = list(raw_arp_device['related_ips'])
                except Exception:
                    logger.exception(f"Problem getting IPs in {raw_arp_device}")
                try:
                    device.interfaces = list(raw_arp_device['interface'])
                except Exception:
                    logger.exception(f"Problem getting interface in {raw_arp_device}")
                try:
                    device.set_raw({'mac': raw_arp_device['mac_address'],
                                    'names': list(raw_arp_device['names']),
                                    'interfaces': list(raw_arp_device['interface']),
                                    'ips': list(raw_arp_device['related_ips'])})
                except Exception:
                    logger.exception(f"Problem setting raw in {raw_arp_device}")
                    device.set_raw({})
                yield device
            except Exception:
                logger.exception(f"Problem with pasrsing arp device {raw_arp_device}")

    def _query_devices_by_client(self, client_name, client_data):
        try:
            assert isinstance(client_data, JuniperClient)
            return client_data.get_all_devices()
        except Exception:
            logger.exception(f'Failed to get all the devices from the client: {client_data[consts.JUNIPER_HOST]}')
            raise AdapterException(f'Failed to get all the devices from the client: {client_data[consts.JUNIPER_HOST]}')

    def _get_client_id(self, client_config):
        return f"{client_config[consts.USER]}@{client_config[consts.JUNIPER_HOST]}"

    def _connect_client(self, client_config):
        try:
            return JuniperClient(url=f"https://{client_config[consts.JUNIPER_HOST]}",
                                 username=client_config[consts.USER],
                                 password=client_config[consts.PASSWORD])
        except Exception:
            logger.exception(
                f'Failed to connect to Juniper provider using this host {client_config[consts.JUNIPER_HOST]}')
            raise ClientConnectionException(
                f'Failed to connect to Juniper provider using this host {client_config[consts.JUNIPER_HOST]}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
