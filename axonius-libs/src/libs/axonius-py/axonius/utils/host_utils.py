import shutil
import time
from pathlib import Path
from datetime import timezone

import dateutil.parser

from axonius.consts.system_consts import CORTEX_PATH

PYTHON_LOCKS_DIR = Path('/tmp/ax-locks/')
PYTHON_INSTALLER_LOCK_FILE = PYTHON_LOCKS_DIR / 'python_installer.lock'
PYTHON_UPGRADE_LOCK_FILE = PYTHON_LOCKS_DIR / 'upgrade.lock'
GUIALIVE_WATCHDOG_IN_PROGRESS = PYTHON_LOCKS_DIR / 'guialive_watchdog_in_progress.lock'
MONGOALIVE_WATCHDOG_IN_PROGRESS = PYTHON_LOCKS_DIR / 'mongoalive_watchdog_in_progress.lock'
WEAVE_WATCHDOG_IN_PROGRESS = PYTHON_LOCKS_DIR / 'weave_watchdog_in_progress.lock'
WATCHDOGS_ARE_DISABLED_FILE = PYTHON_LOCKS_DIR / 'watchdogs_are_disabled.lock'
LOCK_TOO_OLD_THRESH = 5 * 60 * 60
# need to be outside of tmp folder for wd running outside host container
PYTHON_RESTORE_LOCK_FILE = Path(CORTEX_PATH) / 'restore/restore.lock'
RESTORE_LOCK_TOO_OLD_THRESH = 12 * 60 * 60


def get_free_disk_space():
    """
    Returns the free disk space in bytes. Notice that multiple
    mounting points can be present, so this returns the free disk
    space for the '/' of the running container. Since this is often
    a volume, it actually returns the number of bytes free on the
    mount on which the volume docker resides == on which docker
    is mounted.

    Another way to do this outside of a container would be:
    shutil.disk_usage(docker.from_env().info()['DockerRootDir']).free / (1024 ** 3)

    :return: The amount of free disk space in bytes
    """
    return shutil.disk_usage('/').free


def check_installer_locks(unlink: bool = True):
    return (check_lock_file(PYTHON_INSTALLER_LOCK_FILE, unlink=unlink) or
            check_lock_file(PYTHON_UPGRADE_LOCK_FILE, unlink=unlink) or
            check_lock_file(PYTHON_RESTORE_LOCK_FILE, unlink=unlink, lock_threshold=RESTORE_LOCK_TOO_OLD_THRESH))


def check_watchdog_action_in_progress():
    lockfiles = [
        GUIALIVE_WATCHDOG_IN_PROGRESS,
        MONGOALIVE_WATCHDOG_IN_PROGRESS,
        WEAVE_WATCHDOG_IN_PROGRESS
    ]
    return any(check_lock_file(lockfile) for lockfile in lockfiles)


def check_if_non_readonly_watchdogs_are_disabled():
    try:
        datetime_to_parse = WATCHDOGS_ARE_DISABLED_FILE.read_text().strip()
        date = dateutil.parser.parse(datetime_to_parse).astimezone(timezone.utc)
        if date.utcnow().astimezone(timezone.utc) < date:
            return True
    except Exception:
        pass

    return False


def create_lock_file(lock_filename: Path):
    try:
        if not PYTHON_LOCKS_DIR.is_dir():
            PYTHON_LOCKS_DIR.mkdir(exist_ok=True)
        lock_filename.touch()
        return True
    except Exception:
        return False


def check_lock_file(path: Path, unlink: bool = True, lock_threshold=LOCK_TOO_OLD_THRESH):
    """
    checks if lock file exists and not older than LOCK_TOO_OLD_THRESH. If it is, it deletes it.
    :return:
    """
    if not path.is_file():
        return False
    if time.time() - path.stat().st_ctime > lock_threshold:
        if unlink:
            try:
                path.unlink()
            except Exception:
                # lock is too old but the file cannot be deleted.
                return False
        return False
    return True
