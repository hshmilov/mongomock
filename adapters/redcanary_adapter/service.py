import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from axonius.utils.parsing import is_domain_valid
from redcanary_adapter.connection import RedcanaryConnection
from redcanary_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class RedcanaryAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        is_decommissioned = Field(bool, 'Is Decommissioned')
        is_isolated = Field(bool, 'Is Isolated')
        monitoring_status = Field(str, 'Monitoring Status')

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
        connection = RedcanaryConnection(domain=client_config['domain'],
                                         verify_ssl=client_config['verify_ssl'],
                                         https_proxy=client_config.get('https_proxy'),
                                         apikey=client_config['apikey'])
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
        The schema RedcanaryAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Redcanary Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-nested-blocks,too-many-branches,too-many-statements
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None or 'attributes' not in device_raw:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device_attributes = device_raw['attributes']
            device.id = str(device_id) + '_' + (device_attributes.get('hostname') or '')
            hostname = device_attributes.get('hostname')
            device.hostname = hostname
            if '.' in hostname:
                domain = '.'.join(hostname.split('.')[1:])
                if is_domain_valid(domain):
                    device.domain = domain
            device.monitoring_status = device_attributes.get('monitoring_status')
            try:
                device.figure_os((device_attributes.get('platform') or '') + ' ' +
                                 (device_attributes.get('operating_system') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            device.is_isolated = device_attributes.get('is_isolated')
            device.is_decommissioned = device_attributes.get('is_decommissioned')
            try:
                device.last_seen = parse_date(device_attributes.get('last_checkin_time'))
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            if device_attributes.get('username'):
                device.last_used_users = [device_attributes.get('username')]
            nics = device_attributes.get('endpoint_network_addresses')
            if nics and isinstance(nics, list):
                for nic in nics:
                    mac = None
                    ips = None
                    try:
                        mac = nic['attributes']['mac_address']
                        if not mac:
                            mac = None
                        else:
                            mac = mac['attributes']['address']
                            if not mac:
                                mac = None
                    except Exception:
                        logger.exception(f'Problem getting mac in {nic}')
                    try:
                        ip = nic['attributes']['ip_address']['attributes']['ip_address']
                        if ip:
                            ips = [ip]
                    except Exception:
                        logger.exception(f'Problem getting ip in {nic}')
                    if mac or ips:
                        device.add_nic(mac, ips)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Redcanary Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
