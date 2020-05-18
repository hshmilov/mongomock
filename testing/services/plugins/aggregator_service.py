import datetime
from multiprocessing.pool import ThreadPool
from threading import Lock

import pymongo
import shutil
import traceback
from collections import defaultdict
from typing import List, Tuple

from bson import Code
from pymongo.errors import OperationFailure, PyMongoError, BulkWriteError
from retrying import retry

from axonius.devices.device_adapter import LAST_SEEN_FIELD
from axonius.entities import EntityType
from axonius.utils.hash import get_preferred_quick_adapter_id
from axonius.utils.mongo_administration import get_collection_storage_size, create_capped_collection
from services.system_service import SystemService
from services.updatable_service import UpdatablePluginMixin
from services.plugin_service import API_KEY_HEADER, PluginService
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME, PLUGIN_NAME, PLUGIN_UNIQUE_NAME, ADAPTERS_LIST_LENGTH
from axonius.consts.gui_consts import USERS_COLLECTION
import requests


class AggregatorService(PluginService, SystemService, UpdatablePluginMixin):

    def __init__(self):
        super().__init__('aggregator')

    def _migrate_db(self):
        super()._migrate_db()
        if self.db_schema_version < 1:
            self._update_schema_version_1()
        if self.db_schema_version < 2:
            self._update_schema_version_2()
        if self.db_schema_version < 3:
            self._update_schema_version_3()
        if self.db_schema_version < 4:
            self._update_schema_version_4()
        if self.db_schema_version < 5:
            self._update_schema_version_5()
        if self.db_schema_version < 6:
            self._update_schema_version_6()
        if self.db_schema_version < 7:
            self._update_schema_version_7()
        if self.db_schema_version < 8:
            self._update_schema_version_8()
        if self.db_schema_version < 9:
            self._update_schema_version_9()
        if self.db_schema_version < 10:
            self._update_schema_version_10()
        if self.db_schema_version < 11:
            self._update_schema_version_11()
        if self.db_schema_version < 12:
            self._update_schema_version_12()
        if self.db_schema_version < 13:
            self._update_schema_version_13()
        if self.db_schema_version < 14:
            self._update_schema_version_14()
        if self.db_schema_version < 15:
            self.db_schema_version = 15  # self._update_schema_version_15() disabled due to a very long migration
        if self.db_schema_version < 16:
            self.db_schema_version = 16  # self._update_schema_version_16() disabled due to a very long migration
        if self.db_schema_version < 17:
            self._update_schema_version_17()
        if self.db_schema_version < 18:
            self._update_schema_version_18()
        if self.db_schema_version < 19:
            self._update_schema_version_19()
        if self.db_schema_version < 20:
            self._update_schema_version_20()
        if self.db_schema_version < 21:
            self._update_schema_version_21()
        if self.db_schema_version < 22:
            self._update_schema_version_22()
        if self.db_schema_version < 23:
            self._update_schema_version_23()
        if self.db_schema_version < 24:
            self._update_schema_version_24()
        if self.db_schema_version < 25:
            self._update_schema_version_25()
        if self.db_schema_version < 26:
            self._update_schema_version_26()
        if self.db_schema_version < 27:
            self._update_schema_version_27()
        if self.db_schema_version < 28:
            self._update_schema_version_28()
        if self.db_schema_version < 29:
            self._update_schema_version_29()
        if self.db_schema_version < 30:
            self._update_schema_version_30()
        if self.db_schema_version < 31:
            self._update_schema_version_31()
        if self.db_schema_version < 32:
            self._update_schema_version_32()

        if self.db_schema_version != 32:
            print(f'Upgrade failed, db_schema_version is {self.db_schema_version}')

    def __create_capped_collections(self):
        """
        Set up historical dbs as capped collections, if they aren't already
        """
        total_capped_data_on_disk = 0
        for entity_type in EntityType:
            col = self._historical_entity_views_db_map[entity_type]
            size = get_collection_storage_size(col)
            print(f'{col.name} size on disk is {size}')
            total_capped_data_on_disk += size

        # This is a bug! docker is not always mounted on root. to get the real disk usage do this:
        # shutil.disk_usage(docker.from_env().info()['DockerRootDir']).free / (1024 ** 3)
        disk_usage = shutil.disk_usage("/")
        # Size for all capped collections:
        # (disk_free + total_current_capped_collection) * 0.8 - 5GB
        # then, each collection will get a fair share
        actual_disk_free = disk_usage.free + total_capped_data_on_disk
        proper_capped_size = (actual_disk_free * 0.8 - 5 * 1024 * 1024 * 1024) / len(EntityType)

        print(f'Disk usage: {disk_usage}; virtually free is: {actual_disk_free}. '
              f'Calculated capped size: {proper_capped_size}')

        for entity_type in EntityType:
            create_capped_collection(self._historical_entity_views_db_map[entity_type], proper_capped_size)

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
            for system_user in self.db.client[GUI_PLUGIN_NAME][USERS_COLLECTION].find({}):
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

    def _update_schema_version_3(self):
        # https://axonius.atlassian.net/browse/AX-2643
        try:
            devices_db = self.db.client[self.plugin_name]['devices_db']

            for device in devices_db.find({
                'tags.plugin_unique_name': 'gui'
            }):
                relevant_tags = [
                    x
                    for x
                    in device['tags']
                    if x['type'] == 'label' and x.get('action_if_exists') == 'replace' and
                    x['plugin_unique_name'] == 'gui'
                ]
                tags_dict = {
                    x['name']: x
                    for x
                    in relevant_tags
                }

                for x in relevant_tags:
                    device['tags'].remove(x)

                device['tags'].extend(tags_dict.values())

                devices_db.replace_one({'_id': device['_id']},
                                       device)

            self.db_schema_version = 3
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 3. Details: {e}')
            traceback.print_exc()

    @staticmethod
    def fix_entity(entity) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """
        Given an axonius entity, calculates which adapters are new and which are false
        :return: Tuple [set_new, set_old] where each set it a list of [plugin_unique_name, id]
        for adapters that should be market new and old, respectfully.
        """
        adapters_by_name = defaultdict(list)
        for adapter in entity['adapters']:
            if adapter['data'].get(LAST_SEEN_FIELD) and '_old' not in adapter['data']:
                adapters_by_name[adapter[PLUGIN_NAME]].append(adapter)

        set_new = []
        set_old = []

        for name, adapters in adapters_by_name.items():
            newest = max(adapters, key=lambda x: x['data'][LAST_SEEN_FIELD])

            set_new.append((newest[PLUGIN_UNIQUE_NAME], newest['data']['id']))
            for adapter in adapters:
                if adapter != newest:
                    set_old.append((adapter[PLUGIN_UNIQUE_NAME], adapter['data']['id']))

        return set_new, set_old

    @staticmethod
    def update_many_adapters(db, to_set, _id, old_value):
        """
        Takes a set from "fix_entity" (see above) and updates the given axonius entity
        :param db: db to change
        :param to_set: one set from fix_entity
        :param _id: _id of entity to change
        :param old_value: which value to set into "data._old"
        """
        db.update_one({
            '_id': _id
        },
            {
                '$set': {
                    'adapters.$[i].data._old': old_value
                }
        },
            array_filters=[
                {
                    '$or': [
                        {
                            '$and': [
                                {f'i.{PLUGIN_UNIQUE_NAME}': unique_name},
                                {'i.data.id': adapter_id}
                            ]
                        }
                        for unique_name, adapter_id
                        in to_set
                    ]
                }
        ])

    def _update_schema_version_4(self):
        # https://axonius.atlassian.net/browse/AX-2698
        try:
            for entity_type in EntityType:
                db = self._entity_db_map[entity_type]

                # all entities that have last_seen but not _old must be fixed to also have _old
                # if there are two
                pending_fix = list(db.find({
                    'adapters': {
                        '$elemMatch': {
                            'data.last_seen': {
                                '$exists': True
                            },
                            'data._old': {
                                '$exists': False
                            }
                        }
                    }
                }))

                print(f'Fixing up {len(pending_fix)} entities for duplicates')

                for entity in pending_fix:
                    _id = entity['_id']
                    set_new, set_old = self.fix_entity(entity)
                    if set_new:
                        self.update_many_adapters(db, set_new, _id, False)

                    if set_old:
                        self.update_many_adapters(db, set_old, _id, True)

            self.db_schema_version = 4
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 4. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_5(self):
        try:
            devices_db = self.db.client[self.plugin_name]['devices_db']

            filter_ = {'adapters': {
                '$elemMatch': {
                    'adapter_properties': {
                        '$exists': True,
                    }
                }
            }
            }

            for device in devices_db.find(filter_):
                for adapter in device.get('adapters', []):
                    id_filter = {'internal_axon_id': device['internal_axon_id']}
                    update = {'$set':
                              {'adapters.$[i].data.adapter_properties': adapter.get('adapter_properties', [])}
                              }
                    array_filter = [{
                        f'i.{PLUGIN_UNIQUE_NAME}': adapter[PLUGIN_UNIQUE_NAME],
                        'i.data.id': adapter['data']['id']}]
                    devices_db.update_one(id_filter, update, array_filters=array_filter)

            self.db_schema_version = 5
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 5. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_6(self):
        # https://axonius.atlassian.net/browse/AX-2639
        def get_fields_from_collection(col, plugin_unique_name=None) -> List[str]:
            map_function = Code('''
                                function() {
                                recursion = function(name, val) {
                                    if (!val) {
                                        emit(name, null);
                                        return;
                                    }
                                    if (val.constructor === Array) {
                                        for (var i = 0; i < val.length; i++) {
                                            recursion(name, val[i]);
                                        }
                                        return;
                                    }

                                    if (val.constructor !== Object) {
                                        emit(name, null);
                                        return;
                                    }
                                    for (var key in val) {
                                        if (name == null) {
                                            recursion(key, val[key]);
                                        }
                                        else {
                                            recursion(name + '.' + key, val[key]);
                                        }
                                    }
                                }
                                for (var i = 0; i < this.adapters.length; ++i) {
                                    if (@PUN@ === true || this.adapters[i].plugin_unique_name == @PUN@) {
                                        recursion(null, this.adapters[i].data);
                                    }
                                }
                              }
                                '''.replace('@PUN@', f'\'{plugin_unique_name}\'' if plugin_unique_name else 'true'))
            reduce_function = Code('''function(key, stuff) { return null; }''')

            all_fields = []
            try:
                all_fields = col.map_reduce(
                    map_function,
                    reduce_function,
                    {
                        'inline': 1
                    })['results']
            except OperationFailure as operation_failure:
                if 'namespace does not exist' not in str(operation_failure):
                    raise
            return [x['_id'] for x in all_fields]

        try:
            for entity_type in EntityType:
                entities_db = self._entity_db_map[entity_type]
                fields_db = self.db.client['aggregator'][entity_type.value + '_fields']
                fields_db.update_one({
                    'name': 'exist'
                }, {
                    '$set': {
                        'fields': get_fields_from_collection(entities_db)
                    }
                },
                    upsert=True
                )
                adapters = list(self.db.client['core']['configs'].find({
                    'supported_features': 'Adapter'
                }))
                for adapter_i, adapter in enumerate(adapters):
                    plugin_unique_name = adapter['plugin_unique_name']
                    fields_db = self.db.client[plugin_unique_name][entity_type.value + '_fields']
                    fields_db.update_one({
                        'name': 'exist'
                    }, {
                        '$set': {
                            'fields': get_fields_from_collection(entities_db, plugin_unique_name)
                        }
                    },
                        upsert=True
                    )
                    print(f'{entity_type}: Adapters upgrade: finished {adapter_i} out of {len(adapters)}')

            self.db_schema_version = 6
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 6. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_7(self):
        try:
            all_adapters = list(self.db.client['core']['configs'].find())
            for entity_type in EntityType:
                global_fields_for_entity = self.db.client['aggregator'][entity_type.value + '_fields']
                for adapter in all_adapters:
                    all_field_data = list(self.db.client[adapter[PLUGIN_UNIQUE_NAME]][entity_type.value + '_fields'].
                                          find({}))
                    for field_data in all_field_data:
                        field_data[PLUGIN_UNIQUE_NAME] = adapter[PLUGIN_UNIQUE_NAME]
                        field_data.pop('_id', None)

                    if all_field_data:
                        global_fields_for_entity.insert_many(all_field_data)

            self.db_schema_version = 7
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 7. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_8(self):
        """
        We clear history before the rebuilds because the format has changed.
        Yes, we lose history, but it's not critical according to the bigboss.
        """
        try:
            for entity_type in EntityType:
                history_col = self.db.get_historical_entity_db_view(entity_type)
                if history_col.estimated_document_count():
                    history_col.rename(f'history_{entity_type.value}_old_data')
                else:
                    try:
                        history_col.drop()
                    except Exception:
                        pass

                col = self.db.get_entity_db(entity_type)

                for entity in col.find({
                    'tags.type': 'label'
                }):
                    # Yes, this is slow, but meh
                    for tag in entity.get('tags', []):
                        if tag.get('type') == 'label':
                            tag['label_value'] = tag.get('name') if tag.get('data', False) else ''
                    col.replace_one({
                        '_id': entity['_id']
                    }, entity)

            self.db_schema_version = 8
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 8. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_9(self):
        """
        We clear history before the rebuilds because the format has changed.
        Yes, we lose history, but it's not critical according to the bigboss.
        """
        try:
            for entity_type in EntityType:
                global_fields_for_entity = self.db.client['aggregator'][entity_type.value + '_fields']
                global_fields_for_entity.delete_many({
                    'name': 'dynamic',
                    'schema': {
                        '$exists': True
                    },
                    PLUGIN_UNIQUE_NAME: {
                        '$exists': False
                    }
                })

            self.db_schema_version = 9
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 9. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_10(self):
        """
        AX-3649 - fix adapter list length
        """
        try:
            for entity_type in EntityType:
                entities_db = self._entity_db_map[entity_type]
                to_fix = []
                for entity in entities_db.find({}, projection={
                    '_id': 1,
                    f'adapters.{PLUGIN_NAME}': 1,
                    ADAPTERS_LIST_LENGTH: 1
                }):
                    calculated_length = len(set(x[PLUGIN_NAME] for x in entity['adapters']))
                    if entity[ADAPTERS_LIST_LENGTH] != calculated_length:
                        to_fix.append(pymongo.operations.UpdateOne({
                            '_id': entity['_id']
                        }, {
                            '$set': {
                                ADAPTERS_LIST_LENGTH: calculated_length
                            }
                        }))

                if to_fix:
                    entities_db.bulk_write(to_fix, ordered=False)

            self.db_schema_version = 10
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 10. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_11(self):
        try:
            # Upgrade tanium id from {device_id} to {device_id}_{device_hostname}
            print(f'Upgading tanium to new id-format..')
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'tanium_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.data.id': 1,
                f'adapters.data.hostname': 1,
            }):
                all_taniums = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'tanium_adapter']
                for tanium_adapter in all_taniums:
                    tanium_data = tanium_adapter['data']
                    tanium_current_hostname = tanium_data.get('hostname')
                    tanium_current_id = tanium_data.get('id')
                    if tanium_current_hostname and tanium_current_id.endswith(f'_{tanium_current_hostname}'):
                        print(f'Found a valid Tanium record. Skipping upgrade process')
                        self.db_schema_version = 11
                        return
                    if tanium_current_hostname and not tanium_current_id.endswith(f'_{tanium_current_hostname}'):
                        tanium_new_id = f'{tanium_current_id}_{tanium_current_hostname}'
                        to_fix.append(pymongo.operations.UpdateOne({
                            '_id': entity['_id'],
                            f'adapters.data.id': tanium_current_id
                        }, {
                            '$set': {
                                'adapters.$.data.id': tanium_new_id
                            }
                        }))

            if to_fix:
                print(f'Upgrading Tanium ID format. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'Tanium upgrade: Nothing to fix. Moving on')

            self.db_schema_version = 11
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 11. Details: {e}')
            raise

    def _update_schema_version_12(self):
        """
        https://axonius.atlassian.net/browse/AX-4520
        """
        try:
            for entity_type in EntityType:
                entities_db = self._entity_db_map[entity_type]

                plugin_name = 'general_info'

                plugin_unique_names_to_fix = [x
                                              for x
                                              in entities_db.distinct('tags.plugin_unique_name')
                                              if f'{plugin_name}_' in x]
                if plugin_unique_names_to_fix:
                    print(f'plugins unique names to fix: {plugin_unique_names_to_fix}')

                for plugin_unique_name in plugin_unique_names_to_fix:
                    # Find all entities where they have the old (general_info_0) but not the new (general_info)
                    # and rename "general_info_0" to "general_info"
                    res = entities_db.update_many({
                        '$and': [
                            {
                                f'tags.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
                            },
                            {
                                f'tags.{PLUGIN_UNIQUE_NAME}': {
                                    '$ne': plugin_name
                                }
                            }
                        ]
                    }, {
                        '$set': {
                            f'tags.$[i].{PLUGIN_UNIQUE_NAME}': plugin_name
                        }
                    }, array_filters=[
                        {
                            f'i.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
                        }
                    ]
                    )
                    print(f'Stage one of fixing general info: {res.matched_count}, modified: {res.modified_count}')

                    # Fix tags.name
                    res = entities_db.update_many({
                        f'tags.name': plugin_unique_name
                    }, {
                        '$set': {
                            f'tags.$[i].name': plugin_name
                        }
                    }, array_filters=[
                        {
                            f'i.name': plugin_unique_name
                        }
                    ]
                    )
                    print(f'Stage two of fixing general info: {res.matched_count}, modified: {res.modified_count}')

                    # Fix tags.data.users.creation_source_plugin_unique_name
                    res = entities_db.update_many(
                        {
                            f'tags.data.users.creation_source_plugin_unique_name': plugin_unique_name
                        },
                        {
                            '$set': {
                                f'tags.$.data.users.$[i].creation_source_plugin_unique_name': plugin_name
                            }
                        }, array_filters=[
                            {
                                f'i.creation_source_plugin_unique_name': plugin_unique_name
                            }
                        ])
                    print(f'Stage three of fixing general info: {res.matched_count}, modified: {res.modified_count}')

                    # Find all entities that were affected already (having both general_info_0 and general_info)
                    # and simply remove the general_info_0
                    res = entities_db.update_many({
                        '$and': [
                            {
                                f'tags.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
                            },
                            {
                                f'tags.{PLUGIN_UNIQUE_NAME}': plugin_name
                            }
                        ]
                    }, {
                        '$pull': {
                            'tags': {
                                PLUGIN_UNIQUE_NAME: plugin_unique_name
                            }
                        }
                    })
                    print(f'Stage four of fixing general info: {res.matched_count}, modified: {res.modified_count}')

                    # Now, the same for adapters:

                    # Find all entities where they have the old (general_info_0) but not the new (general_info)
                    # and rename "general_info_0" to "general_info"
                    res = entities_db.update_many({
                        '$and': [
                            {
                                f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
                            },
                            {
                                f'adapters.{PLUGIN_UNIQUE_NAME}': {
                                    '$ne': plugin_name
                                }
                            }
                        ]
                    }, {
                        '$set': {
                            f'adapters.$[i].{PLUGIN_UNIQUE_NAME}': plugin_name,
                        }
                    }, array_filters=[
                        {
                            f'i.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
                        }
                    ]
                    )
                    print(f'Stage one for adapters: {res.matched_count}, modified: {res.modified_count}')

                    # Find all entities that were affected already (having both general_info_0 and general_info)
                    # and simply remove the general_info_0
                    res = entities_db.update_many({
                        '$and': [
                            {
                                f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
                            },
                            {
                                f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_name
                            }
                        ]
                    }, {
                        '$pull': {
                            'adapters': {
                                PLUGIN_UNIQUE_NAME: plugin_unique_name
                            }
                        }
                    })
                    print(f'Stage two for adapters: {res.matched_count}, modified: {res.modified_count}')

            self.db_schema_version = 12
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 12. Details: {e}')
            traceback.print_exc()

    def _update_schema_version_13(self):
        print('Upgrade to schema 13 - Convert Symantec Adapter client_id to a new format')
        try:
            def new_symantec_client_id(client_config):
                return client_config['domain'] + '_' + client_config['username'] + '_' + \
                    (client_config.get('username_domain') or '')

            self._upgrade_adapter_client_id('symantec_adapter', new_symantec_client_id)
            self.db_schema_version = 13
        except Exception as e:
            print(f'Exception while upgrading core db to version 13. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_14(self):
        print('Update to schema 14 - Convert Hyper-V adapter client_id to a new format')
        try:
            def hyper_v_new_client_id(client_config):
                return client_config['host'] + '_' + client_config.get('username')

            self._upgrade_adapter_client_id('hyper_v_adapter', hyper_v_new_client_id)
            self.db_schema_version = 14
        except Exception as e:
            print(f'Exception while upgrading core db to version 14. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_15(self):
        print('Update to schema 15 - update AWS SSM last seen')
        try:
            all_set_operations = []
            all_unset_operations = []
            devices_db = self._entity_db_map[EntityType.Devices]
            for device in devices_db.find(
                {'adapters.data.ssm_data': {'$exists': True}},
                projection={
                    '_id': 1,
                    f'adapters.{PLUGIN_NAME}': 1,
                    'adapters.data.id': 1,
                    'adapters.data.last_seen': 1,
                    'adapters.data.ssm_data':  1,
                }
            ):
                all_aws = [x for x in device['adapters'] if x[PLUGIN_NAME] == 'aws_adapter']
                for current_aws in all_aws:
                    current_aws_data = current_aws.get('data') or {}
                    if not current_aws_data.get('ssm_data'):
                        continue

                    if not current_aws_data.get('id'):
                        print(f'Warning! found aws ssm with no id')
                        continue

                    current_last_seen = current_aws_data.get('last_seen')
                    if current_last_seen:
                        all_set_operations.append(
                            pymongo.operations.UpdateOne(
                                {
                                    '_id': device['_id'],
                                    'adapters.data.id': current_aws_data['id']
                                },
                                {
                                    '$set': {
                                        'adapters.$.data.ssm_data.last_seen': current_last_seen
                                    }
                                }
                            )
                        )

                        all_unset_operations.append(
                            pymongo.operations.UpdateOne(
                                {
                                    '_id': device['_id'],
                                    'adapters.data.id': current_aws_data['id']
                                },
                                {
                                    '$unset': {
                                        'adapters.$.data.last_seen': 1
                                    }
                                }
                            )
                        )

            print(f'Going to fix {len(all_set_operations)} ssm devices')
            if all_set_operations:
                for i in range(0, len(all_set_operations), 1000):
                    devices_db.bulk_write(all_set_operations[i: i + 1000], ordered=False)
                    print(f'aws ssm last_seen addition: Fixed Chunk of {i + 1000} records')

                for i in range(0, len(all_unset_operations), 1000):
                    devices_db.bulk_write(all_unset_operations[i: i + 1000], ordered=False)
                    print(f'aws ssm last_seen removal: Fixed Chunk of {i + 1000} records')

            self.db_schema_version = 15
        except Exception as e:
            print(f'Exception while upgrading core db to version 15. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_16(self):
        # https://axonius.atlassian.net/browse/AX-4846
        print('Update to schema 16 - remove _old from all users')
        try:
            res = self._entity_db_map[EntityType.Users].update_many({
                'adapters.data._old': True
            }, {
                '$set': {
                    'adapters.$[].data._old': False
                }
            })
            print(f'Updates {res.modified_count} users from {res.matched_count} matches')

            include_outdated = 'INCLUDE OUTDATED: '
            views_collection = self._entity_views_map[EntityType.Users]
            saved_queries_cursor = views_collection.find({
                'view.query.filter': {
                    '$regex': f'^{include_outdated}'
                }
            }, projection={
                '_id': True,
                'view.query.filter': True
            })
            counter = 0
            for q in saved_queries_cursor:
                counter += 1
                new_query = q['view']['query']['filter'][len(include_outdated):]
                views_collection.update_one({
                    '_id': q['_id']
                }, {
                    '$set': {
                        'view.query.filter': new_query
                    }
                })
            print(f'Updated {counter} saved views')

            self.db_schema_version = 16
        except Exception as e:
            print(f'Exception while upgrading core db to version 16. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_17(self):
        try:
            # Upgrade solarwinds id from {device_id} to {device_id}_{device_name}
            print(f'Upgrading solarwinds to new id-format..')
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'solarwinds_orion_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.data.id': 1,
                f'adapters.data.name': 1,
            }):
                all_solarwinds = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'solarwinds_orion_adapter']
                for solarwinds_adapter in all_solarwinds:
                    solarwinds_data = solarwinds_adapter['data']
                    solarwinds_current_name = solarwinds_data.get('name')
                    solarwinds_current_id = solarwinds_data.get('id')
                    if '_' in solarwinds_current_id:
                        continue
                    if solarwinds_current_name and solarwinds_current_id.endswith(f'_{solarwinds_current_name}'):
                        continue
                    if solarwinds_current_name and not solarwinds_current_id.endswith(f'_{solarwinds_current_name}'):
                        solarwinds_new_id = f'{solarwinds_current_id}_{solarwinds_current_name}'
                        to_fix.append(pymongo.operations.UpdateOne({
                            '_id': entity['_id'],
                            f'adapters.data.id': solarwinds_current_id
                        }, {
                            '$set': {
                                'adapters.$.data.id': solarwinds_new_id
                            }
                        }))

            if to_fix:
                print(f'Upgrading Solarwinds ID format. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'Solarwinds upgrade: Nothing to fix. Moving on')

            self.db_schema_version = 17
        except Exception as e:
            print(f'Could not upgrade aggregator db to version 17. Details: {e}')
            raise

    def _update_schema_version_18(self):
        print(f'Fixing quick ids for solarwinds')
        devices_db = self._entity_db_map[EntityType.Devices]
        cursor = devices_db.find(
            {f'adapters.{PLUGIN_NAME}': 'solarwinds_orion_adapter'},
            projection={
                f'adapters.{PLUGIN_UNIQUE_NAME}': True,
                'adapters.data.id': True,
                '_id': True
            }
        )

        for entity_i, entity in enumerate(cursor):
            for adapter in entity['adapters']:
                if 'solarwinds' not in adapter[PLUGIN_UNIQUE_NAME]:
                    continue
                devices_db.update_one({
                    '_id': entity['_id'],
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: adapter[PLUGIN_UNIQUE_NAME],
                            'data.id': adapter['data']['id']
                        }
                    }
                }, {
                    '$set': {
                        'adapters.$.quick_id': get_preferred_quick_adapter_id(adapter[PLUGIN_UNIQUE_NAME],
                                                                              adapter['data']['id'])
                    }
                })

            if entity_i % 1000 == 0:
                print(f'Finished {entity_i} devices')

        print('Done')
        self.db_schema_version = 18

    def _update_schema_version_19(self):
        # https://axonius.atlassian.net/browse/AX-5401
        print('Update to schema 19 - add first fetch time')
        try:
            self._fix_db_for_entity(EntityType.Devices)
            self._fix_db_for_entity(EntityType.Users)
            self.db_schema_version = 19
        except Exception as e:
            print(f'Exception while upgrading core db to version 19. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_20(self):
        # https://axonius.atlassian.net/browse/AX-5401
        print('Update to schema 20 - azure and azure ad verify ssl')
        try:
            all_azure_pun = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'azure_adapter'}))
            all_azure_ad_pun = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'azure_ad_adapter'}))
            all_plugin_unique_names = [doc[PLUGIN_UNIQUE_NAME] for doc in (all_azure_pun + all_azure_ad_pun)]
            for plugin_unique_name in all_plugin_unique_names:
                self.db.client[plugin_unique_name]['clients'].update(
                    {},
                    {
                        '$set':
                            {
                                'verify_ssl': True
                            }
                    }
                )
            self.db_schema_version = 20
        except Exception as e:
            print(f'Exception while upgrading core db to version 20. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_21(self):
        print('Update to schema 21 - fix bigfix id')
        try:
            # Upgrade bigfix id from {device_id} to {device_id}_{device_hostname}
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'bigfix_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                f'adapters.data.id': 1,
                f'adapters.data.hostname': 1,
            }):
                all_bigfix = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'bigfix_adapter']
                for bigfix_adapter in all_bigfix:
                    bigfix_data = bigfix_adapter['data']
                    bigfix_current_hostname = bigfix_data.get('hostname')
                    bigfix_current_id = bigfix_data.get('id')
                    if not bigfix_current_id:
                        continue
                    if not bigfix_current_hostname:
                        continue
                    if bigfix_current_id.endswith(f'_{bigfix_current_hostname}'):
                        continue
                    bigfix_new_id = f'{bigfix_current_id}_{bigfix_current_hostname}'
                    to_fix.append(pymongo.operations.UpdateOne({
                        '_id': entity['_id'],
                        f'adapters.data.id': bigfix_current_id
                    }, {
                        '$set': {
                            'adapters.$.data.id': bigfix_new_id,
                            'adapters.$.quick_id': get_preferred_quick_adapter_id(bigfix_adapter[PLUGIN_UNIQUE_NAME],
                                                                                  bigfix_new_id)
                        }
                    }))

            if to_fix:
                print(f'Upgrading Bigfix ID format. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'Bigfix upgrade: Nothing to fix. Moving on')

            self.db_schema_version = 21
        except Exception as e:
            print(f'Exception while upgrading core db to version 21. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_22(self):
        print('Update to schema 22 - enable cisco ise fetch endpoint')
        try:
            # Activate cisco ise "fetch endpoints" only if clients already connected
            cisco_ise_adapters = list(self.db.client['core']['configs'].find({PLUGIN_NAME: 'cisco_ise_adapter'}))
            cisco_ise_names = [doc[PLUGIN_UNIQUE_NAME] for doc in cisco_ise_adapters]
            for plugin_unique_name in cisco_ise_names:
                if self.db.client[plugin_unique_name]['clients'].find_one():
                    self.db.client[plugin_unique_name]['configurable_configs'].update_one(
                        {"config_name": "CiscoIseAdapter"},
                        {'$set': {'config': {'fetch_endpoints': True}}}
                    )

            self.db_schema_version = 22
        except Exception as e:
            print(f'Exception while upgrading core db to version 22. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_23(self):
        print('Update to schema 23 - fix sccm  id')
        try:
            # Upgrade sccm id from {device_id} to {device_id}_{device_hostname}
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'sccm_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                f'adapters.data.id': 1,
                f'adapters.data.hostname': 1,
            }):
                all_sccm = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'sccm_adapter']
                for sccm_adapter in all_sccm:
                    sccm_data = sccm_adapter['data']
                    sccm_current_hostname = sccm_data.get('hostname')
                    sccm_current_id = sccm_data.get('id')
                    if not sccm_current_id:
                        continue
                    if not sccm_current_hostname:
                        continue
                    if sccm_current_id.endswith(f'${sccm_current_hostname}'):
                        continue
                    sccm_new_id = f'{sccm_current_id}${sccm_current_hostname}'
                    to_fix.append(pymongo.operations.UpdateOne({
                        '_id': entity['_id'],
                        f'adapters.quick_id': get_preferred_quick_adapter_id(
                            sccm_adapter[PLUGIN_UNIQUE_NAME], sccm_current_id
                        )
                    }, {
                        '$set': {
                            'adapters.$.data.id': sccm_new_id,
                            'adapters.$.quick_id': get_preferred_quick_adapter_id(
                                sccm_adapter[PLUGIN_UNIQUE_NAME], sccm_new_id
                            )
                        }
                    }))

            if to_fix:
                print(f'Upgrading Sccm ID format. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'Sccm upgrade: Nothing to fix. Moving on')

            self.db_schema_version = 23
        except Exception as e:
            print(f'Exception while upgrading core db to version 23. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_24(self):
        """
        See Jira Issue: AX-5956
        """
        print('Update to schema 24 - remove aggregated fields index')
        try:
            # Remove aggregated fields indexes
            for current_collection in ['devices_db', 'users_db',
                                       'historical_devices_db_view', 'historical_users_db_view']:
                try:
                    self.db.client['aggregator'][current_collection].drop_index([('hostnames', pymongo.ASCENDING)])
                except PyMongoError:
                    print(f'Index hostnames doesn\'t exist on {current_collection}')
                try:
                    self.db.client['aggregator'][current_collection].drop_index([('last_seen', pymongo.ASCENDING)])
                except PyMongoError:
                    print(f'Index last_seen doesn\'t exist on {current_collection}')
            self.db_schema_version = 24
        except Exception as e:
            print(f'Exception while upgrading aggregator db to version 24. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_25(self):
        print('Update to schema 25 - fix airwatch id')
        try:
            # Upgrade airwatch id from {device_id} to {device_id}_{device_name}
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'airwatch_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                f'adapters.data.id': 1,
                f'adapters.data.name': 1,
            }):
                all_airwatch = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'airwatch_adapter']
                for airwatch_adapter in all_airwatch:
                    airwatch_data = airwatch_adapter['data']
                    airwatch_current_name = airwatch_data.get('name')
                    airwatch_current_id = airwatch_data.get('id')
                    if not airwatch_current_id:
                        continue
                    if not airwatch_current_name:
                        continue
                    if airwatch_current_id.endswith(f'_{airwatch_current_name}'):
                        continue
                    airwatch_new_id = f'{airwatch_current_id}_{airwatch_current_name}'
                    to_fix.append(pymongo.operations.UpdateOne({
                        '_id': entity['_id'],
                        f'adapters.data.id': airwatch_current_id
                    }, {
                        '$set': {
                            'adapters.$.data.id': airwatch_new_id,
                            'adapters.$.quick_id': get_preferred_quick_adapter_id(
                                airwatch_adapter[PLUGIN_UNIQUE_NAME], airwatch_new_id
                            )
                        }
                    }))

            if to_fix:
                print(f'Upgrading Airwatch ID format. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'Airwatch upgrade: Nothing to fix. Moving on')

            self.db_schema_version = 25
        except Exception as e:
            print(f'Exception while upgrading core db to version 25. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_26(self):
        print('Update to schema 26 - fix quick_id for ad-sccm')
        try:
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'active_directory_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                f'adapters.data.id': 1,
                f'adapters.quick_id': 1,
            }):
                all_ad = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'active_directory_adapter']
                for ad_adapter in all_ad:
                    ad_current_plugin_unique_name = ad_adapter[PLUGIN_UNIQUE_NAME]
                    ad_current_quick_id = ad_adapter['quick_id']
                    ad_current_id = ad_adapter['data'].get('id')
                    if not ad_current_id:
                        continue
                    if not ad_current_plugin_unique_name:
                        continue
                    if not ad_current_quick_id:
                        continue
                    if '$' not in ad_current_id:
                        continue
                    ad_preferred_quick_id_adapter = get_preferred_quick_adapter_id(
                        ad_current_plugin_unique_name, ad_current_id
                    )

                    if ad_current_quick_id != ad_preferred_quick_id_adapter:
                        to_fix.append(pymongo.operations.UpdateOne({
                            '_id': entity['_id'],
                            f'adapters.quick_id': ad_current_quick_id
                        }, {
                            '$set': {
                                'adapters.$.quick_id': ad_preferred_quick_id_adapter
                            }
                        }))

            if to_fix:
                print(f'Upgrading AD Quick ID. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'AD Quick ID upgrade: Nothing to fix. Moving on')

            self.db_schema_version = 26
        except Exception as e:
            print(f'Exception while upgrading core db to version 26. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_27(self):
        print('Update to schema 27 - migrate tanium id')
        try:
            # for each tanium id that starts with SQ_DEVICE or ASSET_DEVICE, fix the id to the new format
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            # Get all devices which have tanium adapter
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'tanium_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                f'adapters.data.id': 1,
                f'adapters.data.uuid': 1,
                f'adapters.data.asset_report': 1,
                f'adapters.data.sq_name': 1
            }):
                # Then go on all tanium device-adapters on each device (each device might have multiple tanium adapters)
                all_tanium = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'tanium_adapter']
                for tanium_adapter in all_tanium:
                    tanium_data = tanium_adapter['data']
                    tanium_uuid = tanium_data.get('uuid') or ''
                    tanium_current_id = tanium_data.get('id')
                    if not tanium_current_id:
                        continue
                    if tanium_current_id.startswith('SQ_DEVICE'):
                        sq_name = tanium_data.get('sq_name') or ''  # if does not exist, this is '', and not None
                        tanium_new_id = f'SQ_DEVICE_{sq_name}_{tanium_uuid}'
                    elif tanium_current_id.startswith('ASSET_DEVICE'):
                        report_name = tanium_data.get('asset_report')    # could be None and that is fine
                        tanium_new_id = f'ASSET_DEVICE_{report_name}_{tanium_uuid}'
                    else:
                        continue
                    to_fix.append(pymongo.operations.UpdateOne({
                        '_id': entity['_id'],
                        f'adapters.quick_id': get_preferred_quick_adapter_id(
                            tanium_adapter[PLUGIN_UNIQUE_NAME], tanium_current_id
                        )
                    }, {
                        '$set': {
                            'adapters.$.data.id': tanium_new_id,
                            'adapters.$.quick_id': get_preferred_quick_adapter_id(
                                tanium_adapter[PLUGIN_UNIQUE_NAME], tanium_new_id
                            )
                        }
                    }))

            if to_fix:
                print(f'Upgrading Tanium ID format. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'Tanium ID upgrade: Nothing to fix. Moving on')
            self.db_schema_version = 27
        except BulkWriteError as e:
            print(f'BulkWriteError: {e.details}')
            raise
        except Exception as e:
            print(f'Exception while upgrading core db to version 27. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_30(self):
        print('Update to schema 30 - remove _old from all devices')
        try:
            res = self._entity_db_map[EntityType.Devices].update_many({
                'adapters.data._old': True
            }, {
                '$set': {
                    'adapters.$[].data._old': False
                }
            })
            print(f'Updates {res.modified_count} devices from {res.matched_count} matches')

            include_outdated = 'INCLUDE OUTDATED: '
            views_collection = self._entity_views_map[EntityType.Devices]
            saved_queries_cursor = views_collection.find({
                'view.query.filter': {
                    '$regex': f'^{include_outdated}'
                }
            }, projection={
                '_id': True,
                'view.query.filter': True
            })
            counter = 0
            for q in saved_queries_cursor:
                counter += 1
                new_query = q['view']['query']['filter'][len(include_outdated):]
                views_collection.update_one({
                    '_id': q['_id']
                }, {
                    '$set': {
                        'view.query.filter': new_query
                    }
                })
            print(f'Updated {counter} saved views')
            self.db_schema_version = 30
        except Exception as e:
            print(f'Exception while upgrading core db to version 30. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_28(self):
        print('Update to schema 28 - migrate tanium devices to sub-adapters')
        try:
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            # Get all devices which have tanium adapter
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'tanium_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                f'adapters.quick_id': 1,
                f'adapters.data.id': 1,
                f'adapters.data.tanium_type': 1,
            }):
                # Then go on all tanium device-adapters on each device (each device might have multiple tanium adapters)
                all_tanium = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'tanium_adapter']
                for tanium_adapter in all_tanium:
                    tanium_quick_id = tanium_adapter.get('quick_id')
                    if not tanium_quick_id:
                        continue

                    tanium_data = tanium_adapter['data']
                    tanium_type = tanium_data.get('tanium_type')
                    tanium_current_id = tanium_data.get('id')
                    if not tanium_current_id:
                        continue
                    if not tanium_type:
                        continue

                    # Mapping
                    tanium_type_to_adapter = {
                        'Saved Question Device': 'tanium_sq_adapter',
                        'Discover Device': 'tanium_discover_adapter',
                        'Asset Device': 'tanium_asset_adapter'
                    }

                    new_plugin_name = tanium_type_to_adapter.get(tanium_type)
                    if not new_plugin_name:
                        continue

                    # Assume the first registration of the tanium adapter. Note that this can be incorrect
                    # in the case of complex systems (master + nodes) where tanium_X_adapter_0 will be in a different
                    # node than the master.
                    new_plugin_unique_name = f'{new_plugin_name}_0'

                    to_fix.append(pymongo.operations.UpdateOne({
                        '_id': entity['_id'],
                        f'adapters.quick_id': tanium_quick_id,
                    }, {
                        '$set': {
                            'adapters.$.plugin_name': new_plugin_name,
                            'adapters.$.plugin_unique_name': new_plugin_unique_name,
                            'adapters.$.quick_id': get_preferred_quick_adapter_id(
                                new_plugin_unique_name, tanium_current_id
                            )
                        }
                    }))

            if to_fix:
                print(f'Migrating tanium devices to tanium new sub-adapters. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'Tanium ID upgrade: Nothing to fix. Moving on')
            self.db_schema_version = 28
        except Exception as e:
            print(f'Exception while upgrading core db to version 28. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_29(self):
        """
        https://axonius.atlassian.net/browse/AX-6563
        """
        print('Update to schema 29 - remove old_device_archive collection')
        try:
            self.db.client['aggregator']['old_device_archive'].drop()
            self.db_schema_version = 29
        except Exception as e:
            print(f'Exception while upgrading aggregator db to version 29. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_31(self):
        print('Update to schema 31 - migrate cherwell id')
        try:
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            # Get all devices which have cherwell adapter
            for entity in entities_db.find({f'adapters.{PLUGIN_NAME}': 'cherwell_adapter'}, projection={
                '_id': 1,
                f'adapters.{PLUGIN_NAME}': 1,
                f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                f'adapters.data.id': 1,
                f'adapters.data.bus_ob_id': 1,
                f'adapters.data.bus_ob_rec_id': 1,
                f'adapters.data.device_serial': 1
            }):
                # Then go on all cherwell device-adapters on each device
                all_cherwell = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'cherwell_adapter']
                for cherwell_adapter in all_cherwell:
                    cherwell_data = cherwell_adapter['data']
                    cherwell_bus_ob_id = cherwell_data.get('bus_ob_id') or ''
                    cherwell_bus_ob_rec_id = cherwell_data.get('bus_ob_rec_id') or ''
                    cherwell_device_serial = cherwell_data.get('device_serial')

                    cherwell_current_id = cherwell_data.get('id')
                    if not cherwell_current_id:
                        continue

                    # Calculate new id
                    cherwell_new_id = cherwell_bus_ob_id + '_' + cherwell_bus_ob_rec_id
                    if cherwell_device_serial:
                        cherwell_new_id += '_' + cherwell_device_serial

                    # If this has been already migrated, move on
                    if cherwell_current_id == cherwell_new_id:
                        continue

                    # Else, add to the list of fixes
                    to_fix.append(pymongo.operations.UpdateOne({
                        '_id': entity['_id'],
                        f'adapters.quick_id': get_preferred_quick_adapter_id(
                            cherwell_adapter[PLUGIN_UNIQUE_NAME], cherwell_current_id
                        )
                    }, {
                        '$set': {
                            'adapters.$.data.id': cherwell_new_id,
                            'adapters.$.quick_id': get_preferred_quick_adapter_id(
                                cherwell_adapter[PLUGIN_UNIQUE_NAME], cherwell_new_id
                            )
                        }
                    }))

            if to_fix:
                print(f'Upgrading Cherwell ID format. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'Cherwell ID upgrade: Nothing to fix. Moving on')
            self.db_schema_version = 31
        except BulkWriteError as e:
            print(f'BulkWriteError: {e.details}')
            raise
        except Exception as e:
            print(f'Exception while upgrading core db to version 31. Details: {e}')
            traceback.print_exc()
            raise

    def _update_schema_version_32(self):
        print('Update to schema 32 - migrate AWS RDS ID')
        try:
            entities_db = self._entity_db_map[EntityType.Devices]
            to_fix = []
            for entity in entities_db.find(
                    {
                        f'adapters.data.aws_device_type': 'RDS'
                    },
                    projection={
                        '_id': 1,
                        f'adapters.{PLUGIN_NAME}': 1,
                        f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
                        f'adapters.data.id': 1,
                        f'adapters.data.aws_device_type': 1,
                        f'adapters.data.rds_data.db_instance_arn': 1,
                    }
            ):
                # Then go on all AWS RDS device-adapters on each device
                all_aws_rds = [x for x in entity['adapters'] if x[PLUGIN_NAME] == 'aws_adapter']
                for aws_rds in all_aws_rds:
                    aws_rds_data = aws_rds['data']
                    if aws_rds_data.get('aws_device_type') != 'RDS':
                        continue

                    aws_rds_current_id = aws_rds_data.get('id')
                    if not aws_rds_current_id:
                        continue

                    aws_rds_new_id = (aws_rds_data.get('rds_data') or {}).get('db_instance_arn')
                    if not aws_rds_new_id:
                        continue

                    # If this has been already migrated, move on
                    if aws_rds_current_id == aws_rds_new_id:
                        continue

                    # Else, add to the list of fixes
                    to_fix.append(pymongo.operations.UpdateOne({
                        '_id': entity['_id'],
                        f'adapters.quick_id': get_preferred_quick_adapter_id(
                            aws_rds[PLUGIN_UNIQUE_NAME], aws_rds_current_id
                        )
                    }, {
                        '$set': {
                            'adapters.$.data.id': aws_rds_new_id,
                            'adapters.$.data.cloud_id': aws_rds_new_id,
                            'adapters.$.quick_id': get_preferred_quick_adapter_id(
                                aws_rds[PLUGIN_UNIQUE_NAME], aws_rds_new_id
                            )
                        }
                    }))

            if to_fix:
                print(f'Upgrading AWS RDS ID format. Found {len(to_fix)} records..')
                for i in range(0, len(to_fix), 1000):
                    entities_db.bulk_write(to_fix[i: i + 1000], ordered=False)
                    print(f'Fixed Chunk of {i + 1000} records')
            else:
                print(f'AWS RDS ID upgrade: Nothing to fix. Moving on')
            self.db_schema_version = 32
        except BulkWriteError as e:
            print(f'BulkWriteError: {e.details}')
            raise
        except Exception as e:
            print(f'Exception while upgrading core db to version 32. Details: {e}')
            traceback.print_exc()
            raise

    def _fix_db_for_entity(self, entity_type: EntityType):
        col = self._entity_db_map[entity_type]
        estimated_count = col.estimated_document_count()
        start_time = datetime.datetime.now()
        print(f'Fixing for entity {entity_type}, count is {estimated_count}, starting at {start_time}')

        class Expando:
            pass

        o = Expando()

        o.counter = 0
        o.adapter_entities_counter = 0
        lock = Lock()
        cursor = col.find({
            'adapters': {
                '$elemMatch': {
                    'data.first_fetch_time': {
                        '$exists': False
                    }
                }
            }
        }, projection={
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
            'adapters.data.id': True,
            'adapters.data.fetch_time': True,
            '_id': True
        })

        def process_entity(entity):
            for adapter in entity['adapters']:
                fetch_time = adapter.get('data', {}).get('fetch_time')
                eid = entity['_id']
                if not fetch_time:
                    print(f'No fetch time data for {eid}')
                    continue
                col.update_one({
                    '_id': eid,
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: adapter[PLUGIN_UNIQUE_NAME],
                            'data.id': adapter['data']['id']
                        }
                    }
                }, {
                    '$set': {
                        'adapters.$.data.first_fetch_time': fetch_time
                    }
                })
                with lock:
                    o.adapter_entities_counter += 1

            with lock:
                o.counter += 1
                if o.counter % 2000 == 0:
                    print(f'{o.counter} out of {estimated_count} completed, {(o.counter / estimated_count) * 100}%, '
                          f'took {(datetime.datetime.now() - start_time).total_seconds()} seconds')

        with ThreadPool(30) as pool:
            pool.map(process_entity, cursor)

        total_seconds = (datetime.datetime.now() - start_time).total_seconds()
        print(f'Took {total_seconds} seconds, {o.counter / total_seconds} entities/second, '
              f'total of {o.adapter_entities_counter} adapte entities, '
              f'{o.adapter_entities_counter / total_seconds} adapter entities/second')

    @retry(wait_random_min=2000, wait_random_max=7000, stop_max_delay=60 * 3 * 1000)
    def query_devices(self, adapter_id, blocking: bool=True):
        url = f'{self.req_url}/trigger/{adapter_id}'
        if not blocking:
            url = f'{url}?blocking={blocking}'
        response = requests.post(url, headers={API_KEY_HEADER: self.api_key})
        assert response.status_code == 200, \
            f"Error in response: {str(response.status_code)}, " \
            f"{str(response.content)}"
        return response

    def clean_db(self, blocking: bool):
        response = requests.post(
            self.req_url + f'/trigger/clean_db?blocking={blocking}',
            headers={API_KEY_HEADER: self.api_key}
        )

        assert response.status_code == 200, \
            f"Error in response: {str(response.status_code)}, " \
            f"{str(response.content)}"

    def is_up(self, *args, **kwargs):
        return super().is_up(*args, **kwargs) and {"Triggerable"}.issubset(self.get_supported_features())
