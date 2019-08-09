import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from axonius.utils.parsing import is_domain_valid
from symantec_adapter import consts
from symantec_adapter.connection import SymantecConnection

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecAdapter(AdapterBase):

    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        client_id = Field(str, 'SEP Server Details')
        online_status = Field(str, 'Online Status')
        cids_defset_version = Field(str, 'Definition Set Version')
        last_scan_date = Field(datetime.datetime, 'Last Scan Date')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain'] + '_' + client_config['username'] + '_' + \
            (client_config.get('username_domain') or '')

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'), client_config.get('port'))

    def _connect_client(self, client_config):
        try:
            connection = SymantecConnection(domain=client_config['domain'],
                                            port=client_config.get('port') or consts.DEFAULT_SYMANTEC_PORT,
                                            verify_ssl=client_config['verify_ssl'],
                                            username=client_config['username'], password=client_config['password'],
                                            username_domain=(client_config.get('username_domain') or ''),
                                            https_proxy=client_config.get('https_proxy'),
                                            url_base_prefix='sepm/api/v1/',
                                            headers={'Content-Type': 'application/json'})
            with connection:
                pass  # check that the connection credentials are valid
            return connection, self._get_client_id(client_config)
        except RESTException as e:
            message = 'Error connecting to client with address {0} and port {1}, reason: {2}'.format(
                client_config['domain'], str(client_config.get('port', consts.DEFAULT_SYMANTEC_PORT)), str(e))
            logger.exception(message)
            message = message[:300]
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Symantec domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Symantec connection

        :return: A json with all the attributes returned from the Symantec Server
        """
        connection, client_id = client_data
        with connection:
            for device_raw in connection.get_device_list():
                yield device_raw, client_id

    def _clients_schema(self):
        """
        The schema SymantecAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Symantec Endpoint Protection Server',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'description': 'Symantec Endpoint Protection Port (Default is 8446)',
                    'type': 'integer',
                    'format': 'port'
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
                    'name': 'username_domain',
                    'title': 'Domain',
                    'type': 'string'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS proxy',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, client_id in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.client_id = client_id
                domain_strip_upper = str(device_raw.get('domainOrWorkgroup', '')).strip().upper()
                computer_name = device_raw.get('computerName') or ''
                if not any(elem in computer_name for elem in [' ', '.']) or \
                        ('Mac' not in str(device_raw.get('operatingSystem'))):
                    device.hostname = computer_name
                    if not is_domain_valid(device_raw.get('domainOrWorkgroup')):
                        # Special case for workgroup
                        if computer_name.upper().endswith('.LOCAL'):
                            computer_name = computer_name[:-len('.LOCAL')]
                        device.hostname = computer_name
                    else:
                        device.hostname = computer_name + '.' + (device_raw.get('domainOrWorkgroup') or '')
                else:
                    device.name = computer_name
                    host_no_spaces_list = device.name.replace(' ', '-').split('-')
                    host_no_spaces_list[0] = ''.join(char for char in host_no_spaces_list[0] if char.isalnum())
                    if len(host_no_spaces_list) > 1:
                        host_no_spaces_list[1] = ''.join(char for char in host_no_spaces_list[1] if char.isalnum())
                    hostname = '-'.join(host_no_spaces_list).split('.')[0]
                    device.hostname = hostname
                if is_domain_valid(device_raw.get('domainOrWorkgroup')):
                    device.domain = device_raw.get('domainOrWorkgroup')
                device.figure_os(' '.join([device_raw.get('operatingSystem', ''),
                                           str(device_raw.get('osbitness', '')),
                                           str(device_raw.get('osversion', '')),
                                           str(device_raw.get('osmajor', '')),
                                           str(device_raw.get('osminor', ''))]))
                mac_addresses = device_raw.get('macAddresses') or []
                ip_addresses = device_raw.get('ipAddresses') or []
                device.add_ips_and_macs(mac_addresses, ip_addresses)
                device.online_status = str(device_raw.get('onlineStatus'))
                device.add_agent_version(agent=AGENT_NAMES.symantec, version=device_raw.get('agentVersion'))
                try:
                    device.last_seen = datetime.datetime.fromtimestamp(max(int(device_raw.get('lastScanTime', 0)),
                                                                           int(device_raw.get('lastUpdateTime', 0)))
                                                                       / 1000)
                except Exception:
                    logger.exception('Problem adding last seen to Symantec')
                device.id = device_raw['agentId'] + '_' + computer_name
                try:
                    if device_raw.get('logonUserName'):
                        if device_raw.get('loginDomain') and is_domain_valid(device_raw.get('loginDomain')):
                            if '.' not in device_raw.get('loginDomain'):
                                device.last_used_users = [device_raw.get('loginDomain') +
                                                          '\\' + device_raw.get('logonUserName')]
                            else:
                                device.last_used_users = [device_raw.get('logonUserName') +
                                                          '@' + device_raw.get('loginDomain')]
                        else:
                            device.last_used_users = [device_raw.get('logonUserName')]
                except Exception:
                    logger.exception(f'Problem adding user to {device_raw}')
                device.cids_defset_version = device_raw.get('cidsDefsetVersion')
                try:
                    if isinstance(device_raw.get('lastScanTime'), int):
                        device.last_scan_date = datetime.datetime.fromtimestamp(device_raw.get('lastScanTime') / 1000)
                except Exception:
                    logger.exception(f'Problem adding last scan date')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device to SEP {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
