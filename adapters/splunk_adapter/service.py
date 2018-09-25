import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from splunk_adapter.connection import SplunkConnection
from axonius.fields import Field

logger = logging.getLogger(f'axonius.{__name__}')


class SplunkAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        vlan = Field(str, 'Vlan')
        port = Field(str, 'port')
        cisco_device = Field(str, 'Cisco Device')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)
        self.max_log_history = int(self.config['DEFAULT']['max_log_history'])  # in days

    def _get_client_id(self, client_config):
        return '{}:{}'.format(client_config['host'], client_config['port'])

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("host"), client_config.get("port"))

    def _connect_client(self, client_config):
        has_token = bool(client_config.get('token'))
        maybe_has_user = bool(client_config.get('username')) or bool(client_config.get('password'))
        has_user = bool(client_config.get('username')) and bool(client_config.get('password'))
        if has_token and maybe_has_user:
            msg = f"Different logins for Splunk domain " \
                  f"{client_config.get('host')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        elif maybe_has_user and not has_user:
            msg = f"Missing credentials for Splunk [] domain " \
                  f"{client_config.get('host')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        try:
            connection = SplunkConnection(**client_config)
            with connection:
                pass
            return connection
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Splunk domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Splunk connection

        :return: A json with all the attributes returned from the Splunk Server
        """
        with client_data:
            yield from client_data.get_devices(f'-{self.max_log_history}d')

    def _clients_schema(self):
        """
        The schema SplunkAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "host",
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": "port",
                    "title": "Port",
                    "type": "integer",
                    "format": "port"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "token",
                    "title": "API Token",
                    "type": "string"
                }
            ],
            "required": [
                "host",
                "port"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        macs_set = set()
        dhcp_macs_set = set()
        for device_raw, device_type in devices_raw_data:
            try:
                device = self._new_device_adapter()
                if 'DHCP' in device_type:
                    mac = device_raw.get('mac')
                    hostname = device_raw.get('hostname')
                    if not mac and not hostname:
                        logger.warning(f'Bad device no mac {device_raw}')
                        continue

                    if mac in dhcp_macs_set:
                        continue
                    if mac:
                        device.id = mac + device_type
                    else:
                        device.id = hostname + device_type
                    device.hostname = hostname
                    ip = device_raw.get('ip')
                    macs = []
                    if len(mac) > 12 and len(mac) % 12 == 0:
                        while mac != '':
                            macs.append(mac[:12])
                            mac = mac[12:]
                    else:
                        macs = [mac]
                    for mac in macs:
                        if not ip:
                            device.add_nic(mac, None)
                        else:
                            device.add_nic(mac, [ip])

                    dhcp_macs_set.add(mac)

                elif 'Cisco' in device_type:
                    mac = device_raw.get('mac')
                    if not mac:
                        logger.warning(f'Bad device no MAC {device_raw}')
                        continue
                    if mac in macs_set:
                        continue
                    device.id = mac + device_type
                    ip = device_raw.get('ip')
                    if not ip:
                        device.add_nic(mac, None)
                    else:
                        device.add_nic(mac, [ip])
                    device.vlan = device_raw.get('vlan')
                    device.port = device_raw.get('port')
                    device.cisco_device = device_raw.get('cisco_device')
                    macs_set.add(mac)
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem getting device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
