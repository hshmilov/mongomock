#!/usr/bin/env python3
import sys

import pytest

from services.standalone_services.selenium_service import SeleniumService


def main():
    selenium_service = SeleniumService()

    try:
        selenium_service.take_process_ownership()
        selenium_service.start(allow_restart=True)

        print('Running after upgrade tests')
        return pytest.main(
            ['-s', '-vv', '--showlocals', '--durations=0'] + sys.argv)
    finally:
        selenium_service.stop()


if __name__ == '__main__':
    sys.exit(main())
