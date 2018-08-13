import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from axonius.adapter_exceptions import GetDevicesError
from observeit_adapter import consts
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.parsing import get_organizational_units_from_dn, get_exception_string


class ObserveitAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        client_version = Field(str, 'Client Version')
        client_status = Field(str, 'Client Status')
        client_type = Field(str, "Clietn Type")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self.devices_fetched_at_a_time = int(self.config['DEFAULT'][consts.DEVICES_FETECHED_AT_A_TIME])

    def _get_client_id(self, client_config):
        return client_config[consts.OBSERVEIT_HOST]

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.OBSERVEIT_DATABASE, consts.DEFAULT_OBSERVEIT_DATABASE),
                                         server=client_config[consts.OBSERVEIT_HOST],
                                         port=client_config.get(consts.OBSERVEIT_PORT, consts.DEFAULT_OBSERVEIT_PORT),
                                         devices_paging=self.devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f"Error connecting to client host: {str(client_config[consts.OBSERVEIT_HOST])}  " \
                      f"database: {str(client_config.get(consts.OBSERVEIT_DATABASE, consts.DEFAULT_OBSERVEIT_DATABASE))}"
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        try:
            client_data.connect()
            yield from client_data.query(consts.OBSERVEIT_QUERY)
        finally:
            client_data.logout()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": consts.OBSERVEIT_HOST,
                    "title": "MSSQL Server",
                    "type": "string"
                },
                {
                    "name": consts.OBSERVEIT_PORT,
                    "title": "Port",
                    "type": "integer",
                    "default": consts.DEFAULT_OBSERVEIT_PORT,
                    "format": "port"
                },
                {
                    "name": consts.OBSERVEIT_DATABASE,
                    "title": "Database",
                    "type": "string",
                    "default": consts.DEFAULT_OBSERVEIT_DATABASE
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
                consts.OBSERVEIT_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.OBSERVEIT_DATABASE
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        for device_raw in raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get("SrvID")
                if device_id is None or device_id == "":
                    logger.error(f"Found a device with no id: {device_raw}, skipping")
                    continue
                device.id = device_id
                domain = device_raw.get("SrvCurrentDomainName")
                device.domain = domain
                hostname = device_raw.get("SrvName")
                if (hostname is not None) and (hostname != ""):
                    if (domain is not None) and (domain.strip() != "") and (domain.strip().lower() != "local") and\
                            (domain.strip().lower() != "workgroup") and (domain.strip().lower() != "n/a") and \
                            (domain.strip().lower() != hostname.strip().lower()) and \
                            (domain.strip().lower() != "localhost") and \
                            (not hostname.strip().lower().startswith(domain.strip().lower())):
                        device.hostname = f"{hostname}.{domain}"
                    else:
                        device.hostname = hostname
                ip_list = device_raw.get("CurrentIPAddressList")
                try:
                    if ip_list is not None:
                        device.add_nic(None, ip_list.split("%"))
                except Exception:
                    logger.exception(f"Problem adding nic to {device_raw}")
                device.client_version = device_raw.get("SrvVersion")
                device.client_status = device_raw.get("SrvMonitorStatus")
                try:
                    device.last_seen = parse_date(str(device_raw.get("ScreenshotLastActivityDate")))
                except Exception:
                    logger.exception(f"Problem adding last seen to {device_raw}")
                device.client_type = device_raw.get("AgentType")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem adding device: {str(device_raw)}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
