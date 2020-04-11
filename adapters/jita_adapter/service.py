import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.configurable import Configurable
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from jita_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class JitaAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        is_stale = Field(bool, 'Is Stale')
        last_logon = Field(datetime.datetime, 'Last Logon')
        last_scanned = Field(datetime.datetime, 'Last Scanned')
        updated = Field(datetime.datetime, 'Updated')
        policy_scan = Field(bool, 'Policy Scan')
        policy_secure = Field(bool, 'Policy Secure')
        last_scan_success = Field(bool, 'Last Scan Success')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.JITA_HOST]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.JITA_DATABASE),
                                         server=client_config[consts.JITA_HOST],
                                         port=client_config.get(consts.JITA_PORT, consts.DEFAULT_JITA_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.JITA_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.JITA_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            for device_raw in client_data.query(consts.JITA_QUERY):
                yield device_raw

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.JITA_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.JITA_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_JITA_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.JITA_DATABASE,
                    'title': 'Database',
                    'type': 'string',
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
                consts.JITA_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.JITA_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('dNSHostName')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_id}')
                    continue
                device.id = str(device_id)
                device.hostname = device_raw.get('dNSHostName')
                if is_domain_valid(device_raw.get('domain')):
                    device.domain = device_raw.get('domain')
                if device_raw.get('lastIP'):
                    device.add_nic(ips=[device_raw.get('lastIP')])
                is_stale = device_raw.get('isStale') if isinstance(device_raw.get('isStale'), bool) else None
                device.is_stale = is_stale
                if self.__exclude_stale_devices and is_stale:
                    continue
                last_logon = parse_date(device_raw.get('lastLogonTimestamp'))
                last_seen = last_logon
                device.last_logon = last_logon
                last_scanned = parse_date(device_raw.get('lastScanned'))
                if not last_seen:
                    last_seen = last_scanned
                elif last_scanned:
                    last_seen = max(last_scanned, last_seen)
                device.last_scanned = last_scanned

                updated = parse_date(device_raw.get('updatedTS'))
                if not last_seen:
                    last_seen = updated
                elif updated:
                    last_seen = max(updated, last_seen)
                device.updated = updated
                device.last_seen = last_seen
                device.figure_os(device_raw.get('operatingSystem'))
                device.policy_scan = device_raw.get('policyScan') \
                    if isinstance(device_raw.get('policyScan'), bool) else None
                device.policy_secure = device_raw.get('policySecure') \
                    if isinstance(device_raw.get('policySecure'), bool) else None
                device.last_scan_success = device_raw.get('lastScanSuccess') \
                    if isinstance(device_raw.get('lastScanSuccess'), bool) else None
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
                },
                {
                    'name': 'exclude_stale_devices',
                    'title': 'Exclude stale devices',
                    'type': 'bool'
                }
            ],
            'required': ['devices_fetched_at_a_time', 'exclude_stale_devices'],
            'pretty_name': 'Remediant SecureOne Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000,
            'exclude_stale_devices': True
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
        self.__exclude_stale_devices = config['exclude_stale_devices']
