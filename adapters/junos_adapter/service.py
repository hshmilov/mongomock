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
            # Make sure device has valid mac addr
            try:
                if raw_line['mac_address'] == None:
                    continue
                else:
                    mac_address = raw_line['mac_address']
                if not is_valid_mac(mac_address):
                    logger.error('Invalid mac addr - skipping device {raw_line}')
                    continue
            except BaseException:
                logger.error("Skipping device {raw_line} because it does not contain field for mac_address.")
                continue
            try:
                # If this device isn't already set up, lets set a default dict that represents it
                if mac_address not in raw_devices:
                    raw_devices[mac_address] = defaultdict(set)

                raw_devices[mac_address]['mac_addr'] = mac_address
                raw_devices[mac_address]['related_ips'].add(raw_line['ip_address'])
                raw_devices[mac_address]['interface'].add(raw_line['interface_name'])
            except Exception:
                logger.exception(f"Error parsing line {raw_data}, bypassing")

        # Now go over all devices and create a deviceadapter for them
        for raw_device in raw_devices.values():
            device = self._new_device_adapter()
            device.id = raw_device['mac_addr']
            device.set_related_ips(list(raw_device['related_ips']))
            device.interfaces = list(raw_device['interface'])

            device.add_nic(mac=raw_device['mac_addr'])

            device.set_raw({
                "mac_addr": device.id,
                "related_ips": device.related_ips.ips,
                "interface": device.interfaces,
            })

            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
