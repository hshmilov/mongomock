import logging

from axonius.consts import report_consts
from axonius.types.enforcement_classes import AlertActionResult
from axonius.clients.service_now.connection import ServiceNowConnection
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowIncidentAction(ActionTypeAlert):
    """
    Creates an incident in the ServiceNow account
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use ServiceNow Adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'ServiceNow Domain',
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
                },
                {
                    'name': 'incident_title',
                    'title': 'Incident Short Description',
                    'type': 'string'
                },
                {
                    'name': 'severity',
                    'title': 'Message Severity',
                    'type': 'string',
                    'enum': [
                        'info', 'warning', 'error'
                    ]
                },
                {
                    'name': 'incident_description',
                    'title': 'Incident Description',
                    'type': 'string'
                },
                {
                    'name': 'description_default',
                    'title': 'Add Incident Description Default',
                    'type': 'bool'
                },
                {
                    'name': 'u_incident_type',
                    'type': 'string',
                    'title': 'Incident Type'
                },
            ],
            'required': [
                'description_default',
                'incident_description',
                'severity',
                'incident_title'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'severity': 'info',
            'description_default': False,
            'incident_description': None,
            'incident_title': None,
            'use_adapter': False,
            'domain': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'verify_ssl': True
        }

    def _create_service_now_incident(self, short_description, description, impact, u_incident_type):
        service_now_dict = {'short_description': short_description,
                            'description': description,
                            'impact': impact,
                            'u_incident_type': u_incident_type}
        try:
            if self._config['use_adapter'] is True:
                response = self._plugin_base.request_remote_plugin('create_incident', 'service_now_adapter', 'post',
                                                                   json=service_now_dict)
                return response.text
            if not self._config.get('domain') or not self._config.get('username') or not self._config.get('password'):
                return 'Missing Parameters For Connection'
            service_now_connection = ServiceNowConnection(domain=self._config['domain'],
                                                          verify_ssl=self._config.get('verify_ssl'),
                                                          username=self._config.get('username'),
                                                          password=self._config.get('password'),
                                                          https_proxy=self._config.get('https_proxy'))
            with service_now_connection:
                service_now_connection.create_service_now_incident(service_now_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating ServiceNow incident wiht {service_now_dict}')
            return f'Got exception creating ServiceNow incident: {str(e)}'

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
        impact = report_consts.SERVICE_NOW_SEVERITY.get(self._config['severity'],
                                                        report_consts.SERVICE_NOW_SEVERITY['error'])
        log_message_full = self._config['incident_description']
        if self._config.get('description_default') is True:
            log_message_full += '\n' + log_message
        message = self._create_service_now_incident(short_description=self._config['incident_title'],
                                                    description=log_message,
                                                    impact=impact,
                                                    u_incident_type=self._config.get('u_incident_type'))
        return AlertActionResult(not message, message or 'Success')
