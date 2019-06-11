import os
import subprocess
import shlex

from axonius.consts.system_consts import PYRUN_PATH_HOST
from devops.scripts.watchdog.watchdog_main import WATCHDOG_MAIN_SCRIPT_PATH

WATCHDOG_CRON_SCRIPT_PATH = os.path.abspath(__file__)


def main():
    subprocess.Popen(shlex.split(f'{PYRUN_PATH_HOST} {WATCHDOG_MAIN_SCRIPT_PATH} start'),
                     preexec_fn=os.setsid)


if __name__ == '__main__':
    main()
