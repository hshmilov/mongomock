import sys
import time
import json
from collections import defaultdict

from datetime import timedelta, datetime, timezone

from slacknotifier import SlackNotifier, get_vm_type_from_instance
from buildsmanager import BuildsManager
from config import EXTERNAL_BUILDS_HOST, CREDENTIALS_PATH

CYCLE_MINUTES = 20     # run a cycle to check on instances state every 1 hour
SHOULD_DELETE_OLD_MESSAGES = False  # Do we want to remove old messages like a notice, after an action has been made?
SE_CI_KEY = 'SE_CI_TEST_KEY'

MONITORING_BOT_METADATA_NAMESPACE = 'monitoring_bot'

REGULAR_SHUTDOWN_TIMES = {
    'first_notice': timedelta(days=1),
    'action': timedelta(days=2)
}

REGULAR_TERMINATE_TIMES = {
    'first_notice': timedelta(days=3),
    'action': timedelta(days=4)
}

MAX_TEST_GROUP_TIME = timedelta(hours=3)


class InstanceMonitor:
    def __init__(self):
        with open(CREDENTIALS_PATH, 'rt') as f:
            self.credentials = json.loads(f.read())
        self.slack_notifier = SlackNotifier()
        self.builds_manager = BuildsManager()

    def run_cycle(self):
        print(f'[{datetime.now()}] Running a cycle')
        all_exceptions = ''
        test_groups = defaultdict(list)
        for instance in self.builds_manager.get_instances():
            try:
                vm_state = instance['cloud']['state']
                vm_type = get_vm_type_from_instance(instance).lower()
                bot_monitoring = instance['db'].get('bot_monitoring') or True

                if bot_monitoring != 'false' and 'demo' not in vm_type and 'saas' not in vm_type \
                        and vm_state in ['running', 'stopped']:
                    if 'test' in vm_type:
                        test_groups[instance['db']['group_name']].append(instance)
                    elif 'builds-vm' in vm_type:
                        self.handle_instance(instance, REGULAR_SHUTDOWN_TIMES, REGULAR_TERMINATE_TIMES)
                    else:
                        raise ValueError(f'Unknown vm type {vm_type}')

            except Exception as e:
                if (instance.get('cloud') or {}).get('key_name') != SE_CI_KEY:
                    # SE-CI Exceptions are known and should not be informed.
                    print(f'Exception {repr(e)}')
                    all_exceptions += f'Exception while handling instance {instance}: {repr(e)}\n'

        for test_group_name, test_group_instances in test_groups.items():
            try:
                first_instance_launch_time = test_group_instances[0]['cloud']['launch_date'].astimezone(timezone.utc)
                already_running = datetime.now().astimezone(timezone.utc) - first_instance_launch_time
                delta = already_running - MAX_TEST_GROUP_TIME
                if delta > timedelta(0):
                    self.slack_notifier.post_channel(
                        f'Test group {test_group_name} is running too much and is probably hanging, '
                        f'I\'m terminating it.',
                        attachments=[
                            {
                                'title': test_group_name,
                                'title_link': f'https://{EXTERNAL_BUILDS_HOST}/#auto_tests',
                                'color': '#fd662c',
                                'fields': [
                                    {
                                        'title': 'Running time',
                                        'value': str(already_running),
                                        'short': 'True'
                                    },
                                    {
                                        'title': 'Number of instances',
                                        'value': len(test_group_instances),
                                        'short': 'True'
                                    }
                                ]
                            }
                        ]
                    )
                    self.builds_manager.terminate_group(test_group_name)

            except Exception as e:
                print(f'Exception {repr(e)}')
                all_exceptions += f'Exception while handling test group {test_group_name} {test_group_instances}: ' \
                    f'{repr(e)}\n'

        if all_exceptions:
            self.slack_notifier.post_channel(
                '',
                attachments=[
                    {
                        'title': f'Exceptions in instance monitor',
                        'color': '#fd662c',
                        'text': str(all_exceptions),
                    }
                ]
            )

    def handle_instance(self, instance, shutdown_times, terminate_times):
        instance_name = instance['db']['name']
        owner = instance['db'].get('owner') or 'Unknown'
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
                    attachments=[self.slack_notifier.get_instance_attachment(instance, [])],
                )
                self.slack_notifier.post_channel(f'Instance "{instance_name}" of user "{owner}" has been stopped.',
                                                 attachments=[
                                                     self.slack_notifier.get_instance_attachment(instance, [])])
                self.builds_manager.stop_instance(cloud_name, cloud_id)
                new_state = 'stopped'

            elif last_user_interaction + shutdown_times['first_notice'] < datetime.now() \
                    and last_message_state not in ['stop_notice', 'stopped']:
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    f'Hi! Do you need your running instance?',
                    attachments=[
                        self.slack_notifier.get_instance_attachment(instance, ['keep', 'shutdown', 'terminate'])]
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
                    attachments=[self.slack_notifier.get_instance_attachment(instance, [])],
                )
                self.slack_notifier.post_channel(f'Instance "{instance_name}" of user "{owner}" should be terminated.',
                                                 attachments=[
                                                     self.slack_notifier.get_instance_attachment(instance, [])])
                # We never actually terminate instances.
                new_state = 'terminated'

            elif last_user_interaction + terminate_times['first_notice'] < datetime.now() \
                    and last_message_state not in ['terminated', 'terminate_notice']:
                result = self.slack_notifier.post_user(
                    owner_slack_id,
                    f'Hi! Do you need your stopped instance?',
                    attachments=[self.slack_notifier.get_instance_attachment(instance, ['keep', 'terminate'])]
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
    print(f'Running Builds Slack Notifier every {CYCLE_MINUTES} minutes')
    im = InstanceMonitor()
    while True:
        im.run_cycle()
        sys.stdout.flush()
        time.sleep(60 * CYCLE_MINUTES)


if __name__ == '__main__':
    sys.exit(main())
