import os
import shlex
import subprocess
from pathlib import Path

from scripts.watchdog.watchdog_task import WatchdogTask
from inotify_simple import INotify, flags

DIR_PATH = '/home/ubuntu/cortex/uploaded_files'
HOSTNAME_CHANGE_FILENAME = 'hostname_change'
UPGRADE_EVENT_FILENAME = 'update_now'
EVENTS = (HOSTNAME_CHANGE_FILENAME, UPGRADE_EVENT_FILENAME)


class InotifyTask(WatchdogTask):
    def __init__(self):
        super().__init__(name=self.__class__.__name__.lower())
        if not Path(DIR_PATH).exists():
            Path(DIR_PATH).mkdir()

    def run(self):
        inotify = INotify()
        watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF
        wd = inotify.add_watch(DIR_PATH, watch_flags)
        while True:
            try:
                for event in inotify.read():
                    if event.name in EVENTS and flags.CREATE in flags.from_mask(event.mask):
                        if event.name == HOSTNAME_CHANGE_FILENAME:
                            destination_command_file = Path(f'{DIR_PATH}/{HOSTNAME_CHANGE_FILENAME}')
                            if not destination_command_file.exists():
                                continue
                            new_hostname = destination_command_file.read_text().strip()
                            subprocess.check_call(shlex.split(f'hostnamectl set-hostname {new_hostname}'))
                            destination_command_file.unlink()
                        elif event.name == UPGRADE_EVENT_FILENAME:
                            destination_command_file = Path(f'{DIR_PATH}/{UPGRADE_EVENT_FILENAME}')
                            os.system('/home/ubuntu/cortex/devops/scripts/instances/run_upgrade_on_instance.sh')
                            destination_command_file.unlink()
            except Exception as e:
                self.report_error(f'Couldn\'t execute task on host due to {str(e)}')


if __name__ == '__main__':
    gw = InotifyTask()
    gw.start()
