import datetime
import logging


from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.adapter_exceptions import GetDevicesError
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.mixins.configurable import Configurable
from axonius.utils.parsing import normalize_var_name
from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from axonius.consts.csv_consts import get_csv_field_names
from mssql_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class MssqlAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get('database'),
                                         server=client_config['domain'],
                                         port=int(client_config.get('port')),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config['username'],
                                       password=client_config['password'])
            with connection:
                pass  # check that the connection credentials are valid
            return connection, client_config
        except Exception as err:
            domain = client_config['domain']
            database = client_config['database']
            message = f'Error connecting to client host: {domain}  ' \
                      f'database: ' \
                      f'{database}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        connection, client_config = client_data
        table = client_config['table']
        connection.set_devices_paging(self.__devices_fetched_at_a_time)
        with connection:
            yield from connection.query(f'Select * from {table}')

    @staticmethod
    def _clients_schema():
        """
        The schema MssqlAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Mssql Domain',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Mssql Port',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'database',
                    'title': 'Mssql Database',
                    'type': 'string'
                },
                {
                    'name': 'table',
                    'title': 'Mssql Table',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'port',
                'database',
                'table'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        first_time = True
        fields = {}
        for device_raw in devices_raw_data:
            try:
                if first_time:
                    fields = get_csv_field_names(device_raw.keys())
                    first_time = False
                if not any(id_field in fields for id_field in ['id', 'serial', 'mac_address', 'hostname']):
                    logger.error(f'Bad devices fields names {device_raw.keys()}')
                    raise GetDevicesError(f'Strong identifier is missing for devices')
                device = self._new_device_adapter()
                vals = {field_name: device_raw.get(fields[field_name][0]) for field_name in fields}

                macs = (vals.get('mac_address') or '').split(',')
                macs = [mac.strip() for mac in macs if mac.strip()]
                mac_as_id = macs[0] if macs else None

                device_id = str(vals.get('id', '')) or vals.get('serial') or mac_as_id or vals.get('hostname')
                if not device_id:
                    logger.error(f'can not get device id for {device_raw}, continuing')
                    continue

                device.id = device_id
                device.device_serial = vals.get('serial')
                device.name = vals.get('name')
                device.hostname = vals.get('hostname')
                device.device_model = vals.get('model')
                device.domain = vals.get('domain')
                try:
                    last_seen = None
                    if isinstance(vals.get('last_seen'), str):
                        last_seen = parse_date(vals.get('last_seen'))
                    if last_seen:
                        device.last_seen = last_seen
                    elif isinstance(vals.get('last_seen'), int):
                        device.last_seen = datetime.datetime.fromtimestamp(vals.get('last_seen'))
                except Exception:
                    logger.exception(f'Problem adding last seen')

                device.device_manufacturer = vals.get('manufacturer')
                device.total_physical_memory = vals.get('total_physical_memory_gb')

                # OS is a special case, instead of getting the first found column we take all of them and combine them
                if 'os' in fields:
                    try:
                        os_raw = ''
                        for os_column in fields['os']:
                            if device_raw.get(os_column) and isinstance(device_raw.get(os_column), str):
                                os_raw += device_raw.get(os_column) + ' '
                        device.figure_os(os_raw)
                    except Exception:
                        logger.error(f'Can not parse os ')

                try:
                    device.os.kernel_version = vals.get('kernel')
                except Exception:
                    # os is probably not set
                    device.figure_os('')
                    device.os.kernel_version = vals.get('kernel')

                try:
                    cpu_speed = vals.get('cpu_speed')
                    architecture = vals.get('architecture')
                    if cpu_speed or architecture:
                        device.add_cpu(ghz=cpu_speed / (1024 ** 3), architecture=architecture)
                except Exception:
                    logger.exception(f'Problem setting cpu')
                try:
                    ips = None
                    if isinstance(vals.get('ip'), str):
                        ips = (vals.get('ip') or '').split(',')
                        ips = [ip.strip() for ip in ips if ip.strip()]
                    device.add_ips_and_macs(macs=macs, ips=ips)
                except Exception:
                    logger.exception(f'Problem getting nic and ips for {device_raw}')

                device.set_raw(device_raw)

                for column_name, column_value in device_raw.items():
                    try:
                        normalized_column_name = 'mssql_' + normalize_var_name(column_name)
                        if not device.does_field_exist(normalized_column_name):
                            # Currently we treat all columns as str
                            cn_capitalized = ' '.join([word.capitalize() for word in column_name.split(' ')])
                            device.declare_new_field(normalized_column_name, Field(str, f'MSSQL {cn_capitalized}'))

                        device[normalized_column_name] = column_value
                    except Exception:
                        logger.exception(f'Could not parse column {column_name} with value {column_value}')

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Mssql Device for {device_raw}')

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
            'pretty_name': 'SQL Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
