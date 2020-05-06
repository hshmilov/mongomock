import datetime
import time
import subprocess

import dateutil.parser
import pymongo
import pytz

from axonius.consts.system_consts import NODE_MARKER_PATH, CORTEX_PATH
from axonius.utils.host_utils import check_installer_locks, check_watchdog_action_in_progress, \
    MONGOALIVE_WATCHDOG_IN_PROGRESS
from scripts.watchdog.watchdog_task import WatchdogTask
import docker

SLEEP_SECONDS = 5
NODE_MSG = 'this watchdog will not run on node'
MONGO_IS_DOWN = 'MONGO IS DOWN'

GUI_IS_DEAD_THRESH = 3 * 60 * 60


class MongoAliveTask(WatchdogTask):

    def __init__(self):
        super().__init__()
        environment = {'DOCKER_HOST': 'unix:///var/run/weave/weave.sock'}
        self.docker_client = docker.from_env(environment=environment)

    @staticmethod
    def check_mongo_connection_now():
        client = pymongo.MongoClient('127.0.0.1:27017', username='ax_user', password='ax_pass',
                                     connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
        list(client['core']['version'].find({}))

    def run(self):
        while True:
            time.sleep(SLEEP_SECONDS)
            try:
                if NODE_MARKER_PATH.is_file():
                    self.report_info(NODE_MSG)
                    continue

                if check_installer_locks():
                    self.report_info('upgrade is in progress...')
                    continue

                if check_watchdog_action_in_progress():
                    self.report_info(f'Other watchdog action in progress...')
                    continue

                try:
                    mongo_container = self.docker_client.containers.get('mongo')
                except Exception:
                    self.report_info(f'Mongo is not up. Have nothing to monitor')
                    continue

                mongo_status = mongo_container.attrs['State']['Status'].lower()
                if mongo_status != 'running':
                    self.report_info(f'Mongo container is up but not running ("{mongo_status}") '
                                     f'Have nothing to monitor')
                    continue

                mongo_started_at = dateutil.parser.parse(mongo_container.attrs['State']['StartedAt'])
                mongo_uptime = (datetime.datetime.now(pytz.utc) - mongo_started_at).total_seconds()

                if mongo_uptime < 60 * 60:
                    self.report_info(f'Mongo container is up but is running less than 1 hour ({mongo_uptime} seconds). '
                                     f'Not testing it In case it is in maintenance / restore')
                    time.sleep(60 * 20)
                    continue

                self.report_info(f'{self.name} is running. Mongo is up: {mongo_uptime}')
                try:
                    self.check_mongo_connection_now()
                    continue
                except Exception as e:
                    self.report_error(f'{MONGO_IS_DOWN}- {e}')

                retries = 0
                fixed = False
                while retries < 5 and not fixed:
                    retries += 1
                    time.sleep(2)
                    self.report_info(f'Retrying to connect to mongo')
                    try:
                        self.check_mongo_connection_now()
                        fixed = True
                    except Exception as e:
                        self.report_error(f'{MONGO_IS_DOWN} - {e}')
                    else:
                        self.report_info('Success connecting to mongo.')
                        break

                if not fixed:
                    MONGOALIVE_WATCHDOG_IN_PROGRESS.touch()
                    self.report_info(f'Restarting mongo and gui')
                    with open('/home/ubuntu/helper.log', 'a') as helper:
                        subprocess.check_call('./se.sh re mongo'.split(),
                                              cwd=CORTEX_PATH,
                                              timeout=300,
                                              stderr=helper,
                                              stdout=helper)
                        subprocess.check_call('./se.sh re gui'.split(),
                                              cwd=CORTEX_PATH,
                                              timeout=60,
                                              stderr=helper,
                                              stdout=helper)
                    self.report_info('Done restarting mongo and gui')
                    time.sleep(60 * 10)     # Avoid infinite loop of restarting
            except Exception as e:
                self.report_info(f'Error - Exception {e}')
            finally:
                if MONGOALIVE_WATCHDOG_IN_PROGRESS.is_file():
                    MONGOALIVE_WATCHDOG_IN_PROGRESS.unlink()


if __name__ == '__main__':
    gw = MongoAliveTask()
    gw.start()
