import shutil
import time
from pathlib import Path

PYTHON_INSTALLER_LOCK_FILE = Path('/tmp/python_installer.lock')
PYTHON_UPGRADE_LOCK_FILE = Path('/tmp/upgrade.lock')
LOCK_TOO_OLD_THRESH = 5 * 60 * 60


def get_free_disk_space():
    """
    Returns the free disk space in bytes. Notice that multiple mounting points can be present,
    so this returns the free disk space for the '/' of the running container. Since this is often a volume,
    it actually returns the number of bytes free on the mount on which the volume docker resides == on which docker
    is mounted.

    Another way to do this outside of a container would be:
    shutil.disk_usage(docker.from_env().info()['DockerRootDir']).free / (1024 ** 3)
    :return:
    """
    return shutil.disk_usage('/').free


def check_installer_locks():
    return check_installer_lock_file(PYTHON_INSTALLER_LOCK_FILE) or check_installer_lock_file(PYTHON_UPGRADE_LOCK_FILE)


def check_installer_lock_file(path):
    """
    check if python installer lock file exists and not older than LOCK_TOO_OLD_THRESH, delete it.
    :return:
    """
    if not path.is_file():
        return False
    if time.time() - path.stat().st_ctime > LOCK_TOO_OLD_THRESH:
        path.unlink()
        return False
    return True
