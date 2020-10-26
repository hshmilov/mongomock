import shlex
import subprocess
from pathlib import Path

from scripts.watchdog.watchdog_task import WatchdogTask
from inotify_simple import INotify, flags

DIR_PATH = '/home/ubuntu/cortex/uploaded_files'
HOSTNAME_CHANGE_FILENAME = 'hostname_change'


class HostnameChangerTask(WatchdogTask):
    def __init__(self):
        super().__init__(name=self.__class__.__name__.lower())

    def run(self):
        inotify = INotify()
        watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF
        wd = inotify.add_watch(DIR_PATH, watch_flags)
        destination_command_file = Path(f'{DIR_PATH}/{HOSTNAME_CHANGE_FILENAME}')
        while True:
            try:
                for event in inotify.read():
                    if event.name == HOSTNAME_CHANGE_FILENAME and \
                            flags.CREATE in flags.from_mask(event.mask) and \
                            destination_command_file.exists():
                        new_hostname = destination_command_file.read_text().strip()
                        subprocess.check_call(shlex.split(f'hostnamectl set-hostname {new_hostname}'))
                        destination_command_file.unlink()
            except Exception as e:
                self.report_error(f'Couldn\'t change hostname of host due to {str(e)}')


if __name__ == '__main__':
    gw = HostnameChangerTask()
    gw.start()
