#!/usr/bin/env python3
import os
import shlex
import subprocess
import signal
import sys

import run_pytest

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
    if os.name != 'nt':
        current_hostname = subprocess.check_output('cat /etc/hostname', shell=True).decode('utf-8').strip()
        print(f'running ui tests on hostname {current_hostname}')
    # This is not the most generic way to get this flag but since we are going to (possibly) remove
    # this mechanism soon i think its a good-enough way for now.
    # The other solution (best one) is to change this whole file into fixtures that raise the system automatically
    should_use_local_selenium = '--host-hub' not in sys.argv
    signal.signal(signal.SIGTERM, signal_term_handler)
    axonius_system = get_service()
    ad_service = AdService()
    json_service = JsonFileService()
    if should_use_local_selenium:
        selenium_service = SeleniumService()

    try:
        axonius_system.take_process_ownership()
        axonius_system.start_and_wait()

        if should_use_local_selenium:
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
        return run_pytest.run_pytest(sys.argv[1:])
    finally:
        if should_use_local_selenium:
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

        ad_service.stop(should_delete=True)
        json_service.stop(should_delete=True)
        axonius_system.stop(should_delete=True)


if __name__ == '__main__':
    sys.exit(main())
