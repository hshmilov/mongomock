from axonius.utils import gui_helpers
from axonius.utils.json import to_json

from axonius.consts import report_consts
from axonius.utils.axonius_query_language import parse_filter
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert


class SendHttpsLogAction(ActionTypeAlert):
    """
    Sends a syslog
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'description',
                    'title': 'Description',
                    'type': 'string'
                },
                {
                    'name': 'send_device_data',
                    'title': 'Send devices data',
                    'type': 'bool'
                },
                {
                    'name': 'description_default',
                    'title': 'Add Incident Description Default',
                    'type': 'bool'
                },
            ],
            'required': [
                'description_default',
                'send_device_data',
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'send_device_data': False,
            'description_default': False,
            'description': None
        }

    def _run(self) -> AlertActionResult:
        # Check if send device data is checked.
        query_name = self._run_configuration.view.name

        if not self._config.get('send_device_data'):
            if self._run_configuration.result:
                prev_result_count = self._run_configuration.result_count
            else:
                prev_result_count = 0
            query_link = self._generate_query_link(query_name).replace('\n', ' ')
            log_message = report_consts.REPORT_CONTENT.format(name=self._report_data['name'],
                                                              query=query_name,
                                                              num_of_triggers=len(self._triggered_set),
                                                              trigger_message=self._get_trigger_description(),
                                                              num_of_current_devices=len(self._internal_axon_ids),
                                                              old_results_num_of_devices=prev_result_count,
                                                              query_link=query_link)
            log_message_full = self._config.get('description') or ''
            if self._config.get('description_default') is True:
                log_message_full += '\n' + log_message
            self._plugin_base.send_https_log_message(log_message_full)
            return AlertActionResult(True, 'Sent Https message')

        query = self._plugin_base.gui_dbs.entity_query_views_db_map[self._entity_type].find_one(
            {
                'name': query_name
            })
        if query:
            parsed_query_filter = parse_filter(query['view']['query']['filter'])
            field_list = query['view'].get('fields', [])
            sort = gui_helpers.get_sort(query['view'])
        else:
            parsed_query_filter = self._create_query(self._internal_axon_ids)
            field_list = ['specific_data.data.name', 'specific_data.data.hostname',
                          'specific_data.data.os.type', 'specific_data.data.last_used_users']
            sort = {}
        all_gui_entities = gui_helpers.get_entities(None, None, parsed_query_filter,
                                                    sort,
                                                    {
                                                        field: 1
                                                        for field
                                                        in field_list
                                                    },
                                                    self._entity_type)

        for entity in all_gui_entities:
            entity['alert_name'] = self._report_data['name']
            self._plugin_base.send_https_log_message(to_json(entity))

        return AlertActionResult(True, 'Sent Devices data to Https log')
