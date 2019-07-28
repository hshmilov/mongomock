import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from symantec_sep_cloud_adapter.connection import SymantecSepCloudConnection
from symantec_sep_cloud_adapter.client_id import get_client_id
from symantec_sep_cloud_adapter.consts import DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecSepCloudAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_status = Field(str, 'Device Status')
        security_client_install_date = Field(datetime.datetime, 'Security Client Install Date')
        mdm_provider = Field(str, 'MDM Provider')
        health_attestation_status = Field(str, 'Health Attestation Status')
        modified = Field(datetime.datetime, 'Modified')
        created = Field(datetime.datetime, 'Created')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = SymantecSepCloudConnection(domain=client_config.get('domain') or DEFAULT_DOMAIN,
                                                verify_ssl=client_config['verify_ssl'],
                                                https_proxy=client_config.get('https_proxy'),
                                                domain_id=client_config['domain_id'],
                                                customer_id=client_config['customer_id'],
                                                client_id=client_config['client_id'],
                                                client_secret=client_config['client_secret'])
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
        The schema SymantecCloudWorkloadAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Symantec Endpoint Protection Cloud URL',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN
                },
                {
                    'name': 'domain_id',
                    'title': 'Domain Id',
                    'type': 'string'
                },
                {
                    'name': 'customer_id',
                    'title': 'Customer Id',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client Id',
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
                }
            ],
            'required': [
                'domain',
                'domain_id',
                'customer_id',
                'client_id',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            device_hardware = device_raw.get('hardware')
            if not isinstance(device_hardware, dict):
                device_hardware = {}

            device.uuid = device_hardware.get('uuid')
            device.health_attestation_status = device_raw.get('health-attestation-status')
            device.device_serial = device_hardware.get('serial-number')
            device.device_model = device_hardware.get('model-name')
            device.last_seen = parse_date(device_raw.get('last-enrollment-date'))
            device.security_client_install_date = parse_date(device_raw.get('security-client-install-date'))
            device.device_model_family = device_hardware.get('model-vendor')
            nics = device_raw.get('network-adapters')
            if not isinstance(nics, list):
                nics = []
            for nic in nics:
                try:
                    device.add_nic(mac=nic.get('addr'), name=nic.get('name'))
                except Exception:
                    logger.exception(f'Problem with nic {nic}')
            try:
                device.figure_os((device_raw.get('operating-system') or {}).get('friendlyname'))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            device.device_status = device_raw.get('device-status')
            device.modified = parse_date(device_raw.get('modified'))
            device.created = parse_date(device_raw.get('created'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching SymantecSepCloud Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
