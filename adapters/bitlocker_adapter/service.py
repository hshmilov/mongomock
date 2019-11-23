import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string, is_domain_valid
from bitlocker_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class BitlockerAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        tpm_version = Field(str, 'TPM Version')
        tpm_manufacturer = Field(str, 'TPM Manufacturer')
        is_compliant = Field(bool, 'Is Compliant')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.BITLOCKER_HOST]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.BITLOCKER_DATABASE),
                                         server=client_config[consts.BITLOCKER_HOST],
                                         port=client_config.get(consts.BITLOCKER_PORT, consts.DEFAULT_BITLOCKER_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.BITLOCKER_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.BITLOCKER_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            compliance_dict = dict()
            try:
                for compliance_data in client_data.query(consts.COMPLIANCE_QUERY):
                    compliance_id = compliance_dict.get('Id')
                    if not compliance_id:
                        continue
                    compliance_dict[compliance_id] = compliance_data
            except Exception:
                logger.exception(f'Problem getting alerts')
            for device_raw in client_data.query(consts.BITLOCKER_QUERY):
                yield device_raw, compliance_dict

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.BITLOCKER_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.BITLOCKER_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_BITLOCKER_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.BITLOCKER_DATABASE,
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
                consts.BITLOCKER_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.BITLOCKER_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, compliance_dict in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('Id')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_id}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('') or 'Name')
                device.hostname = device_raw.get('Name')
                device.last_seen = parse_date(device_raw.get('LastUpdateTime'))
                device.bios_version = device_raw.get('BiosVersion')
                device.tpm_version = device_raw.get('TpmVersion')
                device.tpm_manufacturer = device_raw.get('TpmMake')
                device.add_agent_version(agent=AGENT_NAMES.bitlocker, version=device_raw.get('AgentVersion'))
                try:
                    compliacne_data = compliance_dict.get(device_id)
                    if compliacne_data:
                        if is_domain_valid(compliacne_data.get('DomainName')):
                            device.domain = compliacne_data.get('DomainName')
                        device.figure_os(compliacne_data.get('OperatingSystemName'))
                        is_compliant = compliacne_data.get('IsCompliant')
                        if str(is_compliant) == '1':
                            device.is_compliant = True
                        elif str(is_compliant) == '0':
                            device.is_compliant = False
                except Exception:
                    logger.exception(f'Problem with compliance data for {device_raw}')
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
            'pretty_name': 'BITLOCKER Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
