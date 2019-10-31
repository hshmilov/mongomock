import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.fields import Field
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.oracle_db.connection import OracleDBConnection
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from symantec_dlp_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=no-self-use
class SymantecDlpAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        group_name = Field(str, 'Group Name')
        group_description = Field(str, 'Group Description')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.SYMANTEC_DLP_HOST] + '_' + client_config[consts.USER]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = OracleDBConnection(host=client_config[consts.SYMANTEC_DLP_HOST],
                                            port=client_config.get(consts.SYMANTEC_DLP_PORT,
                                                                   consts.DEFAULT_SYMANTEC_DLP_PORT),
                                            devices_paging=self.__devices_fetched_at_a_time,
                                            username=client_config[consts.USER],
                                            password=client_config[consts.PASSWORD],
                                            service=client_config[consts.SYMANTEC_DLP_DATABASE]
                                            )
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                for _ in connection.query(consts.SYMANTEC_DLP_QUERY):
                    break
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.SYMANTEC_DLP_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.SYMANTEC_DLP_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            for device_raw in client_data.query(consts.SYMANTEC_DLP_QUERY):
                yield device_raw

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.SYMANTEC_DLP_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.SYMANTEC_DLP_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_SYMANTEC_DLP_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.SYMANTEC_DLP_DATABASE,
                    'title': 'Database',
                    'type': 'string'
                },
                {
                    'name': consts.USER,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                consts.SYMANTEC_DLP_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.SYMANTEC_DLP_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('AGENTID')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_id}')
                    continue
                device.id = str(device_id) + '_' + device_raw.get('AGENTNAME')
                device.hostname = device_raw.get('AGENTNAME')
                device.figure_os(device_raw.get('OSNAME'))
                device.add_agent_version(agent=AGENT_NAMES.symantec_dlp,
                                         version=device_raw.get('VERSION'),
                                         status=device_raw.get('STATUS'))
                device.last_seen = parse_date(device_raw.get('LASTCONNECTIONTIME'))
                device.group_name = device_raw.get('NAME')
                device.group_description = device_raw.get('DESCRIPTION')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device: {str(device_raw)}')

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
            'required': [],
            'pretty_name': 'Symantec Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
