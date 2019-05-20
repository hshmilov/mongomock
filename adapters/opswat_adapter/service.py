import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field
from axonius.utils.parsing import is_domain_valid
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from opswat_adapter.connection import OpswatConnection
from opswat_adapter.client_id import get_client_id
from opswat_adapter.consts import DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class OpswatAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        severity = Field(str, 'Severity')
        device_status = Field(str, 'Status')
        device_type = Field(str, 'Device Type')
        nickname = Field(str, 'Nickname')
        agent_version = Field(str, 'Agent Version')
        group_name = Field(str, 'Group Name')
        total_cves = Field(int, 'Total CVEs')
        country = Field(str, 'Country')
        total_issue = Field(int, 'Total Issue')
        total_warning = Field(int, 'Total Warning')
        total_critical = Field(int, 'Total Critical')
        link_username = Field(str, 'Link Username')
        link_username_group = Field(str, 'Link Username Group')
        remediation_link = Field(str, 'Remediation Link')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain') or DEFAULT_DOMAIN)

    @staticmethod
    def get_connection(client_config):
        connection = OpswatConnection(domain=client_config.get('domain') or DEFAULT_DOMAIN,
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
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
                (client_config.get('domain') or DEFAULT_DOMAIN), str(e))
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
        The schema OpswatAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Opswat Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN
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
                'client_id',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('device_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('device_name') or '')
            device.hostname = device_raw.get('device_name')
            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.set_boot_time(boot_time=parse_date(device_raw.get('last_reboot')))
            device.agent_version = device_raw.get('agent_version')
            device.nickname = device_raw.get('nickname')
            device.device_type = device_raw.get('device_type')
            device.group_name = device_raw.get('group_name')
            try:
                if device_raw.get('cves') and isinstance(device_raw.get('cves').get('total'), int):
                    device.total_cves = device_raw.get('cves').get('total')
            except Exception:
                logger.exception(f'Problem getting CVEs from {device_raw}')
            try:
                if device_raw.get('geo_info') and isinstance(device_raw.get('geo_info').get('country'), str):
                    device.country = device_raw.get('geo_info').get('country')
            except Exception:
                logger.exception(f'Problem getting country from {device_raw}')

            issue_info = device_raw.get('issue')
            if issue_info and isinstance(issue_info, dict):
                try:
                    if isinstance(issue_info.get('total_issue'), int):
                        device.total_issue = issue_info.get('total_issue')
                    if isinstance(issue_info.get('total_warning'), int):
                        device.total_warning = issue_info.get('total_warning')
                    if isinstance(issue_info.get('total_critical'), int):
                        device.total_critical = issue_info.get('total_critical')
                except Exception:
                    logger.exception(f'Problem getting issue for {device_raw}')

            try:
                os_info = device_raw.get('os_info')
                if os_info and isinstance(os_info, dict):
                    device.figure_os((os_info.get('family') or '') + ' ' +
                                     (os_info.get('name') or '') + ' ' + (os_info.get('version') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            nics = device_raw.get('network_info')
            if isinstance(nics, list):
                for nic in nics:
                    try:
                        mac = nic.get('mac')
                        if not mac:
                            mac = None
                        ips = []
                        if nic.get('ipv4') and 'N/A' not in nic.get('ipv4'):
                            ips.append(nic.get('ipv4'))
                        if nic.get('ipv6') and 'N/A' not in nic.get('ipv6'):
                            ips.append(nic.get('ipv6'))
                        if not ips:
                            ips = None
                        if mac or ips:
                            device.add_nic(mac, ips)
                    except Exception:
                        logger.exception(f'Problem getting nic for {nic}')
            user_info = device_raw.get('user_info')
            if user_info and isinstance(user_info, dict):
                try:
                    username = user_info.get('username')
                    domain = user_info.get('domain')
                    if not is_domain_valid(domain):
                        domain = None
                    if username:
                        if domain:
                            if '.' in domain:
                                username = f'{username}.{domain}'
                            else:
                                username = f'{domain}\\{username}'
                        device.last_used_users = [username]
                except Exception:
                    logger.exception(f'Problem getting user info for {device_raw}')
            device.severity = device_raw.get('severity')
            device.device_status = device_raw.get('status')
            device.remediation_link = device_raw.get('remediation_link')
            link_user = device_raw.get('link_user')
            if link_user and isinstance(link_user, dict):
                try:
                    device.link_username = link_user.get('username')
                    device.link_username_group = link_user.get('group')
                except Exception:
                    logger.exception(f'Problem getting link user info for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Opswat Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
