"""
Set plugin type to core
"""
import sys

from testing.services.plugins.core_service import CoreService


def main():
    configs = CoreService().db.client['core']['configs']

    print(f'[SET_CORE_PLUGIN_TYPE] setting plugin type...')
    configs.update_one(
        {'plugin_name': 'core'},
        {
            '$set': {
                'plugin_type': 'Plugin'
            }
        }
    )
    print(f'[SET_CORE_PLUGIN_TYPE] done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
