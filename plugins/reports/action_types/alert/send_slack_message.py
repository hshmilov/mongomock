import logging
import requests

from axonius.utils import gui_helpers, db_querying_helper
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert

logger = logging.getLogger(f'axonius.{__name__}')


class SlackSendMessageAction(ActionTypeAlert):
    """
    Send a meassge to Slack channel
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'webhook_url',
                    'title': 'Incoming webhook URL',
                    'type': 'string'
                },
                {
                    'name': 'verify_url',
                    'title': 'Verify URL',
                    'type': 'bool'
                },
                {
                    'name': 'incident_description',
                    'title': 'Incident description',
                    'type': 'string',
                    'format': 'text'
                },
            ],
            'required': [
                'incident_description',
                'verify_url',
                'webhook_url'

            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'incident_description': None,
            'verify_url': False,
            'webhook_url': None
        }

    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')
        field_list = self.trigger_view_config.get('fields', [
            'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
            'specific_data.data.last_used_users', 'labels'
        ])
        sort = gui_helpers.get_sort(self.trigger_view_config)
        all_gui_entities = db_querying_helper.get_entities(None,
                                                           None,
                                                           self.trigger_view_parsed_filter,
                                                           sort, {
                                                               field: 1
                                                               for field
                                                               in field_list
                                                           }, self._entity_type)

        entities_str = ''
        for i, entity in enumerate(all_gui_entities):
            entities_str += str(entity) + '\n\n'
            if i == 5:
                break
        old_results_num_of_devices = len(self._internal_axon_ids) + len(self._removed_axon_ids) - \
            len(self._added_axon_ids)
        alert_name = self._report_data['name']
        log_message_full = self._config['incident_description']
        success = False
        try:
            slack_dict = {
                'attachments': [
                    {
                        'color': '#fd662c',
                        'text': 'Description: ' + log_message_full + '\n' + 'First 5 Results Are: \n' + entities_str,
                        'pretext': f'An Axonius alert - "{alert_name}" was triggered '
                                   f'because of {self._get_trigger_description()}.',
                        'title': f'Query "{self.trigger_view_name}"',
                        'title_link': self._generate_query_link(),
                        'fields': [
                            {
                                'title': 'Current amount',
                                'value': len(self._internal_axon_ids),
                                'short': True
                            },
                            {
                                'title': 'Previous amount',
                                'value': old_results_num_of_devices,
                                'short': True
                            }
                        ],
                        'footer': 'Axonius',
                        'footer_icon': 'https://s3.us-east-2.amazonaws.com/axonius-public/logo.png'
                    }
                ]
            }
            response = requests.post(url=self._config['webhook_url'],
                                     json=slack_dict,
                                     headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                                     verify=self._config['verify_url'])
            success = response.status_code == 200
            if success is True:
                message = 'Success'
            else:
                message = response.text
        except Exception as e:
            logger.exception('Problem sending to slack')
            message = str(e)
        return AlertActionResult(success, message)
