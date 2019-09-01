import datetime
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
from specops_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class SpecopsAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        last_full_inventory = Field(datetime.datetime, 'Last Full Inventory')
        last_heartbeat = ListField(datetime.datetime, 'Last Heartbeat')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return client_config[consts.SPECOPS_HOST]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.SPECOPS_DATABASE),
                                         server=client_config[consts.SPECOPS_HOST],
                                         port=client_config.get(consts.SPECOPS_PORT, consts.SPECOPS_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.SPECOPS_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.SPECOPS_DATABASE, consts.SPECOPS_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:

            hardware_dict = dict()
            try:
                for hardware_data in client_data.query(consts.HARDWARE_QUERY):
                    asset_id = hardware_data.get('PrincipalId')
                    if not asset_id:
                        continue
                    hardware_dict[asset_id] = hardware_data
            except Exception:
                logger.exception(f'Problem getting hardware')

            ad_dict = dict()
            try:
                for ad_data in client_data.query(consts.AD_QUERY):
                    asset_id = ad_data.get('PrincipalId')
                    if not asset_id:
                        continue
                    ad_dict[asset_id] = ad_data
            except Exception:
                logger.exception(f'Problem getting ad')

            os_dict = dict()
            try:
                for os_data in client_data.query(consts.OS_QUERY):
                    asset_id = os_data.get('PrincipalId')
                    if not asset_id:
                        continue
                    os_dict[asset_id] = os_data
            except Exception:
                logger.exception(f'Problem getting os')

            network_dict = dict()
            try:
                for network_data in client_data.query(consts.NETWORK_QUERY):
                    asset_id = network_data.get('PrincipalId')
                    if not asset_id:
                        continue
                    network_dict[asset_id] = network_data
            except Exception:
                logger.exception(f'Problem getting network')

            for device_raw in client_data.query(consts.COMPUTERS_QUERY):
                yield device_raw, hardware_dict, ad_dict, os_dict, network_dict

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {
                    'name': consts.SPECOPS_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.SPECOPS_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_SPECOPS_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.SPECOPS_DATABASE,
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
                consts.SPECOPS_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.SPECOPS_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, hardware_dict, ad_dict, os_dict, network_dict in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('PrincipalId')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_id}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('Computer') or '')
                device.hostname = device_raw.get('Computer')
                if is_domain_valid(device_raw.get('Domain')):
                    device.domain = device_raw.get('Domain')
                last_full_inventory = parse_date(device_raw.get('Last full inventory'))
                device.last_full_inventory = last_full_inventory
                device.last_seen = last_full_inventory
                last_heartbeat = parse_date(device_raw.get('Last Heartbeat'))
                device.last_heartbeat = last_heartbeat
                try:
                    if last_full_inventory and last_heartbeat:
                        if last_heartbeat > last_full_inventory:
                            device.last_seen = last_heartbeat
                    elif last_heartbeat:
                        device.last_seen = last_heartbeat
                except Exception:
                    logger.exception(f'Problem with last seen of {device_raw}')

                os_data = os_dict.get(device_raw.get('PrincipalId'))
                if isinstance(os_data, dict):
                    try:
                        device.figure_os((os_data.get('Operating system') or '') + ' ' +
                                         (os_data.get('OS version') or '') + ' ' +
                                         (os_data.get('OS service pack') or ''))
                    except Exception:
                        logger.exception(f'Problem with os data')

                network_data = network_dict.get(device_raw.get('PrincipalId'))
                if isinstance(network_data, dict):
                    try:
                        mac = network_data.get('Mac address')
                        if not mac:
                            mac = None
                        ips = network_data.get('IP addresses')
                        if not ips or not isinstance(ips, str):
                            ips = None
                        else:
                            ips = ips.split(',')
                        if mac or ips:
                            device.add_nic(mac=mac, ips=ips)
                    except Exception:
                        logger.exception(f'Problem with network data')

                ad_data = ad_dict.get(device_raw.get('PrincipalId'))
                if isinstance(ad_data, dict):
                    try:
                        device.description = ad_data.get('Description')
                    except Exception:
                        logger.exception(f'Problem with ad data')

                hardware_data = hardware_dict.get(device_raw.get('PrincipalId'))
                if isinstance(hardware_data, dict):
                    try:
                        device.device_model = hardware_data.get('Computer model')
                        device.bios_serial = hardware_data.get('Serial number bios')
                        if hardware_data.get('Last user') and isinstance(hardware_data.get('Last user'), str):
                            device.last_used_users = hardware_data.get('Last user').split(',')
                        device.bios_version = hardware_data.get('Bios version')
                    except Exception:
                        logger.exception(f'Problem with hardware data')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device: {str(device_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

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
            'pretty_name': 'Specops Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
