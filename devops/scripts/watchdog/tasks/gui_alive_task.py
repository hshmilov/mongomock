import os
import subprocess
import time

import docker
import requests
import urllib3
from scripts.watchdog.watchdog_task import WatchdogTask

from axonius.consts.system_consts import CORTEX_PATH, NODE_MARKER_PATH
from axonius.utils.host_utils import check_installer_locks, check_watchdog_action_in_progress, \
    GUIALIVE_WATCHDOG_IN_PROGRESS, create_lock_file

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

            if check_installer_locks():
                self.report_info('upgrade is in progress...')
                continue

            if check_watchdog_action_in_progress():
                self.report_info(f'Other watchdog action in progress...')
                continue

            self.report_info(f'{self.name} is running')
            try:
                response = requests.get(f'https://localhost:{INTERNAL_PORT}/api/signup', verify=False, timeout=(10, 20))
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
                    mongo = self.docker_client.containers.get('mongo')
                    try:
                        mongo.stop(timeout=20 * 60)
                    except Exception as e:
                        self.report_error(f'Failed to stop mongo - {e}')
                        # If mongo does not stop in such long time we suspect a real docker system error,
                        # remove with force=True will just get stuck. It's better to reboot
                        raise
                    mongo.remove(force=True)
                    self.report_info(f'Stopped mongo')

                    for container in self.docker_client.containers.list():
                        self.report_info(f'Stopping {container.name}')
                        try:
                            container.stop(timeout=3)
                        except Exception as e:
                            self.report_info(f'Failed to stop {container.name} - {e}')
                        container.remove(force=True)
                        self.report_info(f'Stopped {container.name}')

                    self.report_info(f'restarting docker service')
                    subprocess.check_call('service docker restart'.split())
                    self.report_info(f'restarted docker service')

                    # fork the process so we won't get killed when the service is restarted
                    ret_code = os.fork()
                    if ret_code == 0:
                        # child process
                        time.sleep(5)
                        self.report_metric(RE_RAISING_MSG, metric_value=0)

                        with open('/home/ubuntu/helper.log', 'a') as helper:
                            # if this one fails - we are doing the reboot still - see the catch clause
                            subprocess.check_call('./axonius.sh system up --all --prod --restart'.split(),
                                                  cwd=CORTEX_PATH,
                                                  timeout=30 * 60,
                                                  stderr=helper,
                                                  stdout=helper)
                            response = requests.get(f'https://localhost:{INTERNAL_PORT}/api/signup', verify=False,
                                                    timeout=(10, 20))
                            if response.status_code != 200:
                                self.report_error(f'Gui is still down after re-raise')
                                self.report_error(f'{ERROR_MSG} {response.status_code} {response.text}')
                                raise Exception('Re-reaise failed')  # raise failed, trigger reboot...
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
                    os.system('reboot --force')
                    self.report_error(f'Reboot command sent')
                    time.sleep(120)
                    os.system('/sbin/shutdown -r now')
                finally:
                    if GUIALIVE_WATCHDOG_IN_PROGRESS.is_file():
                        GUIALIVE_WATCHDOG_IN_PROGRESS.unlink()


if __name__ == '__main__':
    gw = GuiAliveTask()
    gw.start()
