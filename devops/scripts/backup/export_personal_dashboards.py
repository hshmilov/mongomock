import json
import os
import sys

from axonius.consts.gui_consts import DASHBOARD_SPACES_COLLECTION, USERS_COLLECTION, DASHBOARD_COLLECTION
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME, AXONIUS_USER_NAME, AXONIUS_RO_USER_NAME
from axonius.entities import EntityType
from axonius.utils.debug import redprint, greenprint
from testing.services.plugins.mongo_service import MongoService


def set_all_queries_from_chart_recursively(item, old_to_new_map: dict):
    """
    Goes over a chart config recursively. For every key in old_to_new_map, if it exists as value in the chart config,
    it gets replaced to it's value in old_to_new_map.
    :return:
    """

    if isinstance(item, dict):
        for sub_key, sub_item in item.items():
            item[sub_key] = set_all_queries_from_chart_recursively(sub_item, old_to_new_map)
        return item
    if isinstance(item, list):
        return [set_all_queries_from_chart_recursively(x, old_to_new_map) for x in item]
    if str(item) in old_to_new_map:
        new_item = old_to_new_map[str(item)]
        if isinstance(new_item, dict) and new_item.get('name'):
            return new_item.get('name')
        else:
            return str(item)

    return item


def main():
    if os.geteuid() != 0:
        redprint('This script must be run as root')
        return -1

    try:
        ms = MongoService()
        gui_db = ms.client[GUI_PLUGIN_NAME]
        views_map = ms.data.entity_views_collection

        all_users = {str(x['_id']): x for x in gui_db[USERS_COLLECTION].find({})}
        all_saved_queries = {
            str(x['_id']): x
            for x in list(views_map[EntityType.Devices].find({})) + list(views_map[EntityType.Users].find({}))
        }
        all_dashboards = {
            str(x['_id']): x for x in list(gui_db[DASHBOARD_COLLECTION].find({}))
        }
        all_personal_db = list(gui_db[DASHBOARD_SPACES_COLLECTION].find({'type': 'personal'}))
        for db_raw in all_personal_db:
            user_id = db_raw.get('user_id')
            if not user_id:
                continue

            panels_orders = db_raw.get('panels_order') or []
            if not panels_orders:
                continue

            user_details = all_users.get(str(user_id)) or {}
            if user_details:
                user_name = f'{user_details.get("user_name") or "Unknown"} ' \
                    f'({user_details.get("first_name") or ""} {user_details.get("last_name") or ""})'
            else:
                user_name = ""

            if AXONIUS_USER_NAME in user_name or AXONIUS_RO_USER_NAME in user_name:
                continue

            print(f'User "{user_name}": ')
            i = 0
            for panel_id in panels_orders:
                panel = all_dashboards.get(str(panel_id)) or {}
                if panel:
                    i = i + 1
                    greenprint(f'{i}. {panel.get("name")!r}')
                    new_panel = set_all_queries_from_chart_recursively(panel, all_saved_queries)
                    print(json.dumps(new_panel, indent=4, default=lambda o: str(o)))

    except Exception:
        if os.environ.get('DEBUG'):
            raise
        redprint('An error occured. Please contact Axonius')
        return -1


if __name__ == '__main__':
    sys.exit(main())
