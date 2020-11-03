import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.network.sockets import test_reachability_tcp
from axonius.utils.parsing import get_exception_string
from scep_adapter.consts import SCEP_DATABASE, SCEP_HOST, SCEP_PORT, DEFAULT_SCEP_PORT, USER, PASSWORD, MALWARE_QUERY

logger = logging.getLogger(f'axonius.{__name__}')


class ScepAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        resource_id = Field(str, 'Resource ID')
        sccm_server = Field(str, 'SCCM Server')
        malware_engine_version = Field(str, 'Malware Protection Engine Version')
        malware_version = Field(str, 'Malware Protection Version')
        malware_product_status = Field(str, 'Malware Protection Product Status')
        malware_last_full_scan = Field(datetime.datetime, 'Malware Protection Last Full Scan')
        malware_last_quick_scan = Field(datetime.datetime, 'Malware Protection Last Quick Scan')
        malware_enabled = Field(str, 'Malware Protection Enabled Status')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[SCEP_HOST]

    def _test_reachability(self, client_config):
        return test_reachability_tcp(
            client_config.get('server'),
            client_config.get('port') or DEFAULT_SCEP_PORT
        )

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(
                database=client_config[SCEP_DATABASE],
                server=client_config[SCEP_HOST],
                port=client_config.get(SCEP_PORT) or DEFAULT_SCEP_PORT,
                devices_paging=self.__devices_fetched_at_a_time,
            )
            connection.set_credentials(username=client_config[USER], password=client_config[PASSWORD])
            with connection:
                for _ in connection.query('select ResourceID from v_GS_AntimalwareHealthStatus'):
                    break
            return connection
        except Exception as err:
            message = (
                f'Error connecting to client host: {str(client_config[SCEP_HOST])}  '
                f'database: {str(client_config[SCEP_DATABASE])}'
            )
            logger.exception(message)
            if 'permission was denied' in str(repr(err)).lower():
                raise ClientConnectionException(f'Error connecting to SCEP: {str(err)}')
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            for device_raw in client_data.query(MALWARE_QUERY):
                yield device_raw, client_data.server

    def _clients_schema(self):
        return {
            'items': [
                {'name': SCEP_HOST, 'title': 'SCEP/MSSQL Server', 'type': 'string'},
                {'name': SCEP_PORT, 'title': 'Port', 'type': 'integer', 'default': DEFAULT_SCEP_PORT},
                {'name': SCEP_DATABASE, 'title': 'Database', 'type': 'string'},
                {'name': USER, 'title': 'User Name', 'type': 'string'},
                {'name': PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
            ],
            'required': [SCEP_HOST, USER, PASSWORD, SCEP_DATABASE],
            'type': 'array',
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, sccm_server in devices_raw_data:
            try:
                device_id = device_raw.get('ResourceID')
                if not device_id:
                    logger.error(f'Got a device with no distinguished name {device_raw}')
                    continue

                device = self._new_device_adapter()
                device.sccm_server = sccm_server
                if not device_raw.get('ResourceID'):
                    logger.warning(f'Bad device with no resource id {device_raw}')
                    continue
                device.id = sccm_server + str(device_raw.get('ResourceID') or '')
                device.resource_id = str(device_raw.get('ResourceID'))
                device.malware_engine_version = device_raw.get('EngineVersion')
                device.malware_version = device_raw.get('Version')
                device.malware_product_status = device_raw.get('ProductStatus')
                device.malware_last_full_scan = parse_date(device_raw.get('LastFullScanDateTimeEnd'))
                device.malware_last_quick_scan = parse_date(device_raw.get('LastQuickScanDateTimeEnd'))
                device.malware_enabled = device_raw.get('Enabled')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with device: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'devices_fetched_at_a_time',
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            'required': ['devices_fetched_at_a_time'],
            'pretty_name': 'SCEP Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000,
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
