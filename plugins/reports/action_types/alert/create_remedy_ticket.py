import logging

from axonius.consts import report_consts
from axonius.clients.remedy.connection import RemedyConnection
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')


class RemedyTicketAction(ActionTypeAlert):
    """
    Creates an incident in the Remedy account
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'BMC Helix Remedy Domain',
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
                    'name': 'form_name',
                    'title': 'Form Name',
                    'type': 'string'
                },
                {
                    'name': 'ticket_description',
                    'title': 'Ticket Description',
                    'type': 'string',
                    'format': 'text'
                },
                {
                    'name': 'description_default',
                    'title': 'Add Ticket Description Default',
                    'type': 'bool'
                },
                {
                    'name': 'priority',
                    'title': 'Priority',
                    'type': 'string'
                }
            ],
            'required': [
                'description_default',
                'ticket_description',
                'domain',
                'username',
                'password',
                'form_name',
                'priority',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'description_default': False,
            'ticket_description': None,
            'domain': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'verify_ssl': True,
            'form_name': None,
            'priority': None
        }

    def _create_remedy_ticket(self, form_name, description, priority):
        remedy_dict = {'Description': description,
                       'Priority': priority}
        try:
            if not self._config.get('domain') or not self._config.get('username') or not self._config.get('password'):
                return 'Missing Parameters For Connection'
            remedy_connection = RemedyConnection(domain=self._config['domain'],
                                                 verify_ssl=self._config.get('verify_ssl'),
                                                 username=self._config.get('username'),
                                                 password=self._config.get('password'),
                                                 https_proxy=self._config.get('https_proxy'))
            with remedy_connection:
                remedy_connection.create_ticket(form_name=form_name,
                                                ticket_body=remedy_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating Remedy ticket wiht {remedy_dict}')
            return f'Got exception creating Remedy incident: {str(e)}'

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
        log_message_full = self._config['ticket_description']
        if self._config.get('description_default') is True:
            log_message_full += '\n' + log_message
        message = self._create_remedy_ticket(form_name=self._config['form_name'],
                                             description=log_message_full,
                                             priority=self._config['priority'])
        return AlertActionResult(not message, message or 'Success')
