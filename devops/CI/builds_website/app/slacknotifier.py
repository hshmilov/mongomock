import os
import json

from slackclient import SlackClient
from config import EXTERNAL_BUILDS_HOST, CREDENTIALS_PATH

IS_DEBUG = os.environ.get('BUILDS_DEBUG') == 'true'
DEBUG_CHANNEL = '@U6CU068S0'    # This developer's slack
DEFAULT_CHANNEL = 'builds'


# pylint: disable=W0235
class SlackNotifierException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


def get_vm_type_from_instance(instance):
    if instance['db'].get('vm_type'):
        return instance['db'].get('vm_type')
    else:
        instance_tags = instance['cloud'].get('tags') or {}
        if instance_tags.get('VM-Type'):
            return instance_tags.get('VM-Type')
        elif instance_tags.get('vm-type'):
            return instance_tags.get('vm-type')

    raise ValueError(f'Can not determinte vm_type')


class SlackNotifier:
    def __init__(self, default_channel=DEFAULT_CHANNEL):
        with open(CREDENTIALS_PATH, 'rt') as f:
            credentials = json.loads(f.read())
            self.slack_token = credentials['slack']['data']['workspace_app_bot_api_token']

        self.default_channel = default_channel
        self.slack_client = SlackClient(self.slack_token)

        if IS_DEBUG:
            self.debug_channel = DEBUG_CHANNEL
        else:
            self.debug_channel = None

    def __delete(self, channel, timestamp):
        result = self.slack_client.api_call(
            'chat.delete',
            channel=channel,
            ts=timestamp,
            as_user=True
        )

        if not result.get('ok'):
            raise SlackNotifierException(f'Error: {result}')

        return result

    def __post(self, channel, message, attachments, last_message):
        if last_message is None:
            result = self.slack_client.api_call(
                'chat.postMessage',
                channel=channel,
                text=message,
                as_user=True,
                attachments=attachments
            )
        else:
            message_channel, message_ts = last_message
            result = self.slack_client.api_call(
                'chat.update',
                channel=message_channel,
                text=message,
                as_user=True,
                attachments=attachments,
                ts=message_ts
            )

        if not result.get('ok'):
            raise SlackNotifierException(f'Error: {result}')

        return result

    def post_channel(self, message, channel=None, attachments=None, last_message=None):
        if not channel:
            channel = self.default_channel

        if IS_DEBUG:
            channel = self.debug_channel
        return self.__post(channel, message, attachments, last_message)

    def post_user(self, user, message, attachments=None, last_message=None):
        channel = f'@{user}'
        if IS_DEBUG:
            channel = self.debug_channel

        return self.__post(channel, message, attachments, last_message)

    def delete_message(self, channel, timestamp):
        if IS_DEBUG:
            channel = self.debug_channel
        return self.__delete(channel, timestamp)

    def post_exception(self, title: str, text: str, fields: dict = None):
        self.post_channel(
            '',
            attachments=[
                {
                    'title': title,
                    'color': '#fd662c',
                    'text': text,
                    'fields': [{'title': k, 'value': str(v)} for k, v in fields.items()] if fields else []
                }
            ]
        )

    @staticmethod
    def get_instance_attachment(instance, action_buttons):
        attachment = {
            'title': f'{instance["db"]["name"]} - {instance["cloud"]["private_ip"]}',
            'title_link': f'https://{instance["cloud"]["private_ip"]}',
            'color': '#fd662c',
            'fields': [
                {
                    'title': 'State',
                    'value': f'{instance["cloud"]["state"]}',
                    'short': 'True'
                },
                {
                    'title': 'Tier',
                    'value': get_vm_type_from_instance(instance) + f' - {instance["cloud"]["cloud"]}',
                    'short': 'True'
                },
                {
                    'title': 'Instance Type',
                    'value': f'{instance["cloud"]["type"]}',
                    'short': 'True'
                },
                {
                    'title': 'Date Created',
                    'value': f'{instance["db"]["date"]}',
                    'short': 'True'
                },
            ]
        }

        if action_buttons:
            attachment['actions'] = []

            cloud_id = instance['cloud']['id']
            cloud_name = instance['cloud']['cloud']

            if 'keep' in action_buttons:
                attachment['actions'].append(
                    {
                        'type': 'button',
                        'text': 'Yes, please keep it',
                        'url': f'https://{EXTERNAL_BUILDS_HOST}/api/instances/{cloud_name}/{cloud_id}/update_state?state=keep',
                        'style': 'default'
                    }
                )

            if 'shutdown' in action_buttons:
                attachment['actions'].append(
                    {
                        'type': 'button',
                        'text': 'Yes, but please shut it down',
                        'url': f'https://{EXTERNAL_BUILDS_HOST}/api/instances/{cloud_name}/{cloud_id}/update_state?state=shutdown',
                        'style': 'default'
                    },
                )

            if 'terminate' in action_buttons:
                attachment['actions'].append(
                    {
                        'type': 'button',
                        'text': 'No, please terminate it',
                        'url': f'https://{EXTERNAL_BUILDS_HOST}/api/instances/{cloud_name}/{cloud_id}/update_state?state=terminate',
                        'style': 'primary',
                        'confirm':
                            {
                                'title': 'Are you sure?',
                                'text': 'Are you sure you would like to terminate this instance?',
                                'ok_text': 'Yes',
                                'dismiss_text': 'No'
                            }
                    }
                )

        return attachment
