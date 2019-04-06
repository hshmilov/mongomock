import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from tripwire_enterprise_adapter.client_id import get_client_id
from tripwire_enterprise_adapter.connection import TripWireEnterpriseConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TripwireEnterpriseAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        tracking_id = Field(str, 'Tracking ID')
        last_check = Field(datetime.datetime, 'Last Check')
        modified_time = Field(datetime.datetime, 'Modified Time')
        imported_time = Field(datetime.datetime, 'Imported Time')
        last_registration = Field(datetime.datetime, 'Last Registration')
        has_failures = Field(bool, 'Has Failures')
        agent_version = Field(str, 'Agent Versoin')
        is_disabled = Field(str, 'Is Disabled')
        is_socks_proxy = Field(str, 'Is Socks Proxy')
        max_severity = Field(int, 'Max Severity')
        real_time_enabled = Field(bool, 'Real Time Enabled')
        rmi_host = Field(str, 'RMI Host')
        rmi_port = Field(str, 'RMI Port')
        tripwire_tags = ListField(str, 'Tripwire Tags')
        element_count = Field(int, 'Element Count')
        agent_capabilities = ListField(str, 'Agent Capabilities')
        audit_enabled = Field(bool, 'Audit Enabled')
        event_generator_installed = Field(bool, 'Evenet Generator Installed')
        event_generator_enabled = Field(bool, 'Evenet Generator Enabled')
        licensed_features = ListField(str, 'Licensed Features')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        client_id = self._get_client_id(client_config)
        try:
            connection = TripWireEnterpriseConnection(domain=client_config['domain'],
                                                      verify_ssl=client_config['verify_ssl'],
                                                      username=client_config['username'],
                                                      password=client_config['password'],
                                                      https_proxy=client_config.get('https_proxy'))
            with connection:
                pass
            return connection
        except Exception as e:
            logger.error(f'Failed to connect to client {client_id}')
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Tripwire Enter Domain',
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
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
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

    # pylint: disable=R0915
    def create_device(self, device_raw):
        device = self._new_device_adapter()
        device_id = device_raw.get('id')
        if not device_id:
            logger.warning(f'Bad device with no name {device_raw}')
            return None
        device.id = device_id + '_' + (device_raw.get('name') or '')
        device.hostname = device_raw.get('name')
        try:
            device.add_ips_and_macs(macs=device_raw.get('macAddresses'), ips=device_raw.get('ipAddresses'))
        except Exception:
            logger.exception(f'Problem adding nic to {device_raw}')
        device.tracking_id = device_raw.get('trackingId')
        try:
            device.last_check = parse_date(device_raw.get('lastCheck'))
            device.imported_time = parse_date(device_raw.get('importedTime'))
            device.modified_time = parse_date(device_raw.get('modifiedTime'))
            device.last_registration = parse_date(device_raw.get('lastRegistration'))

        except Exception:
            logger.exception(f'Problem adding parse date {device_raw}')
        device.device_manufacturer = device_raw.get('make')
        device.device_model = device_raw.get('model')
        device.has_failures = device_raw.get('hasFailures')
        device.agent_version = device_raw.get('agentVersion')
        device.description = device_raw.get('description')
        device.is_disabled = device_raw.get('isDisabled')
        device.is_socks_proxy = device_raw.get('isSocksProxy')
        device.real_time_enabled = device_raw.get('realTimeEnabled')
        device.rmi_host = device_raw.get('rmiHost')
        device.rmi_port = device_raw.get('rmiPort')
        try:
            device.max_severity = device_raw.get('maxSeverity')
        except Exception:
            logger.exception(f'Problem getting max severity for {device_raw}')
        try:
            if device_raw.get('tags') and isinstance(device_raw.get('tags'), list):
                for tag_raw in device_raw.get('tags'):
                    if tag_raw and isinstance(tag_raw, dict):
                        device.tripwire_tags.append(tag_raw.get('tag'))
        except Exception:
            logger.exception(f'Problem adding tags to {device_raw}')
        try:
            device.element_count = device_raw.get('elementCount')
        except Exception:
            logger.exception(f'Problem getting element count for {device_raw}')
        try:
            device.agent_capabilities = device_raw.get('commonAgentCapabilities')
        except Exception:
            logger.exception(f'Problem getting agent capabilities for {device_raw}')
        try:
            device.figure_os((device_raw.get('commonAgentOsName') or '') + ' ' +
                             (device_raw.get('commonAgentOsVersion') or ''))
        except Exception:
            logger.exception(f'Prbolem getting os for {device_raw}')
        device.uuid = device_raw.get('commonAgentUuid')
        device.audit_enabled = device_raw.get('auditEnabled')
        device.event_generator_installed = device_raw.get('eventGeneratorInstalled')
        device.event_generator_enabled = device_raw.get('eventGeneratorEnabled')
        try:
            device.licensed_features = device_raw.get('licensedFeatures')
        except Exception:
            logger.exception(f'Problem getting license features for {device_raw}')
        device.set_raw(device_raw)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in iter(devices_raw_data):
            try:
                device = self.create_device(device_raw)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
