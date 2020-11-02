import datetime
import subprocess
import sys
import os

from pymongo.database import Database

from axonius.consts.plugin_consts import HISTORICAL_DEVICES_DB_VIEW, HISTORICAL_USERS_DB_VIEW, \
    USER_ADAPTERS_HISTORICAL_RAW_DB, DEVICE_ADAPTERS_HISTORICAL_RAW_DB, DEVICES_DB, USERS_DB
from axonius.utils.debug import redprint, greenprint, yellowprint
from axonius.utils.host_utils import PYTHON_LOCKS_DIR, WATCHDOGS_ARE_DISABLED_FILE
from axonius.utils.mongo_administration import get_collection_stats
from testing.services.plugins.mongo_service import MongoService
from utils import CORTEX_PATH

COLLECTION_NAMES = [
    HISTORICAL_DEVICES_DB_VIEW, HISTORICAL_USERS_DB_VIEW,
    DEVICE_ADAPTERS_HISTORICAL_RAW_DB, USER_ADAPTERS_HISTORICAL_RAW_DB,
    DEVICES_DB, USERS_DB
]

MINIMUM_AVAILABLE_SPACE_TO_FREE = 30 * (1024 ** 3)      # we will not run compact for less than this amount of space


def main():
    try:
        try:
            _, action = sys.argv
        except Exception:
            action = None

        if os.geteuid() != 0:
            raise ValueError(f'Please run me as root!')

        if os.environ.get('TERM') != 'screen':
            raise ValueError(f'Please run me inside tmux!')

        amount_of_space_to_free = 0
        collections_to_defrag = []
        aggregator: Database = MongoService().client['aggregator']
        for collection_name in COLLECTION_NAMES:
            collection_stats = get_collection_stats(aggregator[collection_name])
            wired_tiger = collection_stats.get('wiredTiger') or {}
            available_for_reuse = (wired_tiger.get('block-manager') or {}).get('file bytes available for reuse')

            available_for_reuse_in_gb = round(available_for_reuse / (1024 ** 3), 2)
            if available_for_reuse >= MINIMUM_AVAILABLE_SPACE_TO_FREE:
                greenprint(f'De-fragmentation of {collection_name!r} will '
                           f'free {available_for_reuse_in_gb} GB, de-fragmenting')
                amount_of_space_to_free += available_for_reuse
                collections_to_defrag.append(collection_name)
            else:
                yellowprint(f'De-fragmentation of {collection_name!r} will '
                            f'free {available_for_reuse_in_gb} GB, not de-fragmenting')

        greenprint(f'Amount of space available for reuse: {round(amount_of_space_to_free / (1024 ** 3), 2)}')
        if action != '--wet':
            return 0

        greenprint(f'Disabling watchdogs for 24 hours...')
        time_to_disable = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        PYTHON_LOCKS_DIR.mkdir(parents=True, exist_ok=True)
        WATCHDOGS_ARE_DISABLED_FILE.write_text(str(time_to_disable))

        greenprint(f'Shutting down the system...')
        output = subprocess.check_output('docker ps --format \'{{.Names}}\'', shell=True).decode('utf-8')
        all_containers = ' '.join(
            [container_name.strip() for container_name in output.strip().splitlines()
             if container_name not in ['weave', 'mongo']]
        )

        for i in range(3):
            subprocess.call(f'docker rm -f {all_containers}', shell=True)

        for collection_name in collections_to_defrag:
            yellowprint(f'Running compact on {collection_name!r}...')
            aggregator.command({
                'compact': collection_name,
                'force': True
            })
            greenprint(f'Done running compact on {collection_name!r}.')

        greenprint(f'Rerunning the system...')
        subprocess.call(f'bash ./machine_boot.sh', cwd=CORTEX_PATH, shell=True)

        greenprint(f'Resuming watchdogs...')
        WATCHDOGS_ARE_DISABLED_FILE.unlink()

        greenprint(f'Done successfully.')
        return 0

    except Exception as e:
        redprint(f'Error: {str(e)}')
        if WATCHDOGS_ARE_DISABLED_FILE.exists():
            greenprint(f'Resuming watchdogs...')
            WATCHDOGS_ARE_DISABLED_FILE.unlink()
        return -1


if __name__ == '__main__':
    sys.exit(main())
