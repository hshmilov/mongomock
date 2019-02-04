import ipaddress
import logging

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from illusive_adapter.connection import IllusiveConnection

logger = logging.getLogger(f'axonius.{__name__}')


class IllusiveAdapter(ScannerAdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        policy_name = Field(str, 'Policy Name')
        deployment_status = Field(str, 'Deployment Status')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = IllusiveConnection(domain=client_config['domain'],
                                            apikey=client_config['apikey'],
                                            verify_ssl=client_config.get('verify_ssl', False),
                                            https_proxy=client_config.get('https_proxy'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Illusive domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Illusive connection

        :return: A json with all the attributes returned from the Illusive Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema IllusiveAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Illusive Domain',
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

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('hostId')
                if not device_id:
                    logger.warning(f'No id of device {device_raw}')
                    continue
                device.id = device_id + (device_raw.get('host') or '')
                hostname_or_ip = device_raw.get('host')
                try:
                    ip = str(ipaddress.ip_address(hostname_or_ip))
                    device.add_nic(None, [ip])
                except Exception:
                    device.hostname = hostname_or_ip
                device.domain = device_raw.get('domainName')
                try:
                    device.figure_os((device_raw.get('operatingSystem') or '') +
                                     (device_raw.get('operatingSystemBitness') or ''))
                except Exception:
                    logger.exception(f'Probelm getting OS for {device_raw}')
                device.last_seen = parse_date(device_raw.get('lastDeployment'))
                try:
                    if 'Unable to find' not in (device_raw.get('lastSeenUser') or ''):
                        device.last_used_users = (device_raw.get('lastSeenUser') or '').split(',')
                except Exception:
                    logger.exception(f'Problem getting users at {device_raw}')
                device.policy_name = device_raw.get('policyName')
                device.deployment_status = device_raw.get('deploymentStatus')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Illusive Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Manager]
