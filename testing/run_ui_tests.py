#!/usr/bin/env python3
import os
import shlex
import signal
import subprocess
import sys
import argparse

import run_pytest
from devops.scripts.automate_dev import credentials_inputer
from services.adapters.ad_service import AdService
from services.adapters.json_file_service import JsonFileService
from services.axonius_service import get_service
from services.standalone_services.selenium_service import SeleniumService

TIMEOUT_EXIT_CODE = 1000    # This has to be a large integer. [1-6] are valid pytest exit codes.


class ArgumentParser(argparse.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.description = '''Example:
  %(prog)s --prepare-only
  %(prog)s --host-hub -k get_device_views_from_api testing/ui_tests/tests/test_api.py
  %(prog)s testing/ui_tests/tests/test_api.py'''

        self.add_argument('--host-hub', action='store_true',
                          help='Don\'t use selenium container, host is running hub')
        self.add_argument('--local-browser', action='store_true',
                          help='Don\'t use selenium container, host is running local browser')
        self.add_argument('--prepare-only', action='store_true',
                          help='Only initialize the test environment, dont run anything')


def print_frame(frame):
    print(f'{frame.f_code} at {frame.f_lineno}')
    if frame.f_back:
        print_frame(frame.f_back)


def signal_term_handler(signal_, frame):
    print(f'{signal_} signal handler')
    print_frame(frame)
    # Exit violently. Do not use sys.exit which can call other code.
    os._exit(TIMEOUT_EXIT_CODE)  # pylint: disable=protected-access


def cleanup(axonius_system, ad_service, json_service, selenium_service=None):

    if selenium_service:
        selenium_service.take_process_ownership()
        selenium_inner_logs = os.path.join(selenium_service.log_dir, 'selenium_inner_logs.log')
        cmd = f'docker exec grid /bin/sh -c "cat /var/log/cont/*" > {selenium_inner_logs}'
        subprocess.Popen(cmd, shell=True).communicate()
        # try to exit gracefully
        rc = subprocess.call(['docker', 'exec', 'grid', 'stop'], stderr=subprocess.STDOUT)
        print(f'return code from from exec grid stop: {rc}')
        rc = subprocess.call(['docker', 'stop', 'grid'], stderr=subprocess.STDOUT)
        print(f'return code from stop grid: {rc}')
        cmd = 'docker kill grid'
        subprocess.Popen(shlex.split(cmd)).communicate()
        cmd = 'docker rm -f grid'
        subprocess.Popen(shlex.split(cmd)).communicate()
        selenium_service.remove_volume()

    axonius_system.take_process_ownership()
    axonius_system.stop(should_delete=True)
    ad_service.take_process_ownership()
    ad_service.stop(should_delete=True)
    json_service.take_process_ownership()
    json_service.stop(should_delete=True)


def main():
    args, pytest = ArgumentParser().parse_known_args()
    if 'linux' in sys.platform.lower():
        current_hostname = subprocess.check_output('cat /etc/hostname', shell=True).decode('utf-8').strip()
        print(f'running ui tests on hostname {current_hostname}')

    # This is not the most generic way to get this flag but since we are going to (possibly) remove
    # this mechanism soon i think its a good-enough way for now.
    # The other solution (best one) is to change this whole file into fixtures that raise the system automatically
    if args.host_hub:
        pytest = ['--host-hub'] + pytest

    if args.local_browser:
        pytest = ['--local-browser'] + pytest

    should_use_local_selenium = not args.host_hub and not args.local_browser

    signal.signal(signal.SIGTERM, signal_term_handler)

    axonius_system = get_service()
    ad_service = AdService()
    json_service = JsonFileService()
    if should_use_local_selenium:
        selenium_service = SeleniumService()

    if args.prepare_only:
        try:
            cleanup(axonius_system, ad_service, json_service, selenium_service if should_use_local_selenium else None)
        except Exception as e:
            print(e)

    try:
        axonius_system.take_process_ownership()
        axonius_system.start_and_wait()

        if should_use_local_selenium:
            selenium_service.take_process_ownership()
            selenium_service.start_and_wait()

        ad_service.take_process_ownership()
        ad_service.start_and_wait()

        json_service.take_process_ownership()
        json_service.start_and_wait()

        credentials_inputer.main()

        if not args.prepare_only:
            print('Running UI tests')
            return run_pytest.run_pytest(pytest)
    finally:
        if not args.prepare_only:
            cleanup(axonius_system, ad_service, json_service, selenium_service if should_use_local_selenium else None)
    return 0


if __name__ == '__main__':
    sys.exit(main())
