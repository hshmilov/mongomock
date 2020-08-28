import logging

from axonius.types.enforcement_classes import EntitiesResult
import axonius.clients.nexpose as nexpose_clients
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, add_node_selection, add_node_default
from reports.action_types.base.ips_scans_utils import get_ips_from_view

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'nexpose_adapter'


class Rapid7AddIPsToSite(ActionTypeBase):
    '''
    Add ips to rapid 7 site
    '''

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Rapid7 adapter',
                    'type': 'bool'
                },
                {
                    'name': 'host',
                    'title': 'Rapid7 domain',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port'
                },
                {
                    'name': 'username',
                    'title': 'User name',
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
                    'title': 'HTTPS proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS proxy user name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS proxy password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'site_name',
                    'title': 'Site name',
                    'type': 'string'
                },
                {
                    'name': 'use_public_ips',
                    'title': 'Use public IP addresses',
                    'type': 'bool'},
                {
                    'name': 'use_private_ips',
                    'title': 'Use private IP addresses',
                    'type': 'bool'
                },
                {
                    'name': 'exclude_ipv6',
                    'title': 'Exclude IPv6 addresses',
                    'type': 'bool'
                },
                {
                    'name': 'cidr_exclude_list',
                    'type': 'string',
                    'title': 'CIDRs exclude list'
                }
            ],
            'required': [
                'verify_ssl',
                'site_name',
                'use_private_ips',
                'use_public_ips',
                'use_adapter',
                'exclude_ipv6'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'site_name': None,
            'use_private_ips': True,
            'cidr_exclude_list': None,
            'use_public_ips': True,
            'use_adapter': True,
            'verify_ssl': False,
            'exclude_ipv6': False,
            'host': None,
            'https_proxy': None,
            'proxy_password': None,
            'proxy_username': None,
            'username': None,
            'password': None
        })

    # pylint: disable=R0912,R0914,R0915,R1702,W0212
    def _run(self) -> EntitiesResult:
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(
            ADAPTER_NAME, self.action_node_id)
        current_result = self._get_entities_from_view({
            'adapters.data.network_interfaces.ips': 1,
            'internal_axon_id': 1
        })
        ips, results = get_ips_from_view(current_result,
                                         self._config['use_public_ips'],
                                         self._config['use_private_ips'],
                                         self._config.get('exclude_ipv6') or False,
                                         cidr_exclude_list=self._config.get('cidr_exclude_list'))
        site_name = self._config['site_name']
        rapid7_dict = {'ips': list(ips), 'site_name': site_name}
        if self._config['use_adapter'] is True:
            response = self._plugin_base.request_remote_plugin('add_ips_to_site', adapter_unique_name,
                                                               'post', json=rapid7_dict)
            if response and response.status_code == 200:
                return results
            if response and response.status_code == 500:
                return generic_fail(self._internal_axon_ids, reason=response.data.message)
            return generic_fail(self._internal_axon_ids)
        try:
            if not self._config.get('host') or not self._config.get('username') or not self._config.get('password') \
                    or not self._config.get('port'):
                return generic_fail(self._internal_axon_ids, reason='Missing Parameters For Connection')
            num_of_simultaneous_devices = 50
            conn = nexpose_clients.NexposeV3Client(num_of_simultaneous_devices, host=self._config['host'],
                                                   port=self._config['port'],
                                                   username=self._config['username'],
                                                   password=self._config['password'],
                                                   verify_ssl=self._config['verify_ssl'],
                                                   token=None,
                                                   https_proxy=self._config.get('https_proxy'),
                                                   proxy_username=self._config.get('proxy_username'),
                                                   proxy_password=self._config.get('proxy_password'),
                                                   )
            conn.add_ips_to_site(rapid7_dict)
            return results
        except Exception as e:
            logger.exception(f'Got exception creating Tenable asset')
            return generic_fail(self._internal_axon_ids, reason=f'Got exception adding ips to Rapid7 site '
                                                                f': {str(e)}')
