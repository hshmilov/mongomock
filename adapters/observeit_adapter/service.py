import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string, is_domain_valid
from observeit_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class ObserveitAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        client_version = Field(str, 'Client Version')
        client_status = Field(str, 'Client Status')
        client_type = Field(str, 'Client Type')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.OBSERVEIT_HOST]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.OBSERVEIT_DATABASE,
                                                                    consts.DEFAULT_OBSERVEIT_DATABASE),
                                         server=client_config[consts.OBSERVEIT_HOST],
                                         port=client_config.get(consts.OBSERVEIT_PORT, consts.DEFAULT_OBSERVEIT_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.OBSERVEIT_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.OBSERVEIT_DATABASE, consts.DEFAULT_OBSERVEIT_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        try:
            client_data.connect()
            yield from client_data.query(consts.OBSERVEIT_QUERY)
        finally:
            client_data.logout()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.OBSERVEIT_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.OBSERVEIT_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_OBSERVEIT_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.OBSERVEIT_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                    'default': consts.DEFAULT_OBSERVEIT_DATABASE
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
                consts.OBSERVEIT_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.OBSERVEIT_DATABASE
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('SrvID')
                if device_id is None or device_id == '':
                    logger.error(f'Found a device with no id: {device_raw}, skipping')
                    continue
                os_type = None
                try:
                    os_type = int(device_raw.get('OSType') or device_raw.get('OperatingSystemType'))
                    device.figure_os(consts.OS_TYPES_DICT[os_type])
                except Exception:
                    logger.exception(f'Problem getting os of {device_raw}')
                domain = device_raw.get('SrvCurrentDomainName')
                if domain and domain.endswith('.local'):
                    domain = domain[:-len('.local')]
                if not is_domain_valid(domain):
                    domain = None
                hostname = device_raw.get('SrvName')
                if os_type is not None and consts.OS_TYPES_DICT[os_type] == 'Mac OS X':
                    if domain and '.' not in domain:
                        domain = domain.replace('’', '')
                        device.hostname = domain
                    elif hostname and hostname.lower() != 'localhost':
                        hostname = hostname.replace('’', '')
                        device.hostname = hostname
                    else:
                        logger.warning(f'Got an Observeit id with only localhost in the names, '
                                       f'it is a bad device {device_raw}')
                        continue
                elif hostname:
                    if domain and not hostname.strip().lower().startswith(domain.strip().lower()):
                        device.hostname = f'{hostname}.{domain}'
                        device.domain = domain
                    else:
                        device.hostname = hostname
                device.id = device_id + (hostname or '') + (domain or '')
                ip_list = device_raw.get('PrimaryIPAddress') or device_raw.get('CurrentIPAddressList')
                try:
                    if ip_list is not None:
                        device.add_nic(None, ip_list.split(','))
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                device.client_version = device_raw.get('SrvVersion')
                device.client_status = device_raw.get('SrvMonitorStatus')
                try:
                    device.last_seen = parse_date(str(device_raw.get('ScreenshotLastActivityDate')))
                except Exception:
                    logger.exception(f'Problem adding last seen to {device_raw}')
                device.client_type = device_raw.get('AgentType')
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
            'pretty_name': 'ObserveIT Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
