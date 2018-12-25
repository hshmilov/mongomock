import logging
from datetime import timedelta
from uuid import UUID

logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from axonius.clients.mssql.connection import MSSQLConnection
import symantec_altiris_adapter.consts as consts
from axonius.utils.parsing import is_domain_valid


class SymantecAltirisAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        is_local = Field(bool, 'Is Local')
        is_managed = Field(bool, 'Is Managed')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self.devices_fetched_at_a_time = int(self.config['DEFAULT'][consts.DEVICES_FETECHED_AT_A_TIME])

    def _get_client_id(self, client_config):
        return client_config[consts.ALTIRIS_HOST]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            server = client_config[consts.ALTIRIS_HOST]
            if server.startswith('https://'):
                server = server[len('https://'):]
            connection = MSSQLConnection(database=client_config.get(consts.ALTIRIS_DATABASE, consts.DEFAULT_ALTIRIS_DATABASE),
                                         server=server,
                                         port=client_config.get(consts.ALTIRIS_PORT, consts.DEFAULT_ALTIRIS_PORT),
                                         devices_paging=self.devices_fetched_at_a_time, tds_version='7.3')
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f"Error connecting to client host: {str(client_config[consts.ALTIRIS_HOST])}  " \
                      f"database: {str(client_config.get(consts.ALTIRIS_DATABASE, consts.DEFAULT_ALTIRIS_DATABASE))}"
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        try:
            client_data.connect()
            yield from client_data.query(consts.ALTIRIS_QUERY)
        finally:
            client_data.logout()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": consts.ALTIRIS_HOST,
                    "title": "MSSQL Server",
                    "type": "string"
                },
                {
                    "name": consts.ALTIRIS_PORT,
                    "title": "Port",
                    "type": "integer",
                    "default": consts.DEFAULT_ALTIRIS_PORT,
                    "format": "port"
                },
                {
                    "name": consts.ALTIRIS_DATABASE,
                    "title": "Database",
                    "type": "string",
                    "default": consts.DEFAULT_ALTIRIS_DATABASE
                },
                {
                    "name": consts.USER,
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
                consts.ALTIRIS_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.ALTIRIS_DATABASE
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device_id = str(UUID(bytes=device_raw.get('Guid')))
                if not device_id:
                    logger.error(f'Got a device with no distinguished name {device_raw}')
                    continue
                device = self._new_device_adapter()
                device.id = device_id + '_' + (device_raw.get('Name') or '')
                domain = device_raw.get('Domain')
                if not is_domain_valid(domain):
                    domain = None
                device.domain = domain
                server_full_name = device_raw.get('Server')
                name = device_raw.get('Name')
                device.hostname = name

                device.figure_os((device_raw.get('OS Name') or '') + ' ' + (device_raw.get('OS Version') or '') + ' ' +
                                 (device_raw.get("OS Revision") or '') + ' ' + (device_raw.get("System Type") or ''))
                try:
                    mac = device_raw.get('MAC Address')
                    if mac is not None and mac.strip() == '':
                        mac = None
                    ip = device_raw.get('IP Address')
                    if ip is None or ip.strip() == '':
                        ips = None
                    else:
                        ips = ip.split(',')
                    if mac or ips:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception(f"Caught weird NIC for device id {device_raw}")
                    pass
                try:
                    username = device_raw.get('User')
                    if username and username.strip():
                        device.last_used_users = username.split(',')
                except Exception:
                    logger.exception(f'Problem adding users to {device_raw}')
                is_managed = device_raw.get('IsManaged')
                if is_managed is not None:
                    device.is_managed = bool(is_managed)
                is_local = device_raw.get('IsLocal')
                if is_local is not None:
                    device.is_local = bool(is_local)
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem with Altiris device {device_raw}")

    def _correlation_cmds(self):
        logger.error("correlation_cmds is not implemented for sccm adapter")
        raise NotImplementedError("correlation_cmds is not implemented for sccm adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        logger.error("_parse_correlation_results is not implemented for sccm adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for sccm adapter")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
