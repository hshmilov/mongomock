import io
import json
import logging
import requests

from axonius.consts import report_consts
from axonius.utils import gui_helpers
from axonius.plugin_base import PluginBase
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')


LINK_TEMPLATE = '<<ISSUE_LINK>>'


class JiraIncidentAction(ActionTypeAlert):
    """
    Creates an incident in the Jira account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'project_key',
                    'title': 'Project key',
                    'type': 'string'
                },
                {
                    'name': 'issue_type',
                    'title': 'Issue type',
                    'type': 'string',
                },
                {
                    'name': 'incident_title',
                    'title': 'Summary',
                    'type': 'string'
                },
                {
                    'name': 'incident_description',
                    'title': 'Description',
                    'type': 'string',
                    'format': 'text'
                },
                {
                    'name': 'description_default',
                    'title': 'Add default incident description',
                    'type': 'bool'
                },
                {
                    'name': 'assignee',
                    'title': 'Assignee',
                    'type': 'string'
                },
                {
                    'name': 'labels',
                    'title': 'Labels',
                    'type': 'string'
                },
                {
                    'name': 'components',
                    'title': 'Components',
                    'type': 'string'
                },
                {
                    'name': 'extra_fields',
                    'title': 'Additional fields',
                    'type': 'string'
                },
                {
                    'name': 'send_csv_data',
                    'title': 'Send CSV data',
                    'type': 'bool'
                },
                {
                    'name': 'created_issue_webhook_url',
                    'title': 'Send created issue link to webhook URL',
                    'type': 'string'
                },
                {
                    'name': 'created_issue_webhook_content',
                    'title': 'Webhook content',
                    'type': 'string',
                    'default': '{"text": "Created issue link is:' + LINK_TEMPLATE + '"}'
                }
            ],
            'required': [
                'description_default',
                'incident_description',
                'project_key',
                'incident_title',
                'issue_type',
                'send_csv_data'
            ],
            'type': 'array'
        }
        jira_keys = PluginBase.Instance.get_jira_keys()
        issue_types = PluginBase.Instance.get_issue_types_names()
        if jira_keys:
            schema['items'][0]['enum'] = jira_keys
        if issue_types:
            schema['items'][1]['enum'] = issue_types
        return schema

    @staticmethod
    def default_config() -> dict:
        return {
            'issue_type': None,
            'extra_fields': None,
            'description_default': False,
            'incident_description': None,
            'project_key': None,
            'send_csv_data': False,
            'incident_title': None,
            'assignee': None,
            'labels': None,
            'components': None,
            'created_issue_webhook_url': None,
            'created_issue_webhook_content': None
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
        log_message_full = self._config['incident_description']
        if self._config.get('description_default') is True:
            log_message_full += '\n' + log_message
        csv_bytes = None
        if self._config.get('send_csv_data'):
            field_list = self.trigger_view_config.get('fields', [
                'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
                'specific_data.data.last_used_users', 'labels'
            ])
            sort = gui_helpers.get_sort(self.trigger_view_config)
            field_filters = self.trigger_view_config.get('colFilters', {})
            excluded_adapters = self.trigger_view_config.get('colExcludedAdapters', {})
            csv_string = gui_helpers.get_csv(self.trigger_view_parsed_filter,
                                             sort,
                                             {field: 1 for field in field_list},
                                             self._entity_type,
                                             field_filters=field_filters,
                                             excluded_adapters=excluded_adapters)
            csv_bytes = io.BytesIO(csv_string.getvalue().encode('utf-8'))

        message, permalink = self._plugin_base.create_jira_ticket(self._config['project_key'],
                                                                  self._config['incident_title'],
                                                                  log_message_full, self._config['issue_type'],
                                                                  assignee=self._config.get('assignee'),
                                                                  labels=self._config.get('labels'),
                                                                  components=self._config.get('components'),
                                                                  csv_file_name='Axonius Entities Data.csv',
                                                                  extra_fields=self._config.get('extra_fields'),
                                                                  csv_bytes=csv_bytes)
        if permalink and \
                self._config.get('created_issue_webhook_url') and self._config.get('created_issue_webhook_content'):
            try:
                created_issue_webhook_url = self._config.get('created_issue_webhook_url')
                created_issue_webhook_content = self._config.get('created_issue_webhook_content')
                created_issue_webhook_content = created_issue_webhook_content.replace(LINK_TEMPLATE, permalink)
                response = requests.post(url=created_issue_webhook_url,
                                         json=json.loads(created_issue_webhook_content),
                                         headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                                         verify=False)
                response.raise_for_status()
            except Exception:
                logger.exception(f'Problem sending created issue to webhoot')

        return AlertActionResult(not message, message or 'Success')
