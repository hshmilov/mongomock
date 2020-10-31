import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.traps import consts
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string, parse_bool_from_raw, int_or_none
from traps_adapter.client_id import get_client_id
from traps_adapter.structures import TrapsDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class TrapsAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(TrapsDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    def get_connection(self, client_config):
        connection = MSSQLConnection(database=client_config.get(consts.TRAPS_DATABASE,
                                                                consts.DEFAULT_TRAPS_DATABASE),
                                     server=client_config.get(consts.TRAPS_HOST),
                                     port=client_config.get(consts.TRAPS_PORT,
                                                            consts.DEFAULT_TRAPS_PORT),
                                     devices_paging=self.__devices_fetched_at_a_time)
        connection.set_credentials(username=client_config.get(consts.USER),
                                   password=client_config.get(consts.PASSWORD))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except Exception:
            message = f'Error connecting to client host: {client_config[consts.TRAPS_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.TRAPS_DATABASE, consts.DEFAULT_TRAPS_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    def _query_devices_by_client(self, client_name, client_data: MSSQLConnection):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            devices_raw_query = list(client_data.query(consts.TRAPS_QUERY))
            for device_raw_original in devices_raw_query:
                device_raw = device_raw_original.copy()

                yield device_raw

    def _clients_schema(self):
        """
        The schema TrapsAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': consts.TRAPS_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.TRAPS_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_TRAPS_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.TRAPS_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                    'default': consts.DEFAULT_TRAPS_DATABASE
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
                consts.TRAPS_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.TRAPS_DATABASE
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_traps_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.content_version = device_raw.get('ContentVersion')
            device.cyvera_version = device_raw.get('CyveraVersion')
            device.heartbeat_interval_minutes = int_or_none(device_raw.get('HeartbeatIntervalMinutes'))
            device.is_64 = parse_bool_from_raw(device_raw.get('Is64Bit'))
            device.is_os_compatible = parse_bool_from_raw(device_raw.get('IsOsCompatible'))
            device.last_data_update_time = parse_date(device_raw.get('LastDataUpdateTime'))
            device.license_expiration_date = parse_date(device_raw.get('LicenseExpirationDate'))
            device.is_on = parse_bool_from_raw(device_raw.get('MachineIsOn'))
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('Id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('MachineName') or '') + '_' \
                + (device_raw.get('UniqueId') or '')
            device.hostname = device_raw.get('MachineName')
            device.uuid = device_raw.get('UniqueId')
            device.last_seen = parse_date(device_raw.get('LastHeartbeatTime'))
            device.first_seen = parse_date(device_raw.get('RegistrationDate'))
            if device_raw.get('IPAddress'):
                device.add_nic(ips=[device_raw.get('IPAddress')])
            device.figure_os((device_raw.get('OsName') or '') + ' ' + (device_raw.get('OSVersion') or ''))
            device.domain = device_raw.get('Domain')

            self._fill_traps_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Traps Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Traps Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': consts.DEVICES_FETCHED_AT_A_TIME,
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            'required': [consts.DEVICES_FETCHED_AT_A_TIME],
            'pretty_name': 'Traps Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            consts.DEVICES_FETCHED_AT_A_TIME: consts.DEVICES_FETCHED_AT_A_TIME_NUMBER
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config[consts.DEVICES_FETCHED_AT_A_TIME]
