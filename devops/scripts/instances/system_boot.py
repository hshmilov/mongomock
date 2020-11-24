#!/usr/bin/env python3
import subprocess
import time
from devops.scripts.instances.instances_consts import BOOTED_FOR_PRODUCTION_MARKER_PATH, CORTEX_PATH


def raise_system():
    subprocess.check_call(['./axonius.sh', 'system', 'up', '--all', '--restart', '--prod'],
                          cwd=str(CORTEX_PATH))


def wait_until_machine_is_ready():
    ready = False
    while not ready:
        try:
            docker_ps_output = subprocess.check_output(['docker', 'ps']).decode('utf-8')
            ready = 'CONTAINER ID' in docker_ps_output
            time.sleep(10)  # Just in case
        except subprocess.CalledProcessError:
            print('Not ready')
            time.sleep(10)


def chmod_cortex_dirs():
    subprocess.check_call('sudo find . -type d -exec chmod 755 {} \\;'.split(' '), cwd=str(CORTEX_PATH))


def set_unique_dns():
    subprocess.check_call(['./axonius.sh', 'system', 'register', '--all'],
                          cwd=str(CORTEX_PATH))


def main():
    try:
        BOOTED_FOR_PRODUCTION_MARKER_PATH.unlink()
    except FileNotFoundError:
        # A bit more defensive than checking for existence beforehand, let's not
        # be so fragile.
        pass
    # Waiting for weave network to be stable.
    wait_until_machine_is_ready()

    raise_system()
    print('System Is Ready.')

    # Putting marker to notify the system is stable and that it's not a new system.
    BOOTED_FOR_PRODUCTION_MARKER_PATH.touch()


if __name__ == '__main__':
    main()
