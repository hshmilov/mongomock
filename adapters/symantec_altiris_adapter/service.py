import logging
from uuid import UUID

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.network.sockets import test_reachability_tcp
from axonius.utils.parsing import get_exception_string
from axonius.utils.parsing import is_domain_valid
from axonius.clients.mssql.connection import MSSQLConnection
from symantec_altiris_adapter import consts


logger = logging.getLogger(f'axonius.{__name__}')


class SymantecAltirisAdapter(AdapterBase, Configurable):

    class MyDeviceAdapter(DeviceAdapter):
        is_local = Field(bool, 'Is Local')
        is_managed = Field(bool, 'Is Managed')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.ALTIRIS_HOST] + '_' + client_config[consts.ALTIRIS_DATABASE]

    def _test_reachability(self, client_config):
        return test_reachability_tcp(
            client_config.get('server'),
            client_config.get('port') or consts.DEFAULT_ALTIRIS_PORT
        )

    def _connect_client(self, client_config):
        try:
            server = client_config[consts.ALTIRIS_HOST]
            if server.startswith('https://'):
                server = server[len('https://'):]
            connection = MSSQLConnection(database=client_config.get(consts.ALTIRIS_DATABASE,
                                                                    consts.DEFAULT_ALTIRIS_DATABASE),
                                         server=server,
                                         port=client_config.get(consts.ALTIRIS_PORT, consts.DEFAULT_ALTIRIS_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time, tds_version='7.3')
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {str(client_config[consts.ALTIRIS_HOST])}  ' \
                      f'database: {str(client_config.get(consts.ALTIRIS_DATABASE, consts.DEFAULT_ALTIRIS_DATABASE))}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    def _query_devices_by_client(self, client_name, client_data: MSSQLConnection):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:

            inventory_dict = dict()
            try:
                for inventory_data in client_data.query(consts.INVENTORY_QUERY):
                    asset_id = inventory_data.get('_ResourceGuid')
                    if not asset_id:
                        continue
                    inventory_dict[asset_id] = inventory_data
            except Exception:
                logger.exception(f'Problem getting inventory')

            software_dict = dict()
            try:
                for software_data in client_data.query(consts.SOFTWARE_QUERY):
                    asset_id = software_data.get('_ResourceGuid')
                    if not asset_id:
                        continue
                    if asset_id not in software_dict:
                        software_dict[asset_id] = []
                    software_dict[asset_id].append(software_data)
            except Exception:
                logger.exception(f'Problem getting inventory')

            for device_raw in client_data.query(consts.ALTIRIS_QUERY):
                yield device_raw, inventory_dict, software_dict

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.ALTIRIS_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.ALTIRIS_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_ALTIRIS_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.ALTIRIS_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                    'default': consts.DEFAULT_ALTIRIS_DATABASE
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
                consts.ALTIRIS_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.ALTIRIS_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, inventory_dict, software_dict in devices_raw_data:
            try:
                device_id = str(UUID(bytes=device_raw.get('Guid')))
                if not device_id:
                    logger.error(f'Got a device with no distinguished name {device_raw}')
                    continue
                device = self._new_device_adapter()
                device.id = device_id + '_' + (device_raw.get('Name') or '')
                domain = device_raw.get('Domain')
                if not is_domain_valid(domain):
                    domain = None
                device.domain = domain
                name = device_raw.get('Name')
                try:
                    software_data = software_dict.get(device_raw.get('Guid'))
                    if software_data and isinstance(software_data, list):
                        for software_raw in software_data:
                            try:
                                device.add_installed_software(name=software_raw.get('DisplayName'),
                                                              version=software_raw.get('DisplayVersion'))
                            except Exception:
                                logger.exception(f'Problem adding software raw {software_raw}')
                except Exception:
                    logger.exception(f'Problem getting software {device_raw}')
                try:
                    inventory_data = inventory_dict.get(device_raw.get('Guid'))
                    if inventory_data:
                        device.bios_serial = inventory_data.get('BIOS Serial Number')
                        if inventory_data.get('Domain') and is_domain_valid(inventory_data.get('Domain')):
                            device.domain = inventory_data.get('Domain')
                        try:
                            device.last_seen = parse_date(inventory_data.get('Client Date'))
                        except Exception:
                            logger.exception(f'Problem adding last seen to {inventory_data}')
                        try:
                            if inventory_data.get('Last Logon User'):
                                if inventory_data.get('Last Logon Domain') \
                                        and is_domain_valid(inventory_data.get('Last Logon Domain')):
                                    if '.' not in inventory_data.get('Last Logon Domain'):
                                        device.last_used_users = [inventory_data.get('Last Logon Domain') +
                                                                  '\\' + inventory_data.get('Last Logon User')]
                                    else:
                                        device.last_used_users = [inventory_data.get('Last Logon User') +
                                                                  '@' + inventory_data.get('Last Logon Domain')]
                                else:
                                    device.last_used_users = [inventory_data.get('Last Logon User')]
                        except Exception:
                            logger.exception(f'Problem adding user to {inventory_data}')
                except Exception:
                    logger.exception(f'Problem adding inventory data {device_raw}')
                device.hostname = name

                device.figure_os((device_raw.get('OS Name') or '') + ' ' + (device_raw.get('OS Version') or '') + ' ' +
                                 (device_raw.get('OS Revision') or '') + ' ' + (device_raw.get('System Type') or ''))
                try:
                    mac = device_raw.get('MAC Address')
                    if mac is not None and mac.strip() == '':
                        mac = None
                    ip = device_raw.get('IP Address')
                    if ip is None or ip.strip() == '':
                        ips = None
                    else:
                        ips = ip.split(',')
                    if mac or ips:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception(f'Caught weird NIC for device id {device_raw}')
                is_managed = device_raw.get('IsManaged')
                if is_managed is not None:
                    device.is_managed = bool(is_managed)
                is_local = device_raw.get('IsLocal')
                if is_local is not None:
                    device.is_local = bool(is_local)
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with Altiris device {device_raw}')

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
