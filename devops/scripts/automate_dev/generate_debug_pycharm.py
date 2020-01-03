from pathlib import Path
from devops.scripts.fast_axonius.fast_axonius import fast_axonius
from axonius.utils.debug import COLOR


def read_db_key():

    axon_setting = Path(__file__).absolute().parents[3] / '.axonius_settings'
    axon_setting_db_key = axon_setting / '.db_key'
    axon_setting_node_id = axon_setting / '.node_id'

    if axon_setting_db_key.is_file() and axon_setting_node_id.is_file():
        try:
            db_key = axon_setting_db_key.open().read()
            node_id = axon_setting_node_id.open().read()
            return db_key, node_id
        except Exception:
            print(f'{COLOR.get("red", "<")} error reading systems keys ')
    else:
        print(f'{COLOR.get("red", "<")} Folder .axonius_setting not exits ; '
              f'start system first in order to generate system keys ')
    return 'DB_KEY', 'NODE_ID'


def main():
    db_key, node_id = read_db_key()
    ax = fast_axonius()
    for service in list(ax._services.values()) + list(ax._plugins.values()):
        if hasattr(service, 'generate_debug_template'):
            service.generate_debug_template(db_key, node_id)


if __name__ == '__main__':
    main()
