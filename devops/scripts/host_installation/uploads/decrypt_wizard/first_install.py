#!/usr/bin/env python3

import sys
from pathlib import Path
import subprocess
import time
import os

AXONIUS_DECRYPTED_FILE = Path(f'/home/ubuntu/cortex/axonius.sh')
INSTALL_LOCK = Path('/tmp/install.lock')

INSTALL_HOME = Path('/home/ubuntu')


def wait_until_machine_is_ready():
    ready = False
    while not ready:
        try:
            docker_ps_output = subprocess.check_output(['docker', 'ps']).decode('utf-8')
            ready = 'CONTAINER ID' in docker_ps_output
            time.sleep(60)  # Just in case
        except subprocess.CalledProcessError:
            print('Docker service is not ready')
            time.sleep(10)


def main():
    if os.getuid() != 0:
        print('Must run as root, exiting')
        return

    decryption_key = sys.argv[1]

    if AXONIUS_DECRYPTED_FILE.is_file():
        print(f'Install already in progress... ')
        return

    try:
        if INSTALL_LOCK.is_file():
            print(f'Decryption is already in process. ')
            return

        print(f'Testing decryption key ...')
        run_command_with_messages(f'gpg --batch --no-use-agent -dq -o /dev/null --passphrase {decryption_key} version.zip',
                                  ok_msg=f'Decryption key is correct',
                                  err_msg='Invalid decryption key',
                                  cwd=str(INSTALL_HOME),
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  shell=True)

        wait_until_machine_is_ready()
        print(f'Machine is ready, Axonius should start soon.')

        os.chdir(INSTALL_HOME)
        # this command should run after this user terminates ssh
        os.system(
            f'/usr/bin/nohup '
            f'/home/decrypt/install_and_run.sh {decryption_key} >> /var/log/machine_boot.log 2>&1 &')

    except Exception as e:
        print(e)


def run_command_with_messages(cmd, ok_msg, err_msg, **kwargs):
    process = subprocess.run(cmd, **kwargs)
    if process.returncode != 0:
        print(err_msg)
        raise Exception(f'Error during execution of {err_msg}')
    else:
        print(ok_msg)


if __name__ == '__main__':
    main()
