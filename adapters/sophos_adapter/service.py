#pylint: disable=too-many-instance-attributes
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from sophos_adapter.connection import SophosConnection

logger = logging.getLogger(f'axonius.{__name__}')


class SophosAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, config_file_path=get_local_config_file(__file__), **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = SophosConnection(domain=client_config['domain'],
                                          https_proxy=client_config.get('https_proxy'),
                                          apikey=client_config.get('apikey'),
                                          authorization=client_config.get('authorization'),
                                          verify_ssl=client_config['verify_ssl'])
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
        Get all devices from a specific Sophos domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Sophos connection

        :return: A json with all the attributes returned from the Sophos Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema SophosAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Sophos API Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'x-api-key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'authorization',
                    'title': 'Authorization',
                    'type': 'string',
                    'format': 'password'
                },

                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'authorization',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw['id']
                if not device_id:
                    logger.warning(f'Bad device with no id {device_id}')
                    continue
                device.id = device_id + (device_raw.get('name') or '')
                device.name = device_raw.get('name')
                device_info = device_raw.get('info') or {}
                hostname = device_info.get('fqdn') or device_info.get('computer_name')
                if hostname and hostname.endswith('.local'):
                    hostname = hostname[:-len('.local')]
                device.hostname = hostname
                device.part_of_domain = device_info.get('isInDomain') or False
                try:
                    device.figure_os((device_info.get('operating_system') or '') +
                                     ' ' + (device_info.get('osName') or ''))
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                domain = device_info.get('domain_name')
                if domain and 'workgroup' not in domain.lower() and 'local' not in domain.lower():
                    device.domain = domain

                aws_id = device_info.get('aws/instance_id')
                if aws_id:
                    device.cloud_id = aws_id
                    device.cloud_provider = 'AWS'
                try:
                    used_user = device_raw.get('last_user')
                    if used_user:
                        device.last_used_users = used_user.split(',')
                except Exception:
                    logger.exception(f'Problem getting users for {device_raw}')
                device.agent_version = device_info.get('softwareVersion')
                device.description = device_info.get('computer_description')
                try:
                    ip_list = (device_info.get('ipAddresses/ipv4') or []) +\
                              (device_info.get('ipAddresses/ipv6') or [])
                    if ip_list:
                        device.add_nic(None, ip_list)
                except Exception:
                    logger.exception(f'Problem getting nic for {device_raw}')
                try:
                    device.last_seen = parse_date(device_raw.get('last_activity'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Got problems with device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
