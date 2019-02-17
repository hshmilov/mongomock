import logging

from axonius.consts import report_consts
from reports.alert_action_types.alert_action_type_base import AlertActionTypeBase
from reports.enforcement_classes import EntityResult

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowIncidentAction(AlertActionTypeBase):
    """
    Creates an incident in the ServiceNow account
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [{
                'name': 'severity',
                'title': 'Message Severity',
                'type': 'string',
                'enum': [
                    'info', 'warning', 'error'
                ]
            }],
            'required': [
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'severity': 'info'
        }

    def run(self) -> EntityResult:
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

        message = self._plugin_base.create_service_now_incident(self._report_data['name'], log_message, impact)
        return EntityResult(not message, message or 'Success')
