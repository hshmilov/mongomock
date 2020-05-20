import logging

from axonius.consts import report_consts
from axonius.types.enforcement_classes import AlertActionResult
from axonius.clients.opsgenie.consts import OPSGENIE_PRIORITIES
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')


class OpsgenieCreateAlert(ActionTypeAlert):
    """
    Creates an alert in Opsgenie
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'message',
                    'title': 'Alert message (up to 130 characters)',
                    'type': 'string',
                    'format': 'text',
                    'limit': 130
                },
                {
                    'name': 'description_default',
                    'title': 'Add default incident description',
                    'type': 'bool'
                },
                {
                    'name': 'priority',
                    'title': 'Priority',
                    'type': 'string',
                    'enum': OPSGENIE_PRIORITIES,
                },
                {
                    'name': 'tags',
                    'title': 'Tags',
                    'type': 'string'
                },
                {
                    'name': 'alias',
                    'title': 'Alias',
                    'type': 'string'
                },
                {
                    'name': 'user',
                    'title': 'User',
                    'type': 'string'
                },
                {
                    'name': 'description',
                    'title': 'Description',
                    'type': 'string',
                    'format': 'text',
                    'limit': 15000
                },
                {
                    'name': 'note',
                    'title': 'Note',
                    'type': 'string',
                    'format': 'text',
                    'limit': 25000
                },
                {
                    'name': 'source',
                    'title': 'Source',
                    'type': 'string'
                }
            ],
            'required': [
                'description_default',
                'priority',
                'message',
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'domain': None,
            'apikey': None,
            'description_default': False,
            'verify_ssl': True,
            'https_proxy': None,
            'priority': 'P3',
            'tags': None,
            'alias': None,
            'user': None,
            'note': None,
            'source': None
        }

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
        description = self._config.get('description') or ''
        if self._config.get('description_default') is True:
            description += '\n' + log_message
        connection = PluginBase.Instance.get_opsgenie_connection()
        if connection:
            with connection:
                message = connection.create_alert(message=self._config['message'],
                                                  priority=self._config.get('priority'),
                                                  description=description,
                                                  tags=self._config.get('tags'),
                                                  alias=self._config.get('alias'),
                                                  user=self._config.get('user'),
                                                  note=self._config.get('note'),
                                                  source=self._config.get('source'))
        else:
            message = 'Opsgenie is disabled'
        return AlertActionResult(not message, message or 'Success')
