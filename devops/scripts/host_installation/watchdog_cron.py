#!/usr/local/bin/python3
import os
import subprocess
import shlex

WATCHDOG_CRON_SCRIPT_PATH = os.path.abspath(__file__)
WATCHDOG_MAIN_SCRIPT_PATH = os.path.join(os.path.dirname(WATCHDOG_CRON_SCRIPT_PATH), '..', 'watchdog',
                                         'watchdog_main')


def main():
    subprocess.Popen(shlex.split(f'{WATCHDOG_MAIN_SCRIPT_PATH} start detached'),
                     cwd=os.path.dirname(WATCHDOG_MAIN_SCRIPT_PATH),
                     preexec_fn=os.setsid)


if __name__ == '__main__':
    main()
