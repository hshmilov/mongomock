import sys
import os
import time

from testing.services.adapters.ad_service import AdService

MARKER = '/home/ubuntu/2_3_remove_ad_config.marker'


def main():
    print(f'Starting patch {sys.argv[0]}')
    if os.path.exists(MARKER):
        print(f'Marker exists! Exiting')
        return 0
    with open(MARKER, 'wt') as f:
        f.write('marker')
    ad_service = AdService()
    print(f'Found AD Service with unique name {ad_service.unique_name}')
    ad_service.set_configurable_config('AdapterBase', 'last_seen_prioritized', False)
    time.sleep(10)
    os.system(f'cd /home/ubuntu/cortex; ./se.sh af {ad_service.unique_name}')
    os.system(f'cd /home/ubuntu/cortex; ./se.sh sc run')


if __name__ == '__main__':
    sys.exit(main())
