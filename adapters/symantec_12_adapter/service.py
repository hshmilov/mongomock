import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.utils.parsing import is_domain_valid
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from symantec_12_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=no-self-use
class Symantec12Adapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.SYMANTEC_12_HOST] + '_' + client_config[consts.USER]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.SYMANTEC_12_DATABASE),
                                         server=client_config[consts.SYMANTEC_12_HOST],
                                         port=client_config.get(consts.SYMANTEC_12_PORT,
                                                                consts.DEFAULT_SYMANTEC_12_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.SYMANTEC_12_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.SYMANTEC_12_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            for device_raw in client_data.query(consts.SYMANTEC_12_QUERY):
                yield device_raw

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.SYMANTEC_12_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.SYMANTEC_12_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_SYMANTEC_12_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.SYMANTEC_12_DATABASE,
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
                consts.SYMANTEC_12_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.SYMANTEC_12_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('COMPUTER_ID')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_id}')
                    continue
                device.id = str(device_id) + '_' + device_raw.get('COMPUTER_NAME')
                device.hostname = device_raw.get('COMPUTER_NAME')
                domain = device_raw.get('COMPUTER_DOMAIN_NAME')
                if is_domain_valid(domain):
                    device.domain = domain
                device.description = device_raw.get('COMPUTER_DESCRIPTION')
                # pylint: disable=invalid-name
                device.total_number_of_physical_processors = device_raw.get('PROCESSOR_NUM') if isinstance(
                    device_raw.get('PROCESSOR_NUM'), int) else None
                # pylint: enable=invalid-name
                device.bios_version = device_raw.get('BIOS_VERSION')
                last_user = device_raw.get('CURRENT_LOGIN_USER')
                if last_user and isinstance(last_user, str):
                    last_user_domain = device_raw.get('CURRENT_LOGIN_DOMAIN')
                    if is_domain_valid(last_user_domain):
                        last_user = f'{last_user}@{last_user_domain}'
                    device.last_used_users = [last_user]
                device.uuid = device_raw.get('UUID')
                ips = []
                macs = []
                if device_raw.get('IP_ADDR1_TEXT'):
                    ips.append(device_raw.get('IP_ADDR1_TEXT'))
                if device_raw.get('IP_ADDR2_TEXT'):
                    ips.append(device_raw.get('IP_ADDR2_TEXT'))
                if device_raw.get('IP_ADDR3_TEXT'):
                    ips.append(device_raw.get('IP_ADDR3_TEXT'))
                if device_raw.get('IP_ADDR4_TEXT'):
                    ips.append(device_raw.get('IP_ADDR4_TEXT'))
                if device_raw.get('MAC_ADDR1'):
                    macs.append(device_raw.get('MAC_ADDR1'))
                if device_raw.get('MAC_ADDR2'):
                    macs.append(device_raw.get('MAC_ADDR2'))
                if device_raw.get('MAC_ADDR3'):
                    macs.append(device_raw.get('MAC_ADDR3'))
                if device_raw.get('MAC_ADDR4'):
                    macs.append(device_raw.get('MAC_ADDR4'))
                if ips or macs:
                    device.add_ips_and_macs(macs=macs, ips=ips)
                device.bios_serial = device_raw.get('BIOS_SERIALNUMBER')
                device.figure_os(device_raw.get('OPERATION_SYSTEM'))
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
