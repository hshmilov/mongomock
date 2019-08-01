import logging

from axonius.consts import report_consts
from axonius.types.enforcement_classes import AlertActionResult
from axonius.clients.zendesk.connection import ZendeskConnection
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')


class ZendeskTicketAction(ActionTypeAlert):
    """
    Creates an incident in the ServiceNow account
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Zendesk Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name Email',
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
                    'name': 'ticket_subject',
                    'title': 'Ticket Subject',
                    'type': 'string'
                },
                {
                    'name': 'ticket_body',
                    'title': 'Ticket Body',
                    'type': 'string'
                },
                {
                    'name': 'description_default',
                    'title': 'Add Incident Description Default',
                    'type': 'bool'
                },
                {
                    'name': 'priority',
                    'title': 'Priority',
                    'type': 'string'
                }
            ],
            'required': [
                'ticket_body',
                'ticket_subject',
                'verify_ssl',
                'password',
                'username',
                'domain',
                'description_default'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'domain': None,
            'username': None,
            'password': None,
            'description_default': False,
            'verify_ssl': True,
            'https_proxy': None,
            'ticket_subject': None,
            'ticket_body': None,
            'priority': None
        }

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
        ticket_body = self._config['ticket_body']
        if self._config.get('description_default') is True:
            ticket_body += '\n' + log_message
        connection = ZendeskConnection(domain=self._config['domain'],
                                       username=self._config['username'],
                                       password=self._config['password'],
                                       verify_ssl=self._config['verify_ssl'],
                                       https_proxy=self._config.get('https_proxy'))
        message = connection.create_ticket(ticket_subject=self._config['ticket_subject'],
                                           priority=self._config.get('priority'),
                                           ticket_body=ticket_body)
        return AlertActionResult(not message, message or 'Success')
