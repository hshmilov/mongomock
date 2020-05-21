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
                    'name': 'domain',
                    'title': 'Freshservice domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API key',
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
                    'name': 'subject',
                    'title': 'Subject',
                    'type': 'string'
                },
                {
                    'name': 'incident_description',
                    'title': 'Ticket description',
                    'type': 'string',
                    'format': 'text'
                },
                {
                    'name': 'description_default',
                    'title': 'Add default ticket description',
                    'type': 'bool'
                },
                {
                    'name': 'ticket_email',
                    'title': 'Ticket requester email',
                    'type': 'string'
                },
                {
                    'name': 'priority',
                    'title': 'Priority',
                    'type': 'string',
                    'enum': FRESH_SERVICE_PRIORITY.keys()
                },
                {
                    'name': 'group_id',
                    'type': 'integer',
                    'title': 'Group ID'
                }
            ],
            'required': [
                'domain', 'apikey', 'priority',
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
            'domain': None,
            'apikey': None,
            'https_proxy': None,
            'subject': None,
            'priority': 'low',
            'verify_ssl': True,
            'ticket_email': None,
            'group_id': None
        }

    def _create_fresh_service_incident(self, description, subject, ticket_email, priority, group_id):
        fresh_service_dict = {'subject': subject,
                              'description': description,
                              'email': ticket_email,
                              'priority': priority,
                              'status': 2
                              }
        if group_id:
            fresh_service_dict['group_id'] = group_id
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
        message = self._create_fresh_service_incident(description=log_message_full,
                                                      subject=self._config['subject'],
                                                      priority=FRESH_SERVICE_PRIORITY.get(self._config['priority']),
                                                      ticket_email=self._config['ticket_email'],
                                                      group_id=self._config.get('group_id'))
        return AlertActionResult(not message, message or 'Success')
