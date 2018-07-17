import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter, ListField, format_ip, JsonStringFormat
from axonius.utils.files import get_local_config_file
from axonius.adapter_exceptions import ClientConnectionException
from collections import defaultdict
from junos_adapter.client import JunOSClient
import re


def is_valid_mac(x):
    return re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", x.lower())


class JunosAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        interfaces = ListField(str, 'Interfaces', description='A list of interfaces that the device has')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        if not client_config.get('port'):
            client_config['port'] = 22

        return ':'.join([client_config['host'], str(client_config['port'])])

    def _connect_client(self, client_config):
        try:
            with JunOSClient(**client_config) as client:
                return client
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client):
        with client:
            # return arp table
            return client.query_arp_table()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": 'host',
                    "title": 'Host Name',
                    "type": 'string'
                },
                {
                    "name": 'username',
                    "title": 'User Name',
                    "type": 'string',
                    "description": "Username for SSH"
                },
                {
                    "name": 'password',
                    "title": "Password",
                    "type": 'string',
                    "format": 'password',
                    "description": "Password for SSH"
                },
                {
                    "name": 'port',
                    "title": 'Protocol port',
                    "type": 'integer',
                    "description": "SSH Port (Default: 22)"
                },
            ],
            "required": [
                "username",
                "password",
                "host",
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        raw_devices = {}
        for raw_line in raw_data:
            try:
                raw_line = raw_line.split()
                flags = 'none'
                mac_addr, ip_addr, name, interface = raw_line[0], raw_line[1], raw_line[2], raw_line[3]
                if len(raw_line) > 4:
                    flags = raw_line[4]

                if not is_valid_mac(mac_addr):
                    logger.error('Invalid mac addr - skipping device {raw_line}')
                    continue

                # If this device isn't already set up, lets set a default dict that represents it
                if mac_addr not in raw_devices:
                    raw_devices[mac_addr] = defaultdict(set)

                raw_devices[mac_addr]['mac_addr'] = mac_addr
                raw_devices[mac_addr]['related_ips'].add(ip_addr)
                raw_devices[mac_addr]['name'].add(name)
                raw_devices[mac_addr]['interface'].add(interface)
                raw_devices[mac_addr]['flags'].add(flags)
            except Exception:
                logger.exception(f"Error parsing line {raw_data}, bypassing")

        # Now go over all devices and create a deviceadapter for them
        for raw_device in raw_devices.values():
            device = self._new_device_adapter()
            device.id = raw_device['mac_addr']
            device.add_related_ips(list(raw_device['related_ips']))
            device.interfaces = list(raw_device['interface'])

            device.add_nic(mac=raw_device['mac_addr'])

            device.set_raw({
                "mac_addr": device.id,
                "related_ips": device.related_ips,
                "name": list(raw_device['name']),
                "interface": list(raw_device['interface']),
                "flags": list(raw_device['flags'])
            })

            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
