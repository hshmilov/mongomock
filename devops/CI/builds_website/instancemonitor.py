import sys
import os
import time

from datetime import timedelta, datetime

from slacknotifier import SlackNotifier
from buildsmanager import BuildsManager, EXTERNAL_BUILDS_HOST

CYCLE_HOURS = 12     # run a cycle to check on instances state every 12 hours
BETA = True  # Remove this when you really want to terminate instances
SHOULD_DELETE_OLD_MESSAGES = False  # Do we want to remove old messages like a notice, after an action has been made?

MONITORING_BOT_METADATA_NAMESPACE = 'monitoring_bot'

SHUTDOWN_TIMES = {
    'first_notice': timedelta(days=1),
    'action': timedelta(days=2)
}

TERMINATE_TIMES = {
    'first_notice': timedelta(days=3),
    'action': timedelta(days=4)
}


class InstanceMonitor:
    def __init__(self):
        self.slack_notifier = SlackNotifier(os.environ['SLACK_WORKSPACE_APP_BOT_API_TOKEN'], 'builds')
        self.builds_manager = BuildsManager()

    def run_cycle(self):
        print(f'[{datetime.now()}]Running a cycle')
        for instance in self.builds_manager.getInstances():
            try:
                vm_state = instance['ec2']['state']
                vm_type = instance['db']['vm_type']
                bot_monitoring = instance['db'].get('bot_monitoring') or True

                if bot_monitoring != 'false' and vm_type == 'Builds-VM' and \
                        vm_state in ['running', 'stopped']:
                    self.handle_instance(instance)

            except Exception as e:
                print(f'Exception {repr(e)}')
                self.slack_notifier.post_channel(f'Exception while handling instance {instance}: {repr(e)}')

    @staticmethod
    def get_instance_attachment(instance, action_buttons):
        attachment = {
            'title': f'{instance["db"]["name"]} - {instance["ec2"]["private_ip_address"]}',
            'title_link': f'https://{instance["ec2"]["private_ip_address"]}',
            'color': '#fd662c',
            'fields': [
                {
                    'title': 'State',
                    'value': f'{instance["ec2"]["state"]}',
                    'short': 'True'
                },
                {
                    'title': 'Tier',
                    'value': 'Instances',
                    'short': 'True'
                },
                {
                    'title': 'Instance Type',
                    'value': f'{instance["ec2"]["instance_type"]}',
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

            if 'keep' in action_buttons:
                attachment['actions'].append(
                    {
                        'type': 'button',
                        'text': 'Yes, please keep it',
                        'url': f'https://{EXTERNAL_BUILDS_HOST}/instances/{instance["ec2"]["id"]}/update_state?state=keep',
                        'style': 'default'
                    }
                )

            if 'shutdown' in action_buttons:
                attachment['actions'].append(
                    {
                        'type': 'button',
                        'text': 'Yes, but please shut it down',
                        'url': f'https://{EXTERNAL_BUILDS_HOST}/instances/{instance["ec2"]["id"]}/update_state?state=shutdown',
                        'style': 'default'
                    },
                )

            if 'terminate' in action_buttons:
                attachment['actions'].append(
                    {
                        'type': 'button',
                        'text': 'No, please terminate it',
                        'url': f'https://{EXTERNAL_BUILDS_HOST}/instances/{instance["ec2"]["id"]}/update_state?state=terminate',
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

    def handle_instance(self, instance):
        instance_name = instance['db']['name']
        owner = instance['db']['owner']
        ec2_id = instance['ec2']['id']
        owner_slack_id = instance['db']['owner_slack_id']
        vm_state = instance['ec2']['state']

        last_message_channel = instance['db'].get(MONITORING_BOT_METADATA_NAMESPACE, {}).get('bot_last_message_channel')
        last_message_ts = instance['db'].get(MONITORING_BOT_METADATA_NAMESPACE, {}).get('bot_last_message_ts')
        last_message_state = instance['db'].get(MONITORING_BOT_METADATA_NAMESPACE, {}).get('bot_last_message_state')
        last_user_interaction = instance['db']['last_user_interaction']

        # A very bad machine state but we don't wanna implement something too complex
        result = None
        if vm_state == 'running':
            if last_user_interaction + SHUTDOWN_TIMES['action'] < datetime.now() and last_message_state != 'stopped':
                if last_message_channel and last_message_ts and SHOULD_DELETE_OLD_MESSAGES:
                    self.slack_notifier.delete_message(last_message_channel, last_message_ts)
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    'Your instance has been stopped (but not terminated).',
                    attachments=[self.get_instance_attachment(instance, [])],
                )
                self.slack_notifier.post_channel(f'Instance "{instance_name}" of user "{owner}" has been stopped.',
                                                 attachments=[self.get_instance_attachment(instance, [])])
                self.builds_manager.stopInstance(ec2_id)
                new_state = 'stopped'

            elif last_user_interaction + SHUTDOWN_TIMES['first_notice'] < datetime.now() \
                    and last_message_state not in ['stop_notice', 'stopped']:
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    f'Hi! Do you need your running instance?',
                    attachments=[self.get_instance_attachment(instance, ['keep', 'shutdown', 'terminate'])]
                )
                new_state = 'stop_notice'

        elif vm_state == 'stopped':
            if last_user_interaction + TERMINATE_TIMES['action'] < datetime.now() \
                    and last_message_state != 'terminated':
                if last_message_channel and last_message_ts and SHOULD_DELETE_OLD_MESSAGES:
                    self.slack_notifier.delete_message(last_message_channel, last_message_ts)
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    'Your instance has been terminated.',
                    attachments=[self.get_instance_attachment(instance, [])],
                )
                self.slack_notifier.post_channel(f'Instance "{instance_name}" of user "{owner}" has been terminated.',
                                                 attachments=[self.get_instance_attachment(instance, [])])
                if not BETA:
                    self.builds_manager.terminateInstance(ec2_id)
                new_state = 'terminated'

            elif last_user_interaction + TERMINATE_TIMES['first_notice'] < datetime.now() \
                    and last_message_state not in ['terminated', 'terminate_notice']:
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    f'Hi! Do you need your stopped instance?',
                    attachments=[self.get_instance_attachment(instance, ['keep', 'terminate'])]
                )
                new_state = 'terminate_notice'

        if result is not None:
            self.builds_manager.set_instance_metadata(
                ec2_id,
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
