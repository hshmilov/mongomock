from pathlib import Path
import os
import subprocess
import shlex
import sys

from axonius.consts.system_consts import PYRUN_PATH_HOST

WATCHDOG_MAIN_SCRIPT_PATH = os.path.abspath(__file__)
TASKS_DIR = Path(os.path.abspath(os.path.dirname(__file__))) / 'tasks'


def run_tasks(action):
    if os.name != 'posix':
        print(f'will not spawn *nix style daemons')
    else:
        for task in TASKS_DIR.glob('*_task.py'):
            cmd = f'{PYRUN_PATH_HOST} {task} {action}'
            print(cmd)
            try:
                subprocess.call(shlex.split(cmd))
            except Exception as exc:
                print(f'{exc}')
                raise


def main():
    if len(sys.argv) == 1:
        action = 'start'
    else:
        action = sys.argv[1]

    run_tasks(action)


if __name__ == '__main__':
    main()
