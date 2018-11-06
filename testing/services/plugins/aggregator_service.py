from typing import List

from retrying import retry

from axonius.entities import EntityType
from services.plugin_service import API_KEY_HEADER, PluginService
from axonius.consts.plugin_consts import GUI_NAME
from axonius.consts.gui_consts import USERS_COLLECTION
import requests


class AggregatorService(PluginService):
    def __init__(self):
        super().__init__('aggregator')

    def wait_for_service(self, *args, **kwargs):
        super().wait_for_service(*args, **kwargs)

    def _migrate_db(self):
        super()._migrate_db()
        if self.db_schema_version < 1:
            self._update_schema_version_1()
        if self.db_schema_version < 2:
            self._update_schema_version_2()

    def _update_schema_version_1(self):
        try:
            # moved from actual views to a collection that is constantly rebuilt
            # thus we drop the old views and make room for the collections that take their
            # place
            aggregator_db = self.db.client[self.plugin_name]
            collections_by_name = {x['name']: x for x in aggregator_db.list_collections()}
            for entity_type in EntityType:
                curr_name = f'{entity_type.value}_db_view'
                coll_data = collections_by_name.get(curr_name)
                if not coll_data:
                    continue
                # we must be careful, if for some reason this is not a view, it shouldn't be removed
                if coll_data.get('type') == 'view':
                    aggregator_db.drop_collection(curr_name)

            self.db_schema_version = 1
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 1. Details: {e}')

    def _update_schema_version_2(self):
        try:
            aggregator_db = self.db.client[self.plugin_name]
            entity_db_map = {
                EntityType.Users: aggregator_db['users_db'],
                EntityType.Devices: aggregator_db['devices_db'],
            }
            for system_user in self.db.client[GUI_NAME][USERS_COLLECTION].find({}):
                for entity_type in EntityType:
                    entity_db_map[entity_type].update_many({
                        'tags.name': 'Notes',
                        'tags.data.user_name': system_user['user_name']
                    }, {
                        '$set': {
                            'tags.$.data.$[].user_id': system_user['_id']
                        }
                    })

            self.db_schema_version = 2
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 2. Details: {e}')

    @retry(wait_random_min=2000, wait_random_max=7000, stop_max_delay=60 * 3 * 1000)
    def query_devices(self, adapter_id):
        response = requests.post(self.req_url + f"/trigger/{adapter_id}", headers={API_KEY_HEADER: self.api_key})

        assert response.status_code == 200, \
            f"Error in response: {str(response.status_code)}, " \
            f"{str(response.content)}"
        self.rebuild_views()
        return response

    def rebuild_views(self, internal_axon_ids: List[str] = None):
        url = f'/trigger/rebuild_entity_view?priority={bool(internal_axon_ids)}'
        return requests.post(self.req_url + url, headers={API_KEY_HEADER: self.api_key},
                             json={
                                 'internal_axon_ids': internal_axon_ids
        })

    def is_up(self):
        return super().is_up() and {"Triggerable"}.issubset(self.get_supported_features())
