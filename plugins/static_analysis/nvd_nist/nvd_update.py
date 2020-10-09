"""
Downloads the most recent version of the NVD, then parses it and removes unneeded information.
Requires internet connection to work.
"""
import logging
import os
import shlex
import subprocess
from axonius.consts.system_consts import CORTEX_PATH

logger = logging.getLogger(f'axonius.{__name__}')

# Paths
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_STATE_FILE = os.path.join(CURRENT_DIR, 'nvd_current_state.json')
ARTIFACT_FOLDER = os.path.join(CURRENT_DIR, 'artifacts')

NVD_ARTIFACTS_PATH = os.path.join(CORTEX_PATH, 'plugins', 'static_analysis', 'nvd_nist', 'artifacts')

NVD_SYNC_CMD = f'{os.path.join(CURRENT_DIR, "..", "nvdsync")} -cve_feed cve-1.1.json.gz {ARTIFACT_FOLDER}'


def update():
    update_from_internet()


def update_from_internet():
    """
    Downloads the files from the internet.
    :return:
    """
    try:
        subprocess.check_call(shlex.split(NVD_SYNC_CMD))
    except subprocess.CalledProcessError:
        logger.warning('Couldn\'t sync with NVD server for new CVE\'s')


def main():
    update()
    return 0


if __name__ == '__main__':
    main()
