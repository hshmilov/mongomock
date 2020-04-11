import sys

from testing.services.plugins.core_service import CoreService


def main():
    cs = CoreService()
    for config in cs.db.client['core']['configs'].find(
            {
                'plugin_type': 'Adapter',
                'status': 'up'
            }
    ):
        pun = config['plugin_unique_name']
        print(f'Checking {pun}')
        for triggerable in cs.db.client[config['plugin_unique_name']]['triggerable_history'].find({
            'finished_at': {'$exists': False}
        }):
            print(f'Found {pun} with {triggerable}')


if __name__ == '__main__':
    sys.exit(main())
