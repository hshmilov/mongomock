#!/usr/bin/env python3
"""
This script destroys the system:
    1. stops all running containers
    2. remove all containers
    3. removes all volumes
    4. *removes all images*
    5. optionally, removes all log files (unless --keep-logs is specified)
"""
import argparse
import os
import shutil
import subprocess
import sys

from utils import AutoOutputFlush, CORTEX_PATH, get_service


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keep-logs', action='store_true', default=False)
    parser.add_argument('--keep-diag', action='store_true', default=False)

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    axonius_system = get_service()
    axonius_system.take_process_ownership()
    services = [name for name, variable in axonius_system.get_all_plugins()]
    adapters = [name for name, variable in axonius_system.get_all_adapters()]

    print(f'Stopping system and {adapters + services}')
    exclude_restart = ['diagnostics'] if args.keep_diag else []
    axonius_system.stop_plugins(adapters, services, should_delete=True, remove_image=True,
                                exclude_restart=exclude_restart)
    axonius_system.stop(should_delete=True, remove_image=True)
    subprocess.check_call(['docker', 'rmi', 'axonius/axonius-libs', '--force'], stdout=subprocess.PIPE)
    subprocess.check_call(['docker', 'rmi', 'axonius/axonius-base-image', '--force'], stdout=subprocess.PIPE)
    axonius_system.delete_network()

    if not args.keep_logs:
        delete_logs()


def delete_logs():
    logs_path = os.path.join(CORTEX_PATH, 'logs')
    if os.path.isdir(logs_path):
        shutil.rmtree(logs_path, ignore_errors=True)


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
