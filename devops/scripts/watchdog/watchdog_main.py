from pathlib import Path
import os
import subprocess
import shlex
import sys

import docker

WATCHDOG_MAIN_SCRIPT_PATH = os.path.abspath(__file__)
TASKS_DIR = Path(os.path.abspath(os.path.dirname(__file__))) / 'tasks'


def run_tasks(action, detached=False):
    if os.name != 'posix' or docker.from_env().info()['OperatingSystem'] == 'Docker Desktop':
        print(f'will not spawn *nix style daemons')
    else:
        for task in TASKS_DIR.glob('*_task.py'):
            cmd = f'docker exec axonius-manager python3 {task} {action}' if not detached else \
                f'docker exec -d axonius-manager python3 {task} {action}'
            print(cmd)
            try:
                subprocess.call(shlex.split(cmd))
            except Exception as exc:
                print(f'{exc}')
                raise


def main():
    detached = False
    if len(sys.argv) == 1:
        action = 'start'
    elif len(sys.argv) == 3:
        action = sys.argv[1]
        detached = True
    else:
        action = sys.argv[1]

    run_tasks(action, detached)


if __name__ == '__main__':
    main()
