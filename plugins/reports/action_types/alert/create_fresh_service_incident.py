import logging

from axonius.consts import report_consts
from axonius.clients.fresh_service.connection import FreshServiceConnection
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_base import add_node_selection, add_node_default
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')

FRESH_SERVICE_PRIORITY = {
    'low': 1,
    'medium': 2,
    'high': 3,
    'urgent': 4
}


ADAPTER_NAME = 'fresh_service_adapter'
# pylint: disable=W0212


class FreshServiceIncidentAction(ActionTypeAlert):
    """
    Creates an incident in the fresh_service account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Fresh Service adapter',
                    'type': 'bool'
                },
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
                    'enum': list(FRESH_SERVICE_PRIORITY.keys())
                },
                {
                    'name': 'group_name',
                    'type': 'string',
                    'title': 'Group name'
                }
            ],
            'required': [
                'use_adapter', 'priority', 'verify_ssl',
                'description_default', 'ticket_email',
                'incident_description', 'subject',
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'description_default': False,
            'incident_description': None,
            'domain': None,
            'apikey': None,
            'https_proxy': None,
            'subject': None,
            'priority': 'low',
            'verify_ssl': True,
            'ticket_email': None,
            'group_name': None,
            'use_adapter': False
        })

    def _create_fresh_service_incident(self, description, subject, ticket_email, priority, group_name,
                                       adapter_unique_name):
        fresh_service_dict = {'subject': subject,
                              'description': description,
                              'email': ticket_email,
                              'priority': priority,
                              'status': 2
                              }
        try:
            if self._config.get('use_adapter') is True:
                fresh_service_dict['group_name'] = group_name
                response = self._plugin_base.request_remote_plugin('create_ticket', adapter_unique_name, 'post',
                                                                   json=fresh_service_dict)
                return response.text
            if not self._config.get('domain') or not self._config.get('apikey'):
                return 'Missing Parameters For Connection'
            fresh_service_connection = FreshServiceConnection(domain=self._config['domain'],
                                                              verify_ssl=self._config.get('verify_ssl'),
                                                              apikey=self._config.get('apikey'),
                                                              https_proxy=self._config.get('https_proxy'))
            with fresh_service_connection:
                fresh_service_connection.create_ticket(fresh_service_dict, group_name=group_name)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating fresh_service incident wiht {fresh_service_dict}')
            return f'Got exception creating fresh_service incident: {str(e)}'

    def _run(self) -> AlertActionResult:
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
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
                                                      group_name=self._config.get('group_name'),
                                                      adapter_unique_name=adapter_unique_name)
        return AlertActionResult(not message, message or 'Success')
