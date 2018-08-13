import logging
from datetime import timedelta
from uuid import UUID

logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from axonius.clients.mssql.connection import MSSQLConnection
import symantec_altiris_adapter.consts as consts


class SymantecAltirisAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter, ADEntity):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self.devices_fetched_at_a_time = int(self.config['DEFAULT'][consts.DEVICES_FETECHED_AT_A_TIME])

    def _get_client_id(self, client_config):
        return client_config[consts.ALTIRIS_HOST]

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.ALTIRIS_DATABASE, consts.DEFAULT_ALTIRIS_DATABASE),
                                         server=client_config[consts.ALTIRIS_HOST],
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
                device.id = device_id
                domain = device_raw.get('Domain')
                server_full_name = device_raw.get('Server')
                name = device_raw.get('Name')
                device.name = name
                device.hostname = server_full_name

                # The last one is to make sure that the server_full_name actually
                # includes the full domain name as well as the server name.
                if domain is not None and server_full_name is not None and len(server_full_name) > len(domain) + len(name):
                    device.domain = server_full_name[len(name) + 1:]
                    device.part_of_domain = True

                device.figure_os(device_raw.get('OS Name', '') + ' ' + device_raw.get('OS Version') + ' ' +
                                 device_raw.get("OS Revision", '') + ' ' + device_raw.get("System Type", ''))
                try:
                    device.add_nic(device_raw.get('MAC Address'), [device_raw.get('IP Address')])
                except Exception:
                    logger.exception(f"Caught weird NIC for device id {device_raw}")
                    pass
                username = device_raw.get('User')
                if username is not None:
                    device.add_users(username=str(username), is_local=True if domain is not None else False)
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
