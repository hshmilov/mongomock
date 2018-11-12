#!/usr/bin/env python3
import shlex
import subprocess
import sys

import pytest

from services.axonius_service import get_service
from services.ports import DOCKER_PORTS
# from services.standalone_services.selenium_service import SeleniumService
from services.adapters.ad_service import AdService
from services.adapters.json_file_service import JsonFileService
from devops.scripts.automate_dev import credentials_inputer


def main():
    axonius_system = get_service()
    ad_service = AdService()
    json_service = JsonFileService()

    # selenium_service = SeleniumService()
    cmd = 'docker run -d --name=grid ' \
          f'-p {DOCKER_PORTS["selenium-hub"]}:24444 -p {DOCKER_PORTS["selenium-vnc"]}:25900 -e TZ="Asia/Jerusalem" ' \
          '-v /dev/shm:/dev/shm --privileged --link=gui:marxonius.com --network=axonius elgalu/selenium'
    subprocess.Popen(shlex.split(cmd)).communicate()
    cmd = 'docker exec grid wait_all_done 30s'
    subprocess.Popen(shlex.split(cmd)).communicate()

    try:
        axonius_system.take_process_ownership()
        axonius_system.start_and_wait()

        # selenium_service.take_process_ownership()
        # selenium_service.start_and_wait()

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
