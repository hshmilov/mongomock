import sys
import time
import json

from datetime import timedelta, datetime

from slacknotifier import SlackNotifier
from buildsmanager import BuildsManager, EXTERNAL_BUILDS_HOST

CYCLE_HOURS = 12     # run a cycle to check on instances state every 12 hours
SHOULD_DELETE_OLD_MESSAGES = False  # Do we want to remove old messages like a notice, after an action has been made?

MONITORING_BOT_METADATA_NAMESPACE = 'monitoring_bot'
CREDENTIALS_PATH = 'credentials.json'

REGULAR_SHUTDOWN_TIMES = {
    'first_notice': timedelta(days=1),
    'action': timedelta(days=2)
}

REGULAR_TERMINATE_TIMES = {
    'first_notice': timedelta(days=3),
    'action': timedelta(days=4)
}

TEST_SHUTDOWN_TIMES = {
    'first_notice': timedelta(hours=3),
    'action': timedelta(hours=4)
}

TEST_TERMINATE_TIMES = {
    'first_notice': timedelta(hours=5),
    'action': timedelta(hours=6)
}


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


class InstanceMonitor:
    def __init__(self):
        with open(CREDENTIALS_PATH, 'rt') as f:
            self.credentials = json.loads(f.read())
        self.slack_notifier = SlackNotifier(self.credentials['slack']['data']['workspace_app_bot_api_token'], 'builds')
        self.builds_manager = BuildsManager(CREDENTIALS_PATH)

    def run_cycle(self):
        print(f'[{datetime.now()}] Running a cycle')
        for instance in self.builds_manager.get_instances():
            try:
                vm_state = instance['cloud']['state']
                vm_type = get_vm_type_from_instance(instance).lower()
                bot_monitoring = instance['db'].get('bot_monitoring') or True

                if bot_monitoring != 'false' and 'demo' not in vm_type and 'saas' not in vm_type \
                        and vm_state in ['running', 'stopped']:
                    if 'test' in vm_type:
                        self.handle_instance(instance, TEST_SHUTDOWN_TIMES, TEST_TERMINATE_TIMES)
                    else:
                        self.handle_instance(instance, REGULAR_SHUTDOWN_TIMES, REGULAR_TERMINATE_TIMES)

            except Exception as e:
                print(f'Exception {repr(e)}')
                self.slack_notifier.post_channel(f'Exception while handling instance {instance}: {repr(e)}')

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

    def handle_instance(self, instance, shutdown_times, terminate_times):
        instance_name = instance['db']['name']
        owner = instance['db']['owner']
        cloud_name = instance['cloud']['cloud']
        cloud_id = instance['cloud']['id']
        owner_slack_id = instance['db']['owner_slack_id']
        vm_state = instance['cloud']['state']

        last_message_channel = instance['db'].get(MONITORING_BOT_METADATA_NAMESPACE, {}).get('bot_last_message_channel')
        last_message_ts = instance['db'].get(MONITORING_BOT_METADATA_NAMESPACE, {}).get('bot_last_message_ts')
        last_message_state = instance['db'].get(MONITORING_BOT_METADATA_NAMESPACE, {}).get('bot_last_message_state')
        last_user_interaction = instance['db']['last_user_interaction']

        # A very bad machine state but we don't wanna implement something too complex
        result = None
        if vm_state == 'running':
            if last_user_interaction + shutdown_times['action'] < datetime.now() and last_message_state != 'stopped':
                if last_message_channel and last_message_ts and SHOULD_DELETE_OLD_MESSAGES:
                    self.slack_notifier.delete_message(last_message_channel, last_message_ts)
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    'Your instance has been stopped (but not terminated).',
                    attachments=[self.get_instance_attachment(instance, [])],
                )
                self.slack_notifier.post_channel(f'Instance "{instance_name}" of user "{owner}" has been stopped.',
                                                 attachments=[self.get_instance_attachment(instance, [])])
                self.builds_manager.stop_instance(cloud_name, cloud_id)
                new_state = 'stopped'

            elif last_user_interaction + shutdown_times['first_notice'] < datetime.now() \
                    and last_message_state not in ['stop_notice', 'stopped']:
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    f'Hi! Do you need your running instance?',
                    attachments=[self.get_instance_attachment(instance, ['keep', 'shutdown', 'terminate'])]
                )
                new_state = 'stop_notice'

        elif vm_state == 'stopped':
            if last_user_interaction + terminate_times['action'] < datetime.now() \
                    and last_message_state != 'terminated':
                if last_message_channel and last_message_ts and SHOULD_DELETE_OLD_MESSAGES:
                    self.slack_notifier.delete_message(last_message_channel, last_message_ts)
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    'This is the last notice. Please terminate your instance.',
                    attachments=[self.get_instance_attachment(instance, [])],
                )
                self.slack_notifier.post_channel(f'Instance "{instance_name}" of user "{owner}" should be terminated.',
                                                 attachments=[self.get_instance_attachment(instance, [])])
                # We never actually terminate instances.
                new_state = 'terminated'

            elif last_user_interaction + terminate_times['first_notice'] < datetime.now() \
                    and last_message_state not in ['terminated', 'terminate_notice']:
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    f'Hi! Do you need your stopped instance?',
                    attachments=[self.get_instance_attachment(instance, ['keep', 'terminate'])]
                )
                new_state = 'terminate_notice'

        if result is not None:
            self.builds_manager.set_instance_metadata(
                cloud_name,
                cloud_id,
                MONITORING_BOT_METADATA_NAMESPACE,
                {
                    'bot_last_message_channel': result['channel'],
                    'bot_last_message_ts': result['ts'],
                    'bot_last_message_state': new_state
                }
            )


def main():
    print(f'Running Builds Slack Notifier every {CYCLE_HOURS} hours')
    im = InstanceMonitor()
    while True:
        im.run_cycle()
        sys.stdout.flush()
        time.sleep(60 * 60 * CYCLE_HOURS)


if __name__ == '__main__':
    sys.exit(main())
