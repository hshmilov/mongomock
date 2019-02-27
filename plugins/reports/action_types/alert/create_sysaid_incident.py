import logging

from axonius.consts import report_consts
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
                    'type': 'string'
                },
                {
                    'name': 'description_default',
                    'title': 'Add Incident Description Default',
                    'type': 'bool'
                },
            ],
            'required': [
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
        log_message_full = self._config['incident_description']
        if self._config.get('description_default') is True:
            log_message_full += '\n' + log_message
        message = self._plugin_base.create_sysaid_incident(log_message_full)
        return AlertActionResult(not message, message or 'Success')
