import json
import sys

from bson import json_util
from testing.services.plugins.gui_service import GuiService


def main():
    try:
        # pylint: disable=unbalanced-tuple-unpacking
        _, mode = sys.argv
    except Exception:
        print(f'Usage: {sys.argv[0]} backup/restore')
        return -1

    gui = GuiService()

    device_view = gui.db.get_collection('gui', 'device_views')

    if mode == 'backup':
        saved_views_filter = {
            'query_type': 'saved',
            '$or': [
                {
                    'predefined': False
                },
                {
                    'predefined': {
                        '$exists': False
                    }
                }
            ]
        }

        with open('backup_views.json', 'wt') as f:
            f.write(
                json.dumps(
                    list(device_view.find(saved_views_filter, projection={'_id': 0})),
                    default=json_util.default
                )
            )

    elif mode == 'restore':
        admin_id = gui.db.client['gui']['users'].find_one({'user_name': 'admin'})['_id']
        with open('backup_views.json', 'rt') as f:
            views = json.loads(f.read(), object_hook=json_util.object_hook)
            for view in views:
                view['updated_by'] = admin_id
                view['user_id'] = admin_id
                try:
                    device_view.insert(view)
                except Exception:
                    print(f'Error inserting {view["name"]}')

    print(f'Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
