#!/usr/bin/env python3
import sys

import pytest

from services.standalone_services.selenium_service import SeleniumService

UPGRAGE_TEST_ARTIFACT_FILE = '/home/ubuntu/cortex/logs/{0}_artifacts.xml'


def main():
    selenium_service = SeleniumService()

    try:
        selenium_service.take_process_ownership()
        selenium_service.start(allow_restart=True)

        print('Running after upgrade tests')
        return pytest.main(
            [f'-s',
             f'-vv',
             f'--junitxml={UPGRAGE_TEST_ARTIFACT_FILE.format(sys.argv[2].split("/")[1])}',
             f'--teamcity',
             f'--showlocals',
             f'--durations=0'] + sys.argv)
    finally:
        selenium_service.stop()


if __name__ == '__main__':
    sys.exit(main())
