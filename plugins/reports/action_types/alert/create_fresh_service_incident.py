import logging

from axonius.consts import report_consts
from axonius.clients.fresh_service.connection import FreshServiceConnection
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')

FRESH_SERVICE_PRIORITY = {
    'low': 1,
    'medium': 2,
    'high': 3,
    'urgent': 4
}


class FreshServiceIncidentAction(ActionTypeAlert):
    """
    Creates an incident in the fresh_service account
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'subject',
                    'title': 'Subject',
                    'type': 'string'
                },
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
                    'name': 'ticket_email',
                    'title': 'Ticket Email',
                    'type': 'string'
                },
                {
                    'name': 'priority',
                    'title': 'Priority',
                    'type': 'string',
                    'enum': FRESH_SERVICE_PRIORITY.keys()
                },
                {
                    'name': 'domain',
                    'title': 'Freshservice Domain',
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
                'use_adapter', 'domain', 'apikey'
                'description_default', 'ticket_email',
                'incident_description', 'subject',
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
            'apikey': None,
            'https_proxy': None,
            'subject': None,
            'verify_ssl': True,
            'ticket_email': None
        }

    def _create_fresh_service_incident(self, description, subject, ticket_email, priority):
        fresh_service_dict = {'subject': subject,
                              'description': description,
                              'email': ticket_email,
                              'priority': priority,
                              'status': 2
                              }
        try:
            if not self._config.get('domain') or not self._config.get('apikey'):
                return 'Missing Parameters For Connection'
            fresh_service_connection = FreshServiceConnection(domain=self._config['domain'],
                                                              verify_ssl=self._config.get('verify_ssl'),
                                                              apikey=self._config.get('apikey'),
                                                              https_proxy=self._config.get('https_proxy'))
            with fresh_service_connection:
                fresh_service_connection.create_ticket(fresh_service_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating fresh_service incident wiht {fresh_service_dict}')
            return f'Got exception creating fresh_service incident: {str(e)}'

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
        message = self._create_fresh_service_incident(description=log_message_full,
                                                      subject=self._config['subject'],
                                                      priority=FRESH_SERVICE_PRIORITY.get(self._config['priority']),
                                                      ticket_email=self._config['ticket_email'],)
        return AlertActionResult(not message, message or 'Success')
