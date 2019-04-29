from deployment.install import create_cronjob, AXONIUS_DEPLOYMENT_PATH
from pathlib import Path

SETUP_NETWORK_SCRIPT_PATH = Path(AXONIUS_DEPLOYMENT_PATH) / 'setup_network.sh'
SETUP_SWAP_PATH = Path(AXONIUS_DEPLOYMENT_PATH) / 'create_swap.py'


def main():
    create_cronjob(SETUP_NETWORK_SCRIPT_PATH, '@reboot')
    create_cronjob(SETUP_SWAP_PATH, '@reboot', specific_run_env='/usr/local/bin/python3')


if __name__ == '__main__':
    main()
