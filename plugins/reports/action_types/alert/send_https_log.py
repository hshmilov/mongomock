import io
import logging

from axonius.utils import gui_helpers, db_querying_helper
from axonius.utils.json import to_json

from axonius.consts import report_consts
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert


logger = logging.getLogger(f'axonius.{__name__}')


class SendHttpsLogAction(ActionTypeAlert):
    """
    Sends a syslog
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'authorization_header',
                    'title': 'Authorization header',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'description',
                    'title': 'Description',
                    'type': 'string',
                    'format': 'text'
                },
                {
                    'name': 'send_device_data',
                    'title': 'Send devices data',
                    'type': 'bool'
                },
                {
                    'name': 'description_default',
                    'title': 'Add default incident description',
                    'type': 'bool'
                },
                {
                    'name': 'send_csv_data',
                    'title': 'Send CSV data',
                    'type': 'bool'
                }
            ],
            'required': [
                'description_default',
                'send_device_data',
                'send_csv_data',
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'send_device_data': False,
            'description_default': False,
            'description': None,
            'authorization_header': None,
            'send_csv_data': False
        }

    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')
        authorization_header = self._config.get('authorization_header')
        field_list = self.trigger_view_config.get('fields', [
            'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
            'specific_data.data.last_used_users', 'labels'
        ])
        sort = gui_helpers.get_sort(self.trigger_view_config)
        field_filters = self.trigger_view_config.get('colFilters', {})
        excluded_adapters = self.trigger_view_config.get('colExcludedAdapters', {})
        try:
            if self._config.get('send_csv_data'):
                csv_string = gui_helpers.get_csv(self.trigger_view_parsed_filter,
                                                 sort,
                                                 {field: 1 for field in field_list},
                                                 self._entity_type,
                                                 field_filters=field_filters,
                                                 excluded_adapters=excluded_adapters)
                csv_bytes = io.BytesIO(csv_string.getvalue().encode('utf-8'))
                self._plugin_base.send_https_log_message(
                    '', authorization_header,
                    files={'file': ('report.csv', csv_bytes)}
                )
        except Exception:
            logger.exception(f'Problem sending CSV https log')

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
            log_message_full = self._config.get('description') or ''
            if self._config.get('description_default') is True:
                log_message_full += '\n' + log_message
            self._plugin_base.send_https_log_message(log_message_full, authorization_header)
            return AlertActionResult(True, 'Sent Https message')
        col_filters = self.trigger_view_config.get('colFilters', {})
        excluded_adapters = self.trigger_view_config.get('colExcludedAdapters', {})
        all_gui_entities = db_querying_helper.get_entities(None,
                                                           None,
                                                           self.trigger_view_parsed_filter,
                                                           sort, {
                                                               field: 1
                                                               for field
                                                               in field_list
                                                           },
                                                           self._entity_type,
                                                           field_filters=col_filters,
                                                           excluded_adapters=excluded_adapters)

        for entity in all_gui_entities:
            entity['alert_name'] = self._report_data['name']
            self._plugin_base.send_https_log_message(to_json(entity), authorization_header)

        return AlertActionResult(True, 'Sent Devices data to Https log')
