from pathlib import Path
import os
import sys

import docker

from scripts.watchdog.tasks.chef_client_task_host import ChefClientTask
from scripts.watchdog.tasks.reset_passwords_task_host import ResetPasswordsTask

WATCHDOG_MAIN_SCRIPT_PATH = os.path.abspath(__file__)
TASKS_DIR = Path(os.path.abspath(os.path.dirname(__file__))) / 'tasks'


def run_tasks():
    if os.name != 'posix' or docker.from_env().info()['OperatingSystem'] == 'Docker Desktop':
        print(f'will not spawn *nix style daemons')
    else:
        rpt = ResetPasswordsTask()
        cct = ChefClientTask()
        rpt.start()
        cct.start()


def main():
    if len(sys.argv) != 2:
        print('Bad arguments')
        return
    run_tasks()


if __name__ == '__main__':
    main()
