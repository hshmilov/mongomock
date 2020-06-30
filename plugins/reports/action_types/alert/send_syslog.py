from axonius.utils import gui_helpers
from axonius.utils.db_querying_helper import get_entities
from axonius.utils.json import to_json

from axonius.consts import report_consts
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert


class NotifySyslogAction(ActionTypeAlert):
    """
    Sends a syslog
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'send_device_data',
                    'title': 'Send device data to syslog',
                    'type': 'bool'
                },
                {
                    'name': 'severity',
                    'title': 'Message severity',
                    'type': 'string',
                    'enum': [
                        'info', 'warning', 'error'
                    ]
                }
            ],
            'required': [
                'send_device_data',
                'severity'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'send_device_data': False,
            'severity': 'info'
        }

    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')

        # Check if send device data is checked.
        if not self._config.get('send_device_data'):
            if self._run_configuration.result:
                prev_result_count = self._run_configuration.result_count
            else:
                prev_result_count = 0
            query_link = self._generate_query_link().replace('\n', ' ')
            log_message = report_consts.REPORT_CONTENT.format(name=self._report_data['name'],
                                                              query=self.trigger_view_name,
                                                              num_of_triggers=len(self._triggered_set),
                                                              trigger_message=self._get_trigger_description(),
                                                              num_of_current_devices=len(self._internal_axon_ids),
                                                              old_results_num_of_devices=prev_result_count,
                                                              query_link=query_link)
            self._plugin_base.send_syslog_message(log_message, self._config['severity'])
            return AlertActionResult(True, 'Sent Syslog message')

        sort = gui_helpers.get_sort(self.trigger_view_config)
        field_list = self.trigger_view_config.get('fields', [
            'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
            'specific_data.data.last_used_users', 'labels'
        ])
        col_filters = self.trigger_view_config.get('colFilters', {})
        all_gui_entities = get_entities(None,
                                        None,
                                        self.trigger_view_parsed_filter,
                                        sort, {
                                            field: 1
                                            for field
                                            in field_list
                                        },
                                        self._entity_type,
                                        field_filters=col_filters)

        for entity in all_gui_entities:
            entity['alert_name'] = self._report_data['name']
            self._plugin_base.send_syslog_message(to_json(entity), self._config['severity'])

        return AlertActionResult(True, 'Sent Devices data to Syslog')
