import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase


logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=W0212


HOSTNAME_MAGIC_WORD = '{{HOSTNAME}}'
USERNAME_MAGIC_WORD = '{{USERNAME}}'
FIRST_NAME_MAGIC_WORD = '{{FIRST_NAME}}'


class JiraIncidentPerEntityAction(ActionTypeBase):
    """
    Creates an incident in the Jira account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'project_key',
                    'title': 'Project Key',
                    'type': 'string'
                },
                {
                    'name': 'issue_type',
                    'title': 'Issue Type',
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
                    'name': 'add_full_device_content',
                    'title': 'Add Full Device Content',
                    'type': 'bool'
                }
            ],
            'required': [
                'incident_description',
                'project_key',
                'incident_title',
                'add_full_device_content',
                'issue_type'
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
            'incident_description': None,
            'project_key': None,
            'incident_title': None,
            'assignee': None,
            'add_full_device_content': False,
            'labels': None,
            'components': None
        }

    # pylint: disable=R0912,R0914,R0915,R1702
    def _run(self) -> EntitiesResult:

        jira_projection = {
            'internal_axon_id': 1,
            'adapters.plugin_name': 1,
            'adapters.data.hostname': 1,
            'adapters.data.id': 1,
            'adapters.data.name': 1,
            'adapters.data.os.type': 1,
            'adapters.data.device_serial': 1,
            'adapters.data.device_manufacturer': 1,
            'adapters.data.network_interfaces.mac': 1,
            'adapters.data.description': 1,
            'adapters.data.cpus.cores': 1,
            'adapters.data.cpus.name': 1,
            'adapters.data.cpus.ghz': 1,
            'adapters.data.username': 1,
            'adapters.data.display_name': 1,
            'adapters.data.mail': 1,
            'adapters.data.last_used_users': 1,
            'adapters.data.domain': 1,
            'adapters.data.power_state': 1
        }
        current_result = self._get_entities_from_view(jira_projection)

        results = []
        for entry in current_result:
            try:
                hostname = None
                first_name = None
                username = None
                log_message_full = self._config['incident_description']
                summary = self._config['incident_title']
                for adapter_data in entry['adapters']:
                    adapter_data = adapter_data.get('data') or {}
                    if adapter_data.get('hostname') and not hostname:
                        hostname = adapter_data.get('hostname')
                    if adapter_data.get('first_name') and not first_name:
                        first_name = adapter_data.get('first_name')
                    if adapter_data.get('username') and not username:
                        username = adapter_data.get('username')
                if hostname:
                    log_message_full = log_message_full.replace(HOSTNAME_MAGIC_WORD, hostname)
                    summary = summary.replace(HOSTNAME_MAGIC_WORD, hostname)
                if username:
                    log_message_full = log_message_full.replace(USERNAME_MAGIC_WORD, username)
                    summary = summary.replace(USERNAME_MAGIC_WORD, username)
                if first_name:
                    log_message_full = log_message_full.replace(FIRST_NAME_MAGIC_WORD, first_name)
                    summary = summary.replace(FIRST_NAME_MAGIC_WORD, first_name)

                if self._config.get('add_full_device_content'):
                    log_message_full += '\n\n' + str(entry)

                message = self._plugin_base.create_jira_ticket(self._config['project_key'],
                                                               summary,
                                                               log_message_full, self._config['issue_type'],
                                                               assignee=self._config.get('assignee'),
                                                               labels=self._config.get('labels'),
                                                               components=self._config.get('components'))
                results.append(EntityResult(entry['internal_axon_id'], not message, message or 'Success'))
            except Exception:
                logger.exception(f'Problem with entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        return results
