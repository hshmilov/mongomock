import time
from pathlib import Path

from scripts.watchdog.watchdog_task import WatchdogTask
import subprocess
import shlex

SLEEP_SECONDS = 60 * 60 * 12  # that is 12 hrs

UPGRADE_LOCK = Path('/tmp/upgrade.lock')


def is_endpoint_false(endpoint):
    try:
        env = {'DOCKER_HOST': 'unix:///var/run/weave/weave.sock'}
        output = subprocess.check_output(
            shlex.split(f'docker run --rm appropriate/curl -kfsSL https://gui.axonius.local:443/api/{endpoint}'),
            env=env, timeout=60 * 2)
        output = output.decode().strip()
        return output == 'false'
    except Exception:
        return False


class ChefClientTask(WatchdogTask):
    def run(self):

        while True:
            if UPGRADE_LOCK.is_file():
                self.report_info('upgrade lock existed. skipping restart')
                time.sleep(60 * 60)  # wait until upgrade is complete
                continue
            else:

                try:
                    if is_endpoint_false('provision'):
                        self.report_info(f'provision was false, chef should be down')
                        continue

                    self.report_info('restarting chef client')
                    try:
                        self.report_info('a sync run')
                        if subprocess.check_call(shlex.split('chef-client'), timeout=60 * 60):
                            self.report_info('chef-client run failed, will restart the service anyway')
                    except Exception as e:
                        self.report_error(f'failed to complete a run - {e}')

                    subprocess.check_call(shlex.split(f'service chef-client restart'), timeout=60 * 10)
                    self.report_info(f'chef-client service restart completed')
                except Exception as e:
                    self.report_error(f'failed to restart - {e}')
                time.sleep(SLEEP_SECONDS)


if __name__ == '__main__':
    gw = ChefClientTask()
    gw.start()
