import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES, DeviceAdapterOS
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.parsing import get_exception_string
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
import wsus_adapter.consts as consts

logger = logging.getLogger(f'axonius.{__name__}')


class WsusAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        wsus_server = Field(str, 'WSUS Server')
        last_sync_result = Field(str, 'Last Sync Result')
        last_sync_time = Field(datetime.datetime, 'Last Sync Time')
        last_reported_inventory_time = Field(datetime.datetime, 'Last Reported Inventory Time')
        groups = ListField(str, 'Groups')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.WSUS_HOST]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(
                database=client_config[consts.WSUS_DATABASE],
                server=client_config[consts.WSUS_HOST],
                port=client_config.get(consts.WSUS_PORT) or consts.DEFAULT_WSUS_PORT,
                devices_paging=self.__devices_fetched_at_a_time,
            )
            connection.set_credentials(username=client_config[consts.USER], password=client_config[consts.PASSWORD])
            with connection:
                for _ in connection.query(consts.WSUS_MAIN_QUERY):
                    break
            return connection
        except Exception as err:
            message = (
                f'Error connecting to client host: {str(client_config[consts.WSUS_HOST])}  '
                f'database: {str(client_config[consts.WSUS_DATABASE])}'
            )
            logger.exception(message)
            if 'permission was denied' in str(repr(err)).lower():
                raise ClientConnectionException(f'Error connecting to WSUS: {str(err)}')
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:

            target_groups_dict = dict()
            try:
                for target_groups_data in client_data.query(consts.TARGET_GROUPS_QUERY):
                    asset_id = target_groups_data.get('ComputerTargetId')
                    group_id = target_groups_data.get('ComputerTargetGroupId')
                    if not asset_id or not group_id:
                        continue
                    if asset_id not in target_groups_dict:
                        target_groups_dict[asset_id] = []
                    target_groups_dict[asset_id].append(group_id)
            except Exception:
                logger.warning(f'Problem getting groups data dict', exc_info=True)

            groups_id_to_data_dict = dict()
            try:
                for target_groups_id_data in client_data.query(consts.TARGET_GROUPS_ID_QUERY):
                    group_id = target_groups_id_data.get('ComputerTargetGroupId')
                    group_name = target_groups_id_data.get('Name')
                    if not group_name or not group_id:
                        continue
                    groups_id_to_data_dict[group_id] = group_name
            except Exception:
                logger.warning(f'Problem getting groups id data dict', exc_info=True)

            for device_raw in client_data.query(consts.WSUS_MAIN_QUERY):
                yield device_raw, client_data.server, target_groups_dict, groups_id_to_data_dict

    def _clients_schema(self):
        return {
            'items': [
                {'name': consts.WSUS_HOST, 'title': 'MSSQL Server', 'type': 'string'},
                {'name': consts.WSUS_PORT, 'title': 'Port', 'type': 'integer', 'default': consts.DEFAULT_WSUS_PORT},
                {'name': consts.WSUS_DATABASE, 'title': 'Database', 'type': 'string'},
                {'name': consts.USER, 'title': 'User Name', 'type': 'string'},
                {'name': consts.PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
            ],
            'required': [consts.WSUS_HOST, consts.USER, consts.PASSWORD, consts.WSUS_DATABASE],
            'type': 'array',
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, wsus_server, target_groups_dict, groups_id_to_data_dict in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.wsus_server = wsus_server
                device_id = device_raw.get('ComputerTargetId')
                if device_id is None:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('Name') or '')
                device.hostname = device_raw.get('Name')
                if device_raw.get('IPAddress'):
                    device.add_nic(ips=[device_raw.get('IPAddress')])
                device.last_sync_result = device_raw.get('LastSyncResult')
                last_sync_time = parse_date(device_raw.get('LastSyncTime'))
                device.last_sync_time = last_sync_time
                last_reported_inventory_time = parse_date(device_raw.get('LastReportedInventoryTime'))
                device.last_reported_inventory_time = last_reported_inventory_time
                if last_reported_inventory_time and last_sync_time:
                    device.last_seen = max(last_sync_time, last_reported_inventory_time)
                else:
                    device.last_seen = last_sync_time or last_reported_inventory_time
                device.add_agent_version(agent=AGENT_NAMES.wsus,
                                         version=device_raw.get('ClientVersion'))
                device.device_manufacturer = device_raw.get('Make')
                device.device_model = device_raw.get('Model')
                try:
                    device.os = DeviceAdapterOS()
                    device.os.type = 'Windows'
                    device.os.build = device_raw.get('OSBuildNumber')
                    device.os.major = device_raw.get('OSMajorVersion')
                    device.os.minor = device_raw.get('OSMinorVersion')
                    device.os.sp = device_raw.get('OSServicePackMajorNumber')
                except Exception:
                    logger.exception(f'Prolbem with os for {device_raw}')
                device.bios_version = device_raw.get('BiosVersion')
                try:
                    group_ids = target_groups_dict.get(device_id)
                    if not isinstance(group_ids, list):
                        group_ids = []
                    for group_id in group_ids:
                        try:
                            if groups_id_to_data_dict.get(group_id):
                                device.groups.append(groups_id_to_data_dict.get(group_id))
                        except Exception:
                            logger.exception(f'Problem with group ID')
                except Exception:
                    logger.exception(f'Problem getting groups')
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
            'pretty_name': 'WSUS Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000,
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
