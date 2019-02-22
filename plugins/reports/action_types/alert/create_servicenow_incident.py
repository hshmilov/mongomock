import logging

from axonius.consts import report_consts
from reports.enforcement_classes import AlertActionResult
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
                    'name': 'incident_title',
                    'title': 'Incident Title',
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
            'description_default': None,
            'incident_description': None,
            'incident_title': None
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
        log_message += '\n'
        impact = report_consts.SERVICE_NOW_SEVERITY.get(self._config['severity'],
                                                        report_consts.SERVICE_NOW_SEVERITY['error'])
        log_message_full = self._config['incident_description']
        if self._config.get('description_default') is True:
            log_message_full += log_message
        message = self._plugin_base.create_service_now_incident(self._config['incident_title'], log_message, impact)
        return AlertActionResult(not message, message or 'Success')
