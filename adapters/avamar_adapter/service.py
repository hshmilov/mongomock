import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from axonius.utils.files import get_local_config_file
from avamar_adapter.connection import AvamarConnection
from avamar_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class AvamarAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        enabled = Field(bool, 'Enabled')
        fqdn = Field(str, 'FQDN')
        activated = Field(bool, 'Activated')
        activation_time = Field(datetime.datetime, 'Activation Time')
        allow_addition_dataset = Field(bool, 'Allow Addition Dataset')
        allow_override_schedule = Field(bool, 'Allow Override Schedule')
        can_client_be_agentless = Field(bool, 'Can Client Be Agentless')
        client_type = Field(str, 'Client Type')
        contact_location = Field(str, 'Contact Location')
        contact_name = Field(str, 'Contact Name')
        contact_phone = Field(str, 'Contact Phone')
        contact_notes = Field(str, 'Contact Notes')
        dataset_fqdn = Field(str, 'Dataset FQDN')
        dataset_id = Field(str, 'Dataset ID')
        encryption = Field(str, 'Encryption')
        overtime_option = Field(str, 'Overtime Option')
        initialization_time = Field(datetime.datetime, 'Initialization Time')
        last_backup_time = Field(datetime.datetime, 'Last Backup Time')
        last_checkit_time = Field(datetime.datetime, 'Last Checkin Time')
        last_contact_time = Field(datetime.datetime, 'Last Contact Time')
        override_dataset = Field(bool, 'Override Dataset')
        override_encryption = Field(bool, 'Override Encryption')
        override_retention = Field(bool, 'Override Retention')
        paging_address = Field(str, 'Paging Address')
        paging_automatic = Field(bool, 'Paging Automatic')
        paging_enabled = Field(bool, 'Paging Enabled')
        paging_port = Field(int, 'Paging Port')
        paging_secure_port = Field(int, 'Paging Secure Port')
        retention_fqdn = Field(str, 'Retention FQDN')
        retention_id = Field(str, 'Retention Id')
        registered = Field(bool, 'Registered')
        restore_only = Field(bool, 'Restore Only')
        total_backups = Field(int, 'Total Backups')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = AvamarConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      username=client_config['username'],
                                      password=client_config['password'],
                                      https_proxy=client_config.get('https_proxy'),
                                      proxy_username=client_config.get('proxy_username'),
                                      proxy_password=client_config.get('proxy_password'),
                                      client_id=client_config.get('client_id'),
                                      client_secret=client_config.get('client_secret'))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema AvamarAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Avamar Domain',
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
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    @staticmethod
    def _create_device(device_raw, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')

            device.activated = device_raw.get('activated') if isinstance(device_raw.get('activated'), bool) else None
            device.allow_addition_dataset = device_raw.get('allowAdditionDataset')\
                if isinstance(device_raw.get('allowAdditionDataset'), bool) else None
            device.allow_override_schedule = device_raw.get('allowOverrideSchedule')\
                if isinstance(device_raw.get('allowOverrideSchedule'), bool) else None
            device.can_client_be_agentless = device_raw.get('canClientBeAgentLess') \
                if isinstance(device_raw.get('canClientBeAgentLess'), bool) else None
            device.override_dataset = device_raw.get('overrideDataset')\
                if isinstance(device_raw.get('overrideDataset'), bool) else None
            device.override_encryption = device_raw.get('overrideEncryption')\
                if isinstance(device_raw.get('overrideEncryption'), bool) else None
            device.override_retention = device_raw.get('overrideRetention') \
                if isinstance(device_raw.get('overrideRetention'), bool) else None
            device.client_type = device_raw.get('clientType')
            device.figure_os(device_raw.get('clientOs'))
            device.activation_time = parse_date(device_raw.get('activationTime'))
            device.add_agent_version(agent=AGENT_NAMES.avamar,
                                     version=device_raw.get('clientVersion'))
            contact_raw = device_raw.get('contact')
            if not isinstance(contact_raw, dict):
                contact_raw = {}
            device.email = contact_raw.get('email')
            device.contact_location = contact_raw.get('location')
            device.contact_name = contact_raw.get('name')
            device.contact_phone = contact_raw.get('phone')
            device.contact_notes = contact_raw.get('notes')
            device.set_raw(device_raw)
            domain = device_raw.get('domainFqdn')
            device.hostname = device_raw.get('name')
            device.fqdn = device_raw.get('fqdn')
            device.dataset_fqdn = device_raw.get('datasetFqdn')
            device.dataset_id = device_raw.get('datasetId')
            if is_domain_valid(domain):
                device.domain = domain
            device.encryption = device_raw.get('encryption')
            device.enabled = device_raw.get('enabled') if isinstance(device_raw.get('enabled'), bool) else None
            device.overtime_option = device_raw.get('overtimeOption')

            device.override_dataset = device_raw.get('allowAdditionDataset')\
                if isinstance(device_raw.get('allowAdditionDataset'), bool) else None
            device.allow_override_schedule = device_raw.get('allowOverrideSchedule')\
                if isinstance(device_raw.get('allowOverrideSchedule'), bool) else None
            device.can_client_be_agentless = device_raw.get('canClientBeAgentLess') \
                if isinstance(device_raw.get('canClientBeAgentLess'), bool) else None
            initialization_time = parse_date(device_raw.get('initializationTime'))
            last_seen = initialization_time
            device.initialization_time = initialization_time
            last_backup_time = parse_date(device_raw.get('lastBackupTime'))
            device.last_backup_time = last_backup_time
            if not last_seen:
                last_seen = last_backup_time
            elif last_backup_time and last_backup_time > last_seen:
                last_seen = last_backup_time

            last_checkit_time = parse_date(device_raw.get('lastCheckinTime'))
            device.last_checkit_time = last_checkit_time
            if not last_seen:
                last_seen = last_checkit_time
            elif last_checkit_time and last_checkit_time > last_seen:
                last_seen = last_checkit_time

            last_contact_time = parse_date(device_raw.get('lastContactTime'))
            device.last_contact_time = last_contact_time
            if not last_seen:
                last_seen = last_contact_time
            elif last_contact_time and last_contact_time > last_seen:
                last_seen = last_contact_time
            device.last_seen = last_seen

            paging_raw = device_raw.get('paging')
            if not isinstance(paging_raw, dict):
                paging_raw = {}
            device.paging_address = paging_raw.get('address')
            device.paging_automatic = paging_raw.get('automatic')\
                if isinstance(paging_raw.get('automatic'), bool) else None
            device.paging_enabled = paging_raw.get('enabled')\
                if isinstance(paging_raw.get('enabled'), bool) else None
            device.paging_port = paging_raw.get('port') \
                if isinstance(paging_raw.get('port'), int) else None
            device.paging_secure_port = paging_raw.get('securePort') \
                if isinstance(paging_raw.get('securePort'), int) else None
            device.retention_fqdn = device_raw.get('retentionFqdn')
            device.retention_id = device_raw.get('retentionId')

            device.registered = paging_raw.get('registered')\
                if isinstance(paging_raw.get('registered'), bool) else None
            device.restore_only = paging_raw.get('restoreOnly')\
                if isinstance(paging_raw.get('restoreOnly'), bool) else None
            device.total_backups = paging_raw.get('totalBackups') \
                if isinstance(paging_raw.get('totalBackups'), int) else None
            return device
        except Exception:
            logger.exception(f'Problem with fetching Avamar Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw, self._new_device_adapter())
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
