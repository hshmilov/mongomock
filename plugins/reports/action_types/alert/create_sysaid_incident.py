import logging

from axonius.consts import report_consts
from axonius.clients.sysaid.connection import SysaidConnection
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert
from reports.action_types.action_type_base import add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'sysaid_adapter'

# pylint: disable=W0212


class SysaidIncidentAction(ActionTypeAlert):
    """
    Creates an incident in the Sysaid account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Sysaid adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Sysaid domain',
                    'type': 'string'
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
                    'name': 'incident_description',
                    'title': 'Incident description',
                    'type': 'string',
                    'format': 'text'
                },
                {
                    'name': 'description_default',
                    'title': 'Add default incident description',
                    'type': 'bool'
                },

            ],
            'required': [
                'use_adapter',
                'verify_ssl',
                'description_default',
                'incident_description',
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'description_default': False,
            'incident_description': None,
            'use_adapter': False,
            'domain': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'verify_ssl': True
        })

    def _create_sysaid_incident(self, description):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        sysaid_dict = {'description': description}
        try:
            if self._config['use_adapter'] is True:
                response = self._plugin_base.request_remote_plugin('create_incident', adapter_unique_name, 'post',
                                                                   json=sysaid_dict)
                return response.text
            if not self._config.get('domain') or not self._config.get('username') or not self._config.get('password'):
                return 'Missing Parameters For Connection'
            sysaid_connection = SysaidConnection(domain=self._config['domain'],
                                                 verify_ssl=self._config.get('verify_ssl'),
                                                 username=self._config.get('username'),
                                                 password=self._config.get('password'),
                                                 https_proxy=self._config.get('https_proxy'))
            with sysaid_connection:
                sysaid_connection.create_sysaid_incident(sysaid_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating Sysaid incident wiht {sysaid_dict}')
            return f'Got exception creating Sysaid incident: {str(e)}'

    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')
        old_results_num_of_devices = len(self._internal_axon_ids) + len(self._removed_axon_ids) - \
            len(self._added_axon_ids)
        log_message = report_consts.REPORT_CONTENT.format(name=self._report_data['name'],
                                                          query=self.trigger_view_name,
                                                          num_of_triggers=self._run_configuration.times_triggered,
                                                          trigger_message=self._get_trigger_description(),
                                                          num_of_current_devices=len(self._internal_axon_ids),
                                                          old_results_num_of_devices=old_results_num_of_devices,
                                                          query_link=self._generate_query_link())
        log_message_full = self._config['incident_description']
        if self._config.get('description_default') is True:
            log_message_full += '\n' + log_message
        message = self._create_sysaid_incident(log_message_full)
        return AlertActionResult(not message, message or 'Success')
