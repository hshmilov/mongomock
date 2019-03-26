from deployment.install import create_cronjob, AXONIUS_DEPLOYMENT_PATH
from pathlib import Path

SETUP_NETWORK_SCRIPT_PATH = Path(AXONIUS_DEPLOYMENT_PATH) / 'setup_network.sh'


def main():
    create_cronjob(SETUP_NETWORK_SCRIPT_PATH, '@reboot')


if __name__ == '__main__':
    main()
