import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string, is_domain_valid
from promisec_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class PromisecAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        threats_found = Field(int, 'Threats Found')
        alert_names = ListField(str, 'Alert Names')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.PROMISEC_HOST]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.PROMISEC_DATABASE,
                                                                    consts.DEFAULT_PROMISEC_DATABASE),
                                         server=client_config[consts.PROMISEC_HOST],
                                         port=client_config.get(consts.PROMISEC_PORT, consts.DEFAULT_PROMISEC_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.PROMISEC_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.PROMISEC_DATABASE, consts.DEFAULT_PROMISEC_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            alerts_dict = dict()
            try:
                for alerts_data in client_data.query(consts.ALERTS_QUERY):
                    asset_id = alerts_data.get('host')
                    if asset_id not in alerts_dict:
                        alerts_dict[asset_id] = []
                    alerts_dict[asset_id].append(alerts_data)
            except Exception:
                logger.exception(f'Problem getting alerts')
            for device_raw in client_data.query(consts.PROMISEC_QUERY):
                yield device_raw, alerts_dict

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.PROMISEC_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.PROMISEC_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_PROMISEC_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.PROMISEC_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                    'default': consts.DEFAULT_PROMISEC_DATABASE
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
                consts.PROMISEC_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.PROMISEC_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, alerts_dict in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('host_id')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_id}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('host_name') or '')
                device.hostname = device_raw.get('host_name')
                try:
                    alerts_data = alerts_dict.get('host_id')
                    if not isinstance(alerts_data, list):
                        alerts_data = []
                    for alert_data in alerts_data:
                        try:
                            device.alert_names.append(alert_data.get('alert_name'))
                        except Exception:
                            logger.exception(f'Problem with alert {alert_data}')
                except Exception:
                    logger.exception(f'Problem with alerts {device_raw}')
                domain = device_raw.get('host_domain')
                if is_domain_valid(domain):
                    device.domain = domain
                try:
                    if device_raw.get('last_user_domain_and_name') and\
                            device_raw.get('last_user_domain_and_name').lower() not in ['none', 'null', 'unknown']:
                        device.last_used_users = device_raw.get('last_user_domain_and_name').split(',')
                except Exception:
                    logger.exception(f'Problem getting user name for {device_raw}')
                try:
                    mac = device_raw.get('host_mac_address')
                    if not mac or mac.lower() in ['none', 'null', 'unknown']:
                        mac = None
                    else:
                        mac = mac.split('-')[-1]
                    ips = device_raw.get('host_ip')
                    if not ips or ips.lower() in ['none', 'null', 'unknown']:
                        ips = None
                    else:
                        ips = ips.split(',')
                    if mac or ips:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                try:
                    device.threats_found = int(device_raw.get('threats_found'))
                except Exception:
                    logger.exception(f'Problem getting threats for {device_raw}')
                try:
                    device.figure_os(device_raw.get('host_os_version'))
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                try:
                    device.last_seen = parse_date(device_raw.get('inspection_end_time'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
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
            'pretty_name': 'Promisec Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
