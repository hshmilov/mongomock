import os
import subprocess
import shlex

WATCHDOG_CRON_SCRIPT_PATH = os.path.abspath(__file__)


def main():
    from devops.scripts.watchdog.watchdog_main import WATCHDOG_MAIN_SCRIPT_PATH
    subprocess.Popen(shlex.split(f'{WATCHDOG_MAIN_SCRIPT_PATH} start detached'), preexec_fn=os.setsid)


if __name__ == '__main__':
    main()
