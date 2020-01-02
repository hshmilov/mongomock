#!/usr/bin/env python3
import pwd
import subprocess
import sys
from pathlib import Path

LOGGED_IN_MARKER_PATH = Path('/home/ubuntu/cortex/.axonius_settings/.logged_in')
INSTANCE_USER_NAME = 'node_maker'

BOOTED_FOR_PRODUCTION = Path('/home/ubuntu/cortex/.axonius_settings/.booted_for_production')
DECRYPT_USER_NAME = 'decrypt'


def main():
    try:
        if LOGGED_IN_MARKER_PATH.exists() and pwd.getpwnam(INSTANCE_USER_NAME):
            if Path('/etc/sudoers.d/90-decrypt').exists():
                Path('/etc/sudoers.d/90-decrypt').unlink()
            subprocess.check_call(['/usr/sbin/userdel', '-f', '-r', INSTANCE_USER_NAME])
    except KeyError:
        # Case of pwd.getpwnam() user doesn't exist
        pass

    try:
        if BOOTED_FOR_PRODUCTION.exists() and pwd.getpwnam(DECRYPT_USER_NAME):
            subprocess.check_call(['/usr/sbin/userdel', '-f', '-r', DECRYPT_USER_NAME])
    except KeyError:
        # Case of pwd.getpwnam() user doesn't exist
        pass

    return sys.exit(0)


if __name__ == '__main__':
    main()
