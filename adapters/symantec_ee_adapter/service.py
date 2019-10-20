import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string, is_domain_valid
from symantec_ee_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecEeAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        decrypted_volumes = ListField(str, 'Decrypted Volumes')
        decrypting_volumes = ListField(str, 'Decrypting Volumes')
        encrypted_volumes = ListField(str, 'Encrypted Volumes')
        encrypting_volumes = ListField(str, 'Encrypting Volumes')
        number_of_hds = Field(int, 'Number Of HDs')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.SYMANTEC_EE_HOST]

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.SYMANTEC_EE_DATABASE,
                                                                    consts.DEFAULT_SYMANTEC_EE_DATABASE),
                                         server=client_config[consts.SYMANTEC_EE_HOST],
                                         port=client_config.get(consts.SYMANTEC_EE_PORT,
                                                                consts.DEFAULT_SYMANTEC_EE_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.SYMANTEC_EE_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.SYMANTEC_EE_DATABASE, consts.DEFAULT_SYMANTEC_EE_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            yield from client_data.query(consts.SYMANTEC_EE_QUERY)

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.SYMANTEC_EE_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.SYMANTEC_EE_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_SYMANTEC_EE_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.SYMANTEC_EE_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                    'default': consts.DEFAULT_SYMANTEC_EE_DATABASE
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
                consts.SYMANTEC_EE_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.SYMANTEC_EE_DATABASE
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('CompName')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_id}')
                    continue
                device.id = str(device_id)
                domain = device_raw.get('DnsDomName')
                device.bios_serial = device_raw.get('SMBIOSSerialNum')
                if is_domain_valid(domain):
                    device.domain = domain
                try:
                    device.last_seen = parse_date(device_raw.get('LastCheckIn'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                device.hostname = device_raw.get('CompName')
                device.add_agent_version(agent=AGENT_NAMES.symantec_ee,
                                         version=device_raw.get('SEE Version'))
                try:
                    device.figure_os(device_raw.get('OSVersion'))
                except Exception:
                    logger.exception(f'Problem getting OS for')
                try:
                    if device_raw.get('DecryptedVolumes') and isinstance(device_raw.get('DecryptedVolumes'), str):
                        device.decrypted_volumes = [vol.strip()
                                                    for vol in device_raw.get('DecryptedVolumes').split(',')
                                                    if vol.strip()]
                except Exception:
                    logger.exception(f'Problem getting DecryptedVolumes in {device_raw}')
                try:
                    if device_raw.get('DecryptingVolumes') and isinstance(device_raw.get('DecryptingVolumes'), str):
                        device.decrypting_volumes = [vol.strip()
                                                     for vol in device_raw.get('DecryptingVolumes').split(',')
                                                     if vol.strip()]
                except Exception:
                    logger.exception(f'Problem getting DecryptingVolumes in {device_raw}')
                try:
                    if device_raw.get('EncryptedVolumes') and isinstance(device_raw.get('EncryptedVolumes'), str):
                        device.encrypted_volumes = [vol.strip()
                                                    for vol in device_raw.get('EncryptedVolumes').split(',')
                                                    if vol.strip()]
                except Exception:
                    logger.exception(f'Problem getting DecryptedVolumes in {device_raw}')
                try:
                    if device_raw.get('EncryptingVolumes') and isinstance(device_raw.get('EncryptingVolumes'), str):
                        device.encrypting_volumes = [vol.strip()
                                                     for vol in device_raw.get('EncryptingVolumes').split(',')
                                                     if vol.strip()]
                except Exception:
                    logger.exception(f'Problem getting EncryptingVolumes in {device_raw}')
                try:
                    device.number_of_hds = int(device_raw.get('NumberOfHardDisks'))
                except Exception:
                    logger.exception(f'Problem getting number of hds to {device_raw}')
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
