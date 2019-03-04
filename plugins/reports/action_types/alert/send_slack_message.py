import logging
import requests

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
                    'title': 'Incoming Webhook URL',
                    'type': 'string'
                },
                {
                    'name': 'verify_url',
                    'title': 'Verify URL',
                    'type': 'bool'
                },
                {
                    'name': 'incident_description',
                    'title': 'Incident Description',
                    'type': 'string'
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
        query_name = self._run_configuration.view.name
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
                        'text': 'Description: ' + log_message_full,
                        'pretext': f'An Axonius alert - "{alert_name}" was trigered '
                                   f'because of {self._get_trigger_description()}.',
                        'title': f'Query "{query_name}"',
                        'title_link': self._generate_query_link(query_name),
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
            resposne = requests.post(url=self._config['webhook_url'],
                                     json=slack_dict,
                                     headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                                     verify=self._config['verify_url'])
            success = resposne.status_code == 200
            if success is True:
                message = 'Success'
            else:
                message = resposne.content
        except Exception as e:
            logger.exception('Problem sending to slack')
            message = str(e)
        return AlertActionResult(success, message)
