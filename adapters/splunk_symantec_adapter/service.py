import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, IPS_FIELD, MAC_FIELD
from axonius.utils.files import get_local_config_file
from splunk_symantec_adapter.connection import SplunkConnection


SPLUNK_HOST = 'host'
SPLUNK_PORT = 'port'
SPLUNK_USER = 'username'
SPLUNK_PASSWORD = 'password'
SPLUNK_TOKEN = 'token'
SPLUNK_ONLINE_HOURS = 'online_hours'


class SplunkSymantecAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)
        self._online_hours = 24

    def _get_client_id(self, client_config):
        return '{0}:{1}'.format(client_config[SPLUNK_HOST], client_config[SPLUNK_PORT])

    def _connect_client(self, client_config):
        has_token = bool(client_config.get(SPLUNK_TOKEN))
        maybe_has_user = bool(client_config.get(SPLUNK_USER)) or bool(client_config.get(SPLUNK_PASSWORD))
        has_user = bool(client_config.get(SPLUNK_USER)) and bool(client_config.get(SPLUNK_PASSWORD))
        if has_token and maybe_has_user:
            msg = f"Different logins for Splunk [Symantec] domain " \
                  f"{client_config.get(SPLUNK_HOST)}, user: {client_config.get(SPLUNK_USER, '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        elif maybe_has_user and not has_user:
            msg = f"Missing credentials for Splunk [Symantec] domain " \
                  f"{client_config.get(SPLUNK_HOST)}, user: {client_config.get(SPLUNK_USER, '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        try:
            self._online_hours = int(client_config[SPLUNK_ONLINE_HOURS] or self._online_hours)
            assert self._online_hours > 0, "You entered an invalid amount of hours as online hours"
            # copying as otherwise we would pop it from the client saved in the gui
            client_con = client_config.copy()
            client_con.pop(SPLUNK_ONLINE_HOURS)
            connection = SplunkConnection(**client_con)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def get_last_query_ts(self, name):
        ts_collection = self._get_collection('queries_ts')
        for item in ts_collection.find({'query_name': name}):
            return item['ts']
        return None

    def set_last_query_ts(self, name, ts):
        ts_collection = self._get_collection('queries_ts')
        ts_collection.update({'query_name': name}, {'query_name': name, 'ts': ts}, upsert=True)

    def _update_new_raw_devices(self, client_data, queries_collection):
        already_updates = []
        last_ts = self.get_last_query_ts('symantec')
        for host in client_data.get_symantec_devices_info(last_ts):
            name = host['name']
            if name in already_updates:
                continue
            already_updates.append(name)
            queries_collection.update({'name': name}, {'name': name, 'host': host}, upsert=True)
            timestamp = client_data.parse_time(host['timestamp'])
            if last_ts is None or last_ts < timestamp:
                last_ts = timestamp
        if last_ts is not None:
            self.set_last_query_ts('symantec', int(last_ts + 1))

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Splunk domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Splunk connection

        :return: A json with all the attributes returned from the Splunk Server
        """
        with client_data:
            queries_collection = self._get_collection('symantec_queries')
            # Update all_devices from splunk
            self._update_new_raw_devices(client_data, queries_collection)

            # Get "Active" devices
            active_hosts = client_data.get_symantec_active_hosts(self._online_hours)

            #
            if active_hosts:
                all_devices = list(queries_collection.find({'$or': [{'name': name} for name in active_hosts]}))
            else:
                all_devices = []
            return all_devices

    def _clients_schema(self):
        """
        The schema SplunkSymantecAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": SPLUNK_HOST,
                    "title": "Host Name",
                    "type": "string",
                },
                {
                    "name": SPLUNK_PORT,
                    "title": "Port",
                    "type": "integer",
                    "format": "port"
                },
                {
                    "name": SPLUNK_USER,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": SPLUNK_PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": SPLUNK_TOKEN,
                    "title": "API Token",
                    "type": "string"
                },
                {
                    "name": SPLUNK_ONLINE_HOURS,
                    "title": "Online Hours Threshold",
                    "description": "Hours for device to be considered online (default = 24)",
                    "type": "number"
                }
            ],
            "required": [
                SPLUNK_HOST,
                SPLUNK_PORT
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            host = device_raw.get('host', '')
            device = self._new_device_adapter()
            device.hostname = host.get('name', '')
            if host.get('type', '') == 'symantec_mac':
                device.figure_os('OS X')
                if host.get('local mac', '') != '000000000000':
                    device.add_nic(':'.join([host.get('local mac', '')[index:index + 2] for index in range(0, 12, 2)]),
                                   host.get('local ips', '').split(' '))
                if host.get('remote mac', '') != '000000000000':
                    device.add_nic(':'.join([host.get('remote mac', '')[index:index + 2] for index in range(0, 12, 2)]),
                                   host['remote ips'].split(' '))
            else:
                device.figure_os(host.get('os', ''))
                for iface in host.get('network', []):
                    device.add_nic(iface.get(MAC_FIELD, ''), iface.get(IPS_FIELD, '').split(' '))
            device.id = host['name']
            device.set_raw(device_raw)
            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
