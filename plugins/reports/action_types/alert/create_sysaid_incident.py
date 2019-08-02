import logging

from axonius.consts import report_consts
from axonius.clients.sysaid.connection import SysaidConnection
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')


class SysaidIncidentAction(ActionTypeAlert):
    """
    Creates an incident in the Sysaid account
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'incident_description',
                    'title': 'Incident Description',
                    'type': 'string',
                    'format': 'text'
                },
                {
                    'name': 'description_default',
                    'title': 'Add Incident Description Default',
                    'type': 'bool'
                },
                {
                    'name': 'use_adapter',
                    'title': 'Use Sysaid Adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Sysaid Domain',
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
                'use_adapter',
                'description_default',
                'incident_description',
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'description_default': False,
            'incident_description': None,
            'use_adapter': False,
            'domain': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'verify_ssl': True
        }

    def _create_sysaid_incident(self, description):
        sysaid_dict = {'description': description}
        try:
            if self._config['use_adapter'] is True:
                response = self._plugin_base.request_remote_plugin('create_incident', 'sysaid_adapter', 'post',
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
        query_name = self._run_configuration.view.name
        old_results_num_of_devices = len(self._internal_axon_ids) + len(self._removed_axon_ids) - \
            len(self._added_axon_ids)
        log_message = report_consts.REPORT_CONTENT.format(name=self._report_data['name'],
                                                          query=query_name,
                                                          num_of_triggers=self._run_configuration.times_triggered,
                                                          trigger_message=self._get_trigger_description(),
                                                          num_of_current_devices=len(self._internal_axon_ids),
                                                          old_results_num_of_devices=old_results_num_of_devices,
                                                          query_link=self._generate_query_link(query_name))
        log_message_full = self._config['incident_description']
        if self._config.get('description_default') is True:
            log_message_full += '\n' + log_message
        message = self._create_sysaid_incident(log_message_full)
        return AlertActionResult(not message, message or 'Success')
