import datetime
from multiprocessing.pool import ThreadPool
from threading import Lock

import pymongo
import shutil
import traceback
from collections import defaultdict
from typing import List, Tuple

from bson import Code
from pymongo.errors import OperationFailure
from retrying import retry

from axonius.devices.device_adapter import LAST_SEEN_FIELD
from axonius.entities import EntityType
from axonius.utils.mongo_administration import get_collection_storage_size, create_capped_collection
from services.updatable_service import UpdatablePluginMixin
from services.plugin_service import API_KEY_HEADER, PluginService
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME, PLUGIN_NAME, PLUGIN_UNIQUE_NAME, ADAPTERS_LIST_LENGTH
from axonius.consts.gui_consts import USERS_COLLECTION
import requests


class AggregatorService(PluginService, UpdatablePluginMixin):
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
            self._update_schema_version_17()  # self._update_schema_version_16() disabled due to a very long migration

        if self.db_schema_version != 17:
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
        # https://axonius.atlassian.net/browse/AX-5401
        print('Update to schema 17 - add first fetch time')
        try:
            self._fix_db_for_entity(EntityType.Devices)
            self._fix_db_for_entity(EntityType.Users)
            self.db_schema_version = 17
        except Exception as e:
            print(f'Exception while upgrading core db to version 16. Details: {e}')
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
                col.update_one({
                    '_id': entity['_id'],
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: adapter[PLUGIN_UNIQUE_NAME],
                            'data.id': adapter['data']['id']
                        }
                    }
                }, {
                    '$set': {
                        'adapters.$.data.first_fetch_time': adapter['data']['fetch_time']
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
    def query_devices(self, adapter_id):
        response = requests.post(self.req_url + f"/trigger/{adapter_id}", headers={API_KEY_HEADER: self.api_key})

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
