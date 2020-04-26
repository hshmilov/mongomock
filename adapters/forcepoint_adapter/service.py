import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.mixins.configurable import Configurable
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from forcepoint_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class ForcepointAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        profile_name = Field(str, 'Profile Name')
        machine_type = Field(str, 'Machine Type')
        synced = Field(bool, 'Synced')
        client_installation_version = Field(str, 'Client Installation Version')
        last_policy_update = Field(datetime.datetime, 'Last Policy Update')
        last_profile_update = Field(datetime.datetime, 'Last Profile Update')
        profile_version = Field(int, 'Profile Version')
        operation_status = Field(str, 'Operation Status')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.FORCEPOINT_HOST]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.FORCEPOINT_DATABASE),
                                         server=client_config[consts.FORCEPOINT_HOST],
                                         port=client_config.get(consts.FORCEPOINT_PORT, consts.DEFAULT_FORCEPOINT_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                for _ in connection.query(consts.FORCEPOINT_QUERY):
                    break
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.FORCEPOINT_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.FORCEPOINT_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            for device_raw in client_data.query(consts.FORCEPOINT_QUERY):
                yield device_raw

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.FORCEPOINT_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.FORCEPOINT_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_FORCEPOINT_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.FORCEPOINT_DATABASE,
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
                consts.FORCEPOINT_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.FORCEPOINT_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.hostname = device_raw.get('Hostname')
                device.id = device.hostname
                device.add_agent_version(agent=AGENT_NAMES.forcepoint_csv,
                                         version=device_raw.get('Version'),
                                         status=device_raw.get('Client Status'))
                ips = None
                macs = None
                if isinstance(device_raw.get('IP Address'), str) and device_raw.get('IP Address'):
                    ips = device_raw.get('IP Address').split(',')
                if isinstance(device_raw.get('MacAddress'), str) and device_raw.get('MacAddress'):
                    macs = device_raw.get('MacAddress').split(',')
                device.add_ips_and_macs(macs=macs, ips=ips)
                if device_raw.get('Logged-in Users') and isinstance(device_raw.get('Logged-in Users'), str):
                    if ';' in device_raw.get('Logged-in Users'):
                        device.last_used_users = device_raw.get('Logged-in Users').split(';')
                    else:
                        device.last_used_users = device_raw.get('Logged-in Users').split(',')
                device.last_seen = parse_date(device_raw.get('Last Update'))
                device.profile_name = device_raw.get('Profile Name')
                device.machine_type = device_raw.get('Machine Type')
                device.client_installation_version = device_raw.get('ClientInstallationVersion')
                device.last_policy_update = parse_date(device_raw.get('LastPolicyUpdate'))
                device.last_profile_update = parse_date(device_raw.get('LastProfileUpdate'))
                device.operation_status = device_raw.get('OperationStatus')
                device.profile_version = device_raw.get('ProfileVersion') \
                    if isinstance(device_raw.get('ProfileVersion'), int) else None
                if str(device_raw.get('Synced')) == '1':
                    device.synced = True
                elif str(device_raw.get('Synced')) == '0':
                    device.synced = False
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
            'required': ['devices_fetched_at_a_time'],
            'pretty_name': 'Forcepoint Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
