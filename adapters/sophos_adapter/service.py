# pylint: disable=too-many-instance-attributes
import hashlib
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import ListField
from sophos_adapter.connection import SophosConnection

logger = logging.getLogger(f'axonius.{__name__}')


class SophosAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        assigned_products = ListField(str, 'Assigned Products')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, config_file_path=get_local_config_file(__file__), **kwargs)

    def _get_client_id(self, client_config):
        api_declassified = hashlib.md5(client_config['authorization'].encode('utf-8')).hexdigest()
        api_declassified_2 = hashlib.md5(client_config['apikey'].encode('utf-8')).hexdigest()
        return client_config['domain'] + '_' + api_declassified + '_' + api_declassified_2

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

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

    # pylint: disable=R0912,R0915
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw['id']
                device_info = device_raw.get('info') or {}
                if not device_id:
                    logger.warning(f'Bad device with no id {device_id}')
                    continue
                hostname = device_info.get('fqdn') or device_info.get('computer_name')
                device.id = device_id + '_' + (device_raw.get('name') or '') + '_' + (hostname or '')
                device.name = device_raw.get('name')
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
                    if used_user and used_user.lower() != 'n/a':
                        device.last_used_users = used_user.split(',')
                except Exception:
                    logger.exception(f'Problem getting users for {device_raw}')
                    device.add_agent_version(agent=AGENT_NAMES.sophos,
                                             version=device_info.get('softwareVersion'))
                device.description = device_info.get('computer_description')
                try:
                    ipv4 = device_info.get('ipAddresses/ipv4') or []
                    if isinstance(ipv4, list):
                        ipv4 = [ip.strip() for ip in ipv4 if (ip and ip.strip())]
                    else:
                        ipv4 = []
                    ipv6 = device_info.get('ipAddresses/ipv6') or []
                    if isinstance(ipv6, list):
                        ipv6 = [ip.strip() for ip in ipv6 if (ip and ip.strip())]
                    else:
                        ipv6 = []
                    ip_list = ipv4 + ipv6
                    macs = device_info.get('macAddresses')
                    if not isinstance(macs, list):
                        macs = None
                    if ip_list:
                        device.add_ips_and_macs(macs=macs, ips=ip_list)
                except Exception:
                    logger.exception(f'Problem getting nic for {device_raw}')
                try:
                    device.last_seen = parse_date(device_raw.get('last_activity'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                device.assigned_products = device_raw.get('assignedProducts')\
                    if isinstance(device_raw.get('assignedProducts'), list) else None
                device.device_serial = device_info.get('serialNumber')
                device.first_seen = parse_date(device_raw.get('registered_at'))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Got problems with device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
