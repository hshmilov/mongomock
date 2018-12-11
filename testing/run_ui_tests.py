#!/usr/bin/env python3
import shlex
import subprocess
import signal
import sys

import pytest

from services.axonius_service import get_service
from services.adapters.ad_service import AdService
from services.adapters.json_file_service import JsonFileService
from services.standalone_services.selenium_service import SeleniumService
from devops.scripts.automate_dev import credentials_inputer


def print_frame(frame):
    print(f'{frame.f_code} at {frame.f_lineno}')
    if frame.f_back:
        print_frame(frame.f_back)


def signal_term_handler(signal_, frame):
    print(f'{signal_} signal handler')
    print_frame(frame)
    raise TimeoutError


def main():
    signal.signal(signal.SIGTERM, signal_term_handler)
    axonius_system = get_service()
    ad_service = AdService()
    json_service = JsonFileService()
    selenium_service = SeleniumService()

    try:
        axonius_system.take_process_ownership()
        axonius_system.start_and_wait()

        selenium_service.take_process_ownership()
        selenium_service.start_and_wait()

        # Set up testing configurations
        axonius_system.core.set_execution_config(True)
        axonius_system.execution.post('update_config')

        ad_service.take_process_ownership()
        ad_service.start_and_wait()

        json_service.take_process_ownership()
        json_service.start_and_wait()

        credentials_inputer.main()

        print('Running UI tests')
        return pytest.main(
            ['-s', '-vv', '--showlocals', '--durations=0'] + sys.argv)
    finally:
        axonius_system.stop(should_delete=True)
        # selenium_service.stop(should_delete=True)
        cmd = 'docker kill grid'
        subprocess.Popen(shlex.split(cmd)).communicate()
        cmd = 'docker rm grid'
        subprocess.Popen(shlex.split(cmd)).communicate()

        ad_service.stop(should_delete=True)
        json_service.stop(should_delete=True)


if __name__ == '__main__':
    sys.exit(main())
