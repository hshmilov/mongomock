import logging

from axonius.clients.service_now.service.adapter_base import ServiceNowAdapterBase
from axonius.clients.service_now.service.structures import SnowDeviceAdapter, SnowUserAdapter
from axonius.clients.service_now.sql import ServiceNowMSSQLConnection
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.adapter_base import AdapterProperty
from axonius.clients.rest.connection import RESTConnection
from axonius.adapter_exceptions import ClientConnectionException
from service_now_sql_adapter import consts
from service_now_sql_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowSqlAdapter(ServiceNowAdapterBase, Configurable):

    ###
    # Note: Most of the logic occurs in ServiceNowAdapterBase
    ###

    class MyDeviceAdapter(SnowDeviceAdapter):
        pass

    class MyUserAdapter(SnowUserAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    def get_connection(self, client_config):
        try:
            connection = ServiceNowMSSQLConnection(database=client_config.get(consts.SERVICE_NOW_SQL_DATABASE,
                                                                              consts.DEFAULT_SERVICE_NOW_SQL_DATABASE),
                                                   server=client_config[consts.SERVICE_NOW_SQL_HOST],
                                                   port=client_config.get(consts.SERVICE_NOW_SQL_PORT,
                                                                          consts.DEFAULT_SERVICE_NOW_SQL_PORT),
                                                   devices_paging=self._devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            message = f'Error connecting to client host: {client_config[consts.SERVICE_NOW_SQL_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.SERVICE_NOW_SQL_DATABASE, consts.DEFAULT_SERVICE_NOW_SQL_DATABASE)}.'\
                      f' {str(e)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    def _clients_schema(self):
        """
        The schema ServiceNowSqlAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': consts.SERVICE_NOW_SQL_HOST,
                    'title': 'ServiceNow SQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.SERVICE_NOW_SQL_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_SERVICE_NOW_SQL_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.SERVICE_NOW_SQL_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                    'default': consts.DEFAULT_SERVICE_NOW_SQL_DATABASE
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
                },
                *ServiceNowAdapterBase.SERVICE_NOW_CLIENTS_SCHEMA_ITEMS,
            ],
            'required': [
                consts.SERVICE_NOW_SQL_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.SERVICE_NOW_SQL_DATABASE,
                *ServiceNowAdapterBase.SERVICE_NOW_CLIENTS_SCHEMA_REQUIRED,
            ],
            'type': 'array'
        }

    # pylint: disable=useless-return
    @classmethod
    def _parse_optional_reference(cls, device_raw: dict, field_name: str, reference_table: dict):
        # ServiceNow SQL references are actually 32 character guid (sys_id) strings!
        # For now:
        # * we dont request and parse subtables, so unable to parse references from reference_table
        # * see _parse_optional_reference_value override on how we handle reference values
        reference_guid = super()._parse_optional_reference(device_raw, field_name, reference_table)
        if reference_guid and not isinstance(reference_guid, str):
            logger.warning(f'Got unexpected reference in SnowSQL: {reference_guid}')
            # fallthrough

        # TO-DO: For Next phase, switch to parsing reference (32bit GUID) and using reference_table param for it.
        return None

    @classmethod
    def _parse_optional_reference_value(cls, device_raw: dict, field_name: str,
                                        reference_table: dict, reference_table_field: str):
        """
        Currently we don't handle raw references.
        But, we do support references with adjacent display value "dv_*" additional fields which exist
            in device_raw to replace only as an alternative for reference.get('name').
        """

        # If reference value asked is name, try to locate it from the raw display value first.
        # See: https://jasondove.wordpress.com/2012/06/16/a-few-random-tips-for-servicenow-reporting/
        if reference_table_field == 'name':
            for curr_field in [f'dv_{field_name}', field_name]:
                raw_value = device_raw.get(curr_field)
                if isinstance(raw_value, str) and raw_value:
                    return raw_value

        return None

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                *ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_SCHEMA_ITEMS,
                {
                    'name': 'devices_fetched_at_a_time',
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            'required': [
                *ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_SCHEMA_REQUIRED,
                'devices_fetched_at_a_time'
            ],
            'pretty_name': 'ServiceNow Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            **ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_DEFAULT,
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        devices_fetched_at_a_time = config.get('devices_fetched_at_a_time') or 1000
        # inject parallel_requests
        config['parallel_requests'] = devices_fetched_at_a_time
        super()._on_config_update(config)
        self._devices_fetched_at_a_time = devices_fetched_at_a_time
