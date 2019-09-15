import ipaddress
import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.parsing import is_domain_valid
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from kaspersky_sc_adapter.connection import KasperskyScConnection
from kaspersky_sc_adapter.client_id import get_client_id
from kaspersky_sc_adapter.consts import STATUSES_LIST, HOST_STATUSES_LIST

logger = logging.getLogger(f'axonius.{__name__}')


class KasperskyScAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        last_full_scan = Field(datetime.datetime, 'Last Full Scan')
        virus_count = Field(int, 'Virus Count')
        agent_status = ListField(str, 'Agent Status', enum=STATUSES_LIST)
        host_status = ListField(str, 'Host Status', enum=HOST_STATUSES_LIST)

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
        connection = KasperskyScConnection(domain=client_config['domain'],
                                           verify_ssl=client_config['verify_ssl'],
                                           https_proxy=client_config.get('https_proxy'),
                                           username=client_config['username'],
                                           password=client_config['password'])
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
        The schema KasperskyScAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Kaspersky Security Center Domain',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = (device_raw.get('value') or {}).get('KLHST_WKS_HOSTNAME')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + ((device_raw.get('value') or {}).get('KLHST_WKS_FQDN') or '')
            device_value = (device_raw.get('value') or {})
            hostname = device_value.get('KLHST_WKS_FQDN')
            try:
                host_status = device_value.get('KLHST_WKS_STATUS')
                if not host_status or not isinstance(host_status, int):
                    host_status = 0
                if host_status & (2**0):
                    device.host_status.append('Visible')
                elif host_status & (2**2):
                    device.host_status.append('Network Agent is installed')
                elif host_status & (2**3):
                    device.host_status.append('Network Agent is Alive')
                elif host_status & (2**4):
                    device.host_status.append('Real-time protection is installed')
                elif host_status & (2**5):
                    device.host_status.append('Computer has been temporarily switched into current server')
            except Exception:
                logger.exception(f'Problem with status for {device_raw}')
            try:
                status = device_value.get('KLHST_WKS_STATUS_MASK')
                if not status or not isinstance(status, int):
                    status = 0
                if status & (2**0):
                    device.agent_status.append('Host with Network Agent installed is online but network agent is '
                                               'inactive')
                elif status & (2**1):
                    device.agent_status.append('Anti-virus application is installed but real-time protection is not '
                                               'running')
                elif status & (2**2):
                    device.agent_status.append('Anti-virus application is installed but not running')
                elif status & (2**3):
                    device.agent_status.append('Number of viruses detected is too much')
                elif status & (2**4):
                    device.agent_status.append('Anti-virus application is installed but real-time protection status '
                                               'differs from one set by the security administrator')
                elif status & (2**5):
                    device.agent_status.append('Anti-virus application is not installed')
                elif status & (2**6):
                    device.agent_status.append('Full scan for viruses performed too long ago')
                elif status & (2**7):
                    device.agent_status.append('Anti-virus bases were updated too long ago')
                elif status & (2**8):
                    device.agent_status.append('Network agent is inactive too long')
                elif status & (2**9):
                    device.agent_status.append('Old license (supported by Administration Server 7.0 or higher)')
                elif status & (2**10):
                    device.agent_status.append('Number of uncured objects is too much '
                                               '(supported by Administration Server 7.0 or higher)')
                elif status & (2**11):
                    device.agent_status.append('Reboot is required')
                elif status & (2**12):
                    device.agent_status.append('One or more incompatible applications are installed on the host')
                elif status & (2**13):
                    device.agent_status.append('Host has one or more vulnerabilities')
                elif status & (2**14):
                    device.agent_status.append('Last search for updates has been performed too long ago on the host')
                elif status & (2**15):
                    device.agent_status.append('The host does not have proper encryption status')
                elif status & (2**16):
                    device.agent_status.append('Mobile device settings does not meet requirements '
                                               'of the security policy')
            except Exception:
                logger.exception(f'Problem with status for {device_raw}')
            if not hostname:
                return None
            device.hostname = hostname
            device_details = device_raw.get('details')
            if not device_details:
                device_details = {}
            device.figure_os(device_details.get('KLHST_WKS_OS_NAME'))
            try:
                domain = device_value.get('KLHST_WKS_WINDOMAIN')
                if is_domain_valid(domain):
                    device.domain = domain
            except Exception:
                logger.exception(f'Problem with domain for {device_raw}')
            try:
                device.last_full_scan = parse_date((device_details.get('KLHST_WKS_LAST_FULLSCAN') or {}).get('value'))
            except Exception:
                logger.exception(f'Problem getting last full scan for {device_raw}')

            try:
                device.last_seen = parse_date((device_value.get('KLHST_WKS_LAST_VISIBLE') or {}).get('value'))
            except Exception:
                logger.exception(f'Problem getting last full scan for {device_raw}')

            try:
                ips = (device_value.get('KLHST_WKS_IP_LONG') or {}).get('value')
                if ips and ipaddress.ip_address(ips):
                    device.add_nic(ips=[str(ipaddress.ip_address(ips))])
            except Exception:
                logger.exception(f'Problem getting nic for {device_raw}')
            try:
                virus_count = (device_details.get('KLHST_WKS_VIRUS_COUNT') or {}).get('value')
                if virus_count:
                    device.virus_count = int(virus_count)
            except Exception:
                logger.exception(f'Problem getting virus count for {device_raw}')
            try:
                apps_raw = device_raw.get('apps') or []
                for sw_name in apps_raw:
                    try:
                        sw_version = apps_raw[sw_name].get('version')
                        device.add_installed_software(name=sw_name,
                                                      version=sw_version)
                    except Exception:
                        logger.exception(f'Problem with sw {sw_name}')

            except Exception:
                logger.exception(f'Problem getting sw data for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching KasperskySc Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
