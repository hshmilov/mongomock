import datetime
import os
import subprocess
import time

import dateutil.parser
import docker
import pytz
import requests
import urllib3
from scripts.watchdog.watchdog_task import WatchdogTask

from axonius.consts.system_consts import CORTEX_PATH, NODE_MARKER_PATH
from axonius.utils.host_utils import check_installer_locks, check_watchdog_action_in_progress, \
    GUIALIVE_WATCHDOG_IN_PROGRESS, create_lock_file, check_if_non_readonly_watchdogs_are_disabled

SLEEP_SECONDS = 60 * 1
ERROR_MSG = 'UI is not responding'  # do not modify this string. used for alerts
NODE_MSG = 'this watchdog will not run on node'
SHUTTING_DOWN_THE_SYSTEM_MGS = 'Gui is dead, shutting down'
RE_RAISING_MSG = 're_raising_axonius'
REBOOTING_MSG = 'rebooting_now'

INTERNAL_PORT = 4433  # 0.0.0.0:443 could be mutual-tls protected. The host exposes 127.0.0.1:4433 without it.

GUI_IS_DEAD_THRESH = 60 * 30  # 30 minutes


class GuiAliveTask(WatchdogTask):

    def __init__(self):
        super().__init__()
        self.last_time_gui_alive = None
        self.mark_gui_alive()
        self.docker_client = docker.from_env()

    def now(self):
        return time.time()

    def mark_gui_alive(self):
        self.last_time_gui_alive = self.now()

    def run(self):

        urllib3.disable_warnings()

        while True:
            time.sleep(SLEEP_SECONDS)

            if NODE_MARKER_PATH.is_file():
                self.report_info(NODE_MSG)
                continue

            if check_if_non_readonly_watchdogs_are_disabled():
                self.report_info(f'Watchdogs are disabled')
                continue

            if check_installer_locks():
                self.report_info('system upgrade/restore is in progress...')
                continue

            if check_watchdog_action_in_progress():
                self.report_info(f'Other watchdog action in progress...')
                continue

            try:
                gui_container = self.docker_client.containers.get('gui')
            except Exception:
                self.report_info(f'GUI is not up. Have nothing to monitor')
                continue

            gui_status = gui_container.attrs['State']['Status'].lower()
            if gui_status != 'running':
                self.report_info(f'Gui container is up but not running ("{gui_status}") '
                                 f'Have nothing to monitor')
                continue

            gui_started_at = dateutil.parser.parse(gui_container.attrs['State']['StartedAt'])
            gui_uptime = (datetime.datetime.now(pytz.utc) - gui_started_at).total_seconds()

            if gui_uptime < 60 * 5:
                self.report_info(f'GUI container is up but is running less than 5 minutes ({gui_uptime} seconds)')
                time.sleep(60 * 5)
                continue

            self.report_info(f'{self.name} is running')
            try:
                response = requests.get(f'https://127.0.0.1:{INTERNAL_PORT}/api/signup',
                                        verify=False,
                                        timeout=(10, 20))
                if response.status_code != 200:
                    self.report_error(f'{ERROR_MSG} {response.status_code} {response.text}')
                else:
                    self.mark_gui_alive()
            except Exception as e:
                self.report_error(f'{ERROR_MSG} {e}')

            if self.now() - self.last_time_gui_alive > GUI_IS_DEAD_THRESH:
                try:
                    create_lock_file(GUIALIVE_WATCHDOG_IN_PROGRESS)
                    self.report_info(SHUTTING_DOWN_THE_SYSTEM_MGS)
                    self.report_info(f'Stopping mongo')
                    try:
                        mongo = self.docker_client.containers.get('mongo')
                        mongo.stop(timeout=20 * 60)
                    except Exception as e:
                        self.report_error(f'Failed to stop mongo - {e}')
                        # If mongo does not stop in such long time we suspect a real docker system error,
                        # remove with force=True will just get stuck. It's better to reboot
                    try:
                        mongo = self.docker_client.containers.get('mongo')
                        mongo.remove(force=True)
                    except Exception as e:
                        self.report_error(f'Failed to kill mongo - {e}')
                    self.report_info(f'Stopped mongo')

                    # Kill everything abruptly now, don't fail if it fails
                    subprocess.call('docker rm -f `docker ps -a -q`', shell=True)

                    self.report_info(f'restarting docker service')
                    subprocess.check_call('/bin/systemctl restart docker'.split())
                    self.report_info(f'restarted docker service')

                    # fork the process so we won't get killed when the service is restarted
                    ret_code = os.fork()
                    if ret_code == 0:
                        # child process
                        time.sleep(5)
                        self.report_metric(RE_RAISING_MSG, metric_value=0)

                        with open('/home/ubuntu/helper.log', 'a') as helper:
                            # if this one fails - we are doing the reboot still - see the catch clause
                            subprocess.check_call('bash ./machine_boot.sh',
                                                  cwd=CORTEX_PATH,
                                                  shell=True,
                                                  timeout=30 * 60,
                                                  stderr=helper,
                                                  stdout=helper)
                            response = requests.get(f'https://127.0.0.1:{INTERNAL_PORT}/api/signup',
                                                    verify=False,
                                                    timeout=(10, 20))
                            if response.status_code != 200:
                                self.report_error(f'Gui is still down after re-raise')
                                self.report_error(f'{ERROR_MSG} {response.status_code} {response.text}')
                                raise Exception('Re-raise failed')  # raise failed, trigger reboot...
                            else:
                                self.report_info(f'Gui responds after re-raise! Child exits')
                                return  # it is important for child process to exit now!

                    else:
                        self.report_info(f'Spawned child process {ret_code}')
                        return

                except Exception as e:
                    # This code can be called either from parent process OR from child process
                    self.report_error(f'Failed during the restore procedure - restarting: {e}')
                    self.report_metric(metric_name=REBOOTING_MSG, metric_value=f'{e}')
                    time.sleep(30)
                    output = subprocess.check_output('/sbin/reboot --force', shell=True)
                    self.report_error(f'Reboot command sent')
                    self.report_error(f'Output is {output.decode()}')
                    time.sleep(120)
                    os.system('/sbin/shutdown -r now')
                finally:
                    if GUIALIVE_WATCHDOG_IN_PROGRESS.is_file():
                        GUIALIVE_WATCHDOG_IN_PROGRESS.unlink()


if __name__ == '__main__':
    gw = GuiAliveTask()
    gw.start()
