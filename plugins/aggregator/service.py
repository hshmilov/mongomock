import logging
from typing import List

from flask import request
from funcy import chunks

logger = logging.getLogger(f'axonius.{__name__}')
"""
AggregatorPlugin.py: A Plugin for the devices aggregation process
"""
from datetime import datetime, timedelta
from itertools import groupby
import concurrent.futures

import pymongo
import requests
import threading
import uuid
import time

from aggregator.exceptions import AdapterOffline, ClientsUnavailable
from axonius.adapter_base import is_plugin_adapter
from axonius.plugin_base import PluginBase, add_rule, return_error, EntityType
from axonius.utils.parsing import get_entity_id_for_plugin_name
from axonius.mixins.triggerable import Triggerable
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, AGGREGATOR_PLUGIN_NAME, SYSTEM_SCHEDULER_PLUGIN_NAME, \
    ADAPTERS_LIST_LENGTH, PLUGIN_NAME
from axonius.utils.threading import LazyMultiLocker
from axonius.utils.files import get_local_config_file
from axonius.utils.json import from_json
from axonius.devices import deep_merge_only_dict

get_devices_job_name = "Get device job"

aggregation_stages_for_entity_view = [
    {
        "$project": {
            'filtered_adapters': {
                '$filter': {
                    'input': '$adapters',
                    'as': 'adapter',
                    'cond': {
                        "$ne": [
                            "$$adapter.pending_delete", True
                        ]
                    }
                }
            },
            'internal_axon_id': 1,
            'tags': 1,
            ADAPTERS_LIST_LENGTH: 1
        },
    },
    {
        '$project': {
            'internal_axon_id': 1,
            ADAPTERS_LIST_LENGTH: 1,
            'generic_data': {
                '$filter': {
                    'input': '$tags',
                    'as': 'tag',
                    'cond': {
                        '$eq': [
                            '$$tag.type', 'data'
                        ]
                    }
                }
            },
            'specific_data': {
                '$concatArrays': [
                    '$filtered_adapters',
                    {
                        '$filter': {
                            'input': '$tags',
                            'as': 'tag',
                            'cond': {
                                '$eq': ['$$tag.type', 'adapterdata']
                            }
                        }
                    }
                ]
            },
            'adapters': '$filtered_adapters.plugin_name',
            'unique_adapter_names': '$filtered_adapters.plugin_unique_name',
            'labels': {
                '$filter': {
                    'input': '$tags',
                    'as': 'tag',
                    'cond': {
                        '$and': [
                            {
                                '$eq': ['$$tag.type', 'label']
                            },
                            {
                                '$eq': ['$$tag.data', True]
                            }
                        ]
                    }
                }
            },
        }
    },
    {
        '$project': {
            'internal_axon_id': 1,
            'generic_data': 1,
            'adapters': 1,
            'unique_adapter_names': 1,
            'labels': '$labels.name',
            'adapters_data': {
                '$map': {
                    'input': '$specific_data',
                    'as': 'data',
                    'in': {
                        '$arrayToObject': {
                            '$concatArrays': [
                                [],
                                [{
                                    'k': '$$data.plugin_name',
                                    'v': '$$data.data'
                                }
                                ]
                            ]
                        }
                    }
                }
            },
            'specific_data': 1,
            ADAPTERS_LIST_LENGTH: 1}
    },
    {
        '$match': {
            'adapters': {
                "$exists": True,
                "$not": {"$size": 0}
            }
        }
    }
]


def get_unique_name_from_plugin_unique_name_and_id(unique_plugin_name, _id):
    return f"{unique_plugin_name}{_id}"


def get_unique_name_from_device(parsed_data) -> str:
    """
    Returns a string that UUIDs a parsed adapter device
    :param parsed_data: parsed adapter device
    :return:
    """
    return get_unique_name_from_plugin_unique_name_and_id(parsed_data[PLUGIN_UNIQUE_NAME], parsed_data['data']['id'])


def _is_tag_valid(tag):
    """
    A valid tag is a tag that has a `name` and `type` and they are both string
    """
    return isinstance(tag.get('name'), str) and isinstance(tag.get('type'), str)


class AggregatorService(PluginBase, Triggerable):
    # This is the amount of delay we should wait before performing a full db rebuild again and again,
    # to introduce some latency over entity_db so other processes can take place
    MIN_DELAY_BETWEEN_FULL_DB_REBUILD = 10

    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=AGGREGATOR_PLUGIN_NAME, *args, **kwargs)

        self.__db_locks = {
            entity: LazyMultiLocker()
            for entity in EntityType
        }

        self.__rebuild_db_view_lock = {
            entity: threading.RLock()
            for entity in EntityType
        }

        # Setting up db
        self.insert_indexes()

        # insertion and link/unlink lock
        self.fetch_lock = {}

        self._activate('fetch_filtered_adapters')

        self._default_activity = True

        # the last time the DB has been rebuilt
        self.__last_full_db_rebuild = {
            entity: datetime.utcnow()
            for entity in EntityType
        }

    def insert_indexes(self):
        """
        Insert useful indexes.
        :return: None
        """

        def common_view_indexes(db):
            # used for querying by it directly
            db.create_index([('internal_axon_id', pymongo.ASCENDING)])
            # used as a trick to split all devices by it relatively equally
            # this will always be a single char, 1-9a-f (hex)
            # then you can split the whole db using it to hack mongo
            # into using multiple cores when aggregating
            # https://axonius.atlassian.net/wiki/spaces/AX/pages/740229240/Implementing+and+integrating+historical+views
            db.create_index([('short_axon_id', pymongo.ASCENDING)])
            # those used for querying by it
            db.create_index([('specific_data.data.id', pymongo.ASCENDING)])
            db.create_index([(f'specific_data.{PLUGIN_NAME}', pymongo.ASCENDING)])
            db.create_index([(f'specific_data.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING)])
            db.create_index([(f'specific_data.adapter_properties', pymongo.ASCENDING)])
            # this is used for when you want to see a single snapshot in time
            db.create_index([(f'accurate_for_datetime', pymongo.ASCENDING)])
            # this is commonly sorted by
            db.create_index([(ADAPTERS_LIST_LENGTH, pymongo.DESCENDING)])

        for entity_type in EntityType:
            common_view_indexes(self._historical_entity_views_db_map[entity_type])
            common_view_indexes(self._entity_views_db_map[entity_type])

        self.devices_db.create_index([
            (f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING), ('adapters.data.id', pymongo.ASCENDING)
        ], unique=True)
        self.devices_db.create_index([(f'adapters.{PLUGIN_NAME}', pymongo.ASCENDING)])
        self.devices_db.create_index([('internal_axon_id', pymongo.ASCENDING)], unique=True)
        self.devices_db.create_index(
            [(ADAPTERS_LIST_LENGTH, pymongo.DESCENDING), ('_id', pymongo.DESCENDING)])

        self.users_db.create_index([
            (f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING), ('adapters.data.id', pymongo.ASCENDING)
        ], unique=True)
        self.users_db.create_index([('internal_axon_id', pymongo.ASCENDING)], unique=True)

    def _request_insertion_from_adapters(self, adapter):
        """Get mapped data from all devices.

        Returned from the Adapter/Plugin.

        Mapped fields will include:
        * Device type - <string?> Computer, laptop, phone, anti-virus instance...
        * OS version - <string> The version of the runnig os
        * Adapter ID - <string> The unique ID that the adapter chose for this device. Could be different
                        For the same device retriven from different adapters
        * Client name - <string> The client used to retrieve this device. For example, in ActiveDirectoryAdapter
                        The client is the DC name that returned this device

        :param str adapter: The address of the adapter (url)
        """
        try:
            clients = self.request_remote_plugin('clients', adapter).json()
        except Exception as e:
            logger.exception(f"{repr(e)}")
            raise AdapterOffline()
        if 'status' in clients and 'message' in clients:
            logger.error(
                f'Request for clients from {adapter} failed. Status: {clients.get("status", "")}, Message \'{clients.get("message", "")}\'')
            raise ClientsUnavailable()
        for client_name in clients:
            try:
                data = self.request_remote_plugin(f'insert_to_db?client_name={client_name}', adapter, method='PUT')
            except Exception as e:
                # request failed
                logger.exception(f"{repr(e)}")
                raise AdapterOffline()
            if data.status_code != 200:
                logger.warn(f"{client_name} client for adapter {adapter} is returned HTTP {data.status_code}. "
                            f"Reason: {str(data.content)}")
                continue
            yield (client_name, from_json(data.content))

    def __rebuild_partial_view(self, from_db, to_db, internal_axon_ids: List[str]):
        """
        See docs for _rebuild_entity_view
        """
        internal_axon_ids = list(internal_axon_ids)
        logger.info(f"Performance: Starting partial rebuild for {len(internal_axon_ids)} devices")

        processed_devices = list(from_db.aggregate([
            {
                "$match": {
                    "internal_axon_id": {
                        "$in": internal_axon_ids
                    }
                }
            },
            *aggregation_stages_for_entity_view,
        ]))
        for device in processed_devices:
            to_db.replace_one(
                filter={
                    "internal_axon_id": device['internal_axon_id']
                },
                replacement=device,
                upsert=True
            )
        retrieved_devices = [x['internal_axon_id'] for x in processed_devices]
        to_be_deleted = [x for x in internal_axon_ids if x not in retrieved_devices]
        to_db.delete_many(
            filter={
                "internal_axon_id": {
                    "$in": to_be_deleted
                }
            })

        logger.info("Performance: Done partial rebuild")

    def _rebuild_entity_view(self, entity_type: EntityType, internal_axon_ids: List[str] = None):
        """
        Takes the "raw" db (i.e. devices_db), performs an aggregation over it to generate
        the "pretty" view from it (i.e. devices_db_view)
        :param entity_type: The entity type to rebuild for
        :param internal_axon_ids: if not none, will rebuild for the given internal axon ids only
        """

        # The following creates a view that has all adapters and tags
        # of type "adapterdata" inside one (unsorted!) array.
        # also hides 'pending_delete" entities
        from_db = self._entity_db_map[entity_type]
        to_db = self._entity_views_db_map[entity_type]

        with self.__rebuild_db_view_lock[entity_type]:
            if internal_axon_ids:
                return self.__rebuild_partial_view(from_db, to_db, internal_axon_ids)

            # this is an expensive routine, and this may be called a lot,
            last_rebuild = self.__last_full_db_rebuild[entity_type]
            seconds_ago = (datetime.utcnow() - last_rebuild).total_seconds()
            if seconds_ago < self.MIN_DELAY_BETWEEN_FULL_DB_REBUILD:
                time.sleep(self.MIN_DELAY_BETWEEN_FULL_DB_REBUILD - seconds_ago)

            tmp_collection = self._get_db_connection()[to_db.database.name][f"temp_{to_db.name}"]
            logger.info("Performance: starting aggregating to tmp collection")
            from_db.aggregate([
                {
                    "$out": tmp_collection.name
                }
            ])
            logger.info("Performance: starting aggregating to actual collection")
            tmp_collection.aggregate([
                *aggregation_stages_for_entity_view,
                {
                    "$out": to_db.name
                }
            ])
            logger.info("Performance: starting drop temp collection")
            tmp_collection.drop()
            logger.info("Performance: finished")
            self.__last_full_db_rebuild[entity_type] = datetime.utcnow()

    def _save_entity_views_to_historical_db(self, entity_type: EntityType):
        from_db = self._entity_views_db_map[entity_type]
        to_db = self._historical_entity_views_db_map[entity_type]

        # using a tmp collection because $out can write with a lot of constraints
        # https://docs.mongodb.com/manual/reference/operator/aggregation/out/
        # > You cannot specify a sharded collection as the output collection.
        # > The $out operator cannot write results to a capped collection. (Not using - but we might)
        # > [...] $out stage atomically replaces the existing collection with the new results collection
        # The last one means that if we use $out we replace everything in the output collection,
        # while we actually just want to add.
        # So - why are we even using $out altogether?
        # $out makes sure we get a consistent view of the DB so if something happens here it won't be affected
        # it is also an easy way for some modifications without involving python code
        # benchmark: 1-2k/sec devices (docker, mongo 3.6) - 100k devices ~ a minute

        tmp_collection = self._get_db_connection()[to_db.database.name][f"temp_{to_db.name}"]
        now = datetime.now()

        val = to_db.find_one(filter={},
                             sort=[('accurate_for_datetime', -1)],
                             projection={
                                 'accurate_for_datetime': 1
        })
        if val:
            val = val['accurate_for_datetime']
            if val.date() == now.date():
                logger.info(f"For {entity_type} not saving history: save only once a day - last saved at {val}")
                return

        from_db.aggregate([
            {
                "$project": {
                    "_id": 0
                }
            },
            {
                "$addFields": {
                    "accurate_for_datetime": {
                        "$literal": now
                    },
                    "short_axon_id": {
                        "$substrCP": [
                            "$internal_axon_id", 0, 1
                        ]
                    }
                }
            },
            {
                "$out": tmp_collection.name
            }
        ])

        for chunk in chunks(10000, tmp_collection.find({})):
            to_db.insert_many(chunk)

        tmp_collection.drop()

    def _triggered(self, job_name, post_json, *args):
        def _filter_adapters_by_parameter(adapter_filter, adapters):
            filtered_adapters = list(adapters.values())
            for current_adapter in adapters.values():
                for key, val in adapter_filter.items():
                    if current_adapter[key] != val:
                        filtered_adapters.remove(current_adapter)
            return filtered_adapters

        adapters = requests.get(self.core_address + '/register')

        if adapters.status_code != 200:
            logger.error(f"Error getting adapters from core. reason: "
                         f"{str(adapters.status_code)}, {str(adapters.content)}")
            return return_error('Could not fetch adapters', 500)

        adapters = adapters.json()

        if job_name == 'clean_db':
            return self._clean_db_devices_from_adapters(job_name, adapters.values())
        elif job_name == 'fetch_filtered_adapters':
            adapters = _filter_adapters_by_parameter(post_json, adapters)
        elif job_name == 'save_history':
            for entity_type in EntityType:
                self._save_entity_views_to_historical_db(entity_type)
            return
        elif job_name == 'rebuild_entity_view':
            for entity_type in EntityType:
                self._rebuild_entity_view(entity_type,
                                          internal_axon_ids=post_json.get('internal_axon_ids') if post_json else None)
            return
        else:
            adapters = [adapter for adapter in adapters.values()
                        if adapter[PLUGIN_UNIQUE_NAME] == job_name]

        logger.debug("Fetching from registered adapters = {}".format(adapters))

        return self._fetch_data_from_adapters(job_name, adapters)

    def _request_clean_db_from_adapter(self, plugin_unique_name):
        """
        calls /clean_devices on the given adapter unique name
        :return:
        """
        response = self.request_remote_plugin(f'clean_devices', plugin_unique_name, method='POST')
        if response.status_code != 200:
            logger.warning(f"Failed cleaning db with adapter {plugin_unique_name}. " +
                           f"Reason: {str(response.content)}")
            return None
        return from_json(response.content)

    def _clean_db_devices_from_adapters(self, job_name, current_adapters):
        """ Function for cleaning the devices db.

        This function runs on all adapters and requests them to clean the db from their devices.
        """
        try:
            with self.fetch_lock.setdefault(job_name, threading.RLock()):
                futures_for_adapter = {}

                # let's add jobs for all adapters
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    num_of_adapters_to_fetch = len(current_adapters)
                    for adapter in current_adapters:
                        if not is_plugin_adapter(adapter['plugin_type']):
                            # This is not an adapter, not running
                            num_of_adapters_to_fetch -= 1
                            continue

                        futures_for_adapter[executor.submit(
                            self._request_clean_db_from_adapter, adapter[PLUGIN_UNIQUE_NAME])] = adapter['plugin_name']

                    for future in concurrent.futures.as_completed(futures_for_adapter):
                        try:
                            num_of_adapters_to_fetch -= 1
                            future.result()
                            logger.info(f"Finished adapter number {num_of_adapters_to_fetch}")
                        except Exception as err:
                            logger.exception("An exception was raised while trying to get a result.")

                logger.info("Finished cleaning all device data.")

                return ''  # raw_detailed_devices

        except Exception as e:
            logger.exception(f'Getting devices from all requested adapters failed, {repr(e)}')

    def _fetch_data_from_adapters(self, job_name, current_adapters=None):
        """ Function for fetching devices from adapters.

        This function runs on all the received adapters and in a different thread fetches all of them.
        """
        try:
            with self.fetch_lock.setdefault(job_name, threading.RLock()):
                futures_for_adapter = {}

                # let's add jobs for all adapters
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    num_of_adapters_to_fetch = len(current_adapters)
                    for adapter in current_adapters:
                        if not is_plugin_adapter(adapter['plugin_type']):
                            # This is not an adapter, not running
                            num_of_adapters_to_fetch -= 1
                            continue

                        futures_for_adapter[executor.submit(
                            self._save_data_from_adapters, adapter[PLUGIN_UNIQUE_NAME])] = adapter['plugin_name']

                    for future in concurrent.futures.as_completed(futures_for_adapter):
                        try:
                            num_of_adapters_to_fetch -= 1
                            future.result()
                            # notify the portion of adapters left to fetch, out of total required
                            self._notify_adapter_fetch_devices_finished(
                                futures_for_adapter[future], num_of_adapters_to_fetch / len(current_adapters))
                        except Exception as err:
                            logger.exception("An exception was raised while trying to get a result.")

                logger.info("Finished getting all device data.")

                return ''  # raw_detailed_devices

        except Exception as e:
            logger.exception('Getting devices from all requested adapters failed.')

    def _do_plugin_push(self, sent_plugin, should_update_view=False):
        """
        :return: '' if on success, else error string
        """
        association_type = sent_plugin.get('association_type')
        associated_adapters = sent_plugin.get('associated_adapters')
        entity = sent_plugin.get('entity')

        if entity not in [EntityType.Devices.value, EntityType.Users.value]:
            return return_error("Acceptable values for entity are: 'devices', 'users'")

        if association_type not in ['Tag', 'Multitag', 'Link', 'Unlink']:
            return "Acceptable values for association_type are: 'Tag', 'Multitag', 'Link', 'Unlink'"
        if not isinstance(associated_adapters, list):
            return "associated_adapters must be a list"

        if association_type == 'Tag':
            # If a tag is associated with more than one adapter we will simply search for devices that have one of them.
            # But still we will be able to store these adapters in the "associated_adapters" field in the db.
            if len(associated_adapters) == 0:
                return "Tag must be associated with at least one adapter"
            if not _is_tag_valid(sent_plugin):
                return "tag name and type must be provided as a string"

        if association_type == 'Multitag':
            if not isinstance(sent_plugin.get('tags'), list):
                return "A multitag must have a list of tags in 'tags'"
            if any(not _is_tag_valid(tag) for tag in sent_plugin['tags']):
                return "All tags in 'tags' must be valid tags, such as they have 'name' and 'type' as string"

        # user doesn't send this
        sent_plugin['accurate_for_datetime'] = datetime.now()

        # we might not trust the sender on this
        sent_plugin[PLUGIN_UNIQUE_NAME], sent_plugin['plugin_name'] = self.get_caller_plugin_name()

        # Get the specific lock we want
        entity = EntityType(entity)
        db_lock = self.__db_locks[entity]
        entities_db = self._entity_db_map[entity]

        # this lock is commented out because it should actually be an A-B lock
        # and having a regular lock is causing too many performance issues
        # so we prefer having slight inconsistencies with the view instead of performance issues
        # see https://axonius.atlassian.net/browse/AX-2059
        # with self.__rebuild_db_view_lock[entity]:

        with db_lock.get_lock(
                [get_unique_name_from_plugin_unique_name_and_id(name, associated_id) for name, associated_id in
                 associated_adapters]):
            # now let's update our db

            # figure out all axonius entities that at least one of its adapters are in the
            # given plugin's association
            entities_candidates = list(entities_db.find({"$or": [
                {
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: associated_plugin_unique_name,
                            'data.id': associated_id
                        }
                    }
                }
                for associated_plugin_unique_name, associated_id in associated_adapters
            ]}))

            if len(entities_candidates) == 0:
                return f"No entities given or all entities given don't exist. " \
                       f"Associated adapters: {associated_adapters}"

            if association_type == 'Tag':
                if len(entities_candidates) != 1:
                    # it has been checked that at most 1 device was provided (if len(associated_adapters) != 1)
                    # then if it's not 1, its definitely 0
                    return "A tag must be associated with just one adapter, the entity provided is unavailable"
                # take (assumed single) key from candidates
                entities_candidate = entities_candidates[0]

                if sent_plugin.get('type') == "adapterdata":
                    relevant_adapter = [x for x in entities_candidate['adapters']
                                        if x[PLUGIN_UNIQUE_NAME] == associated_adapters[0][0]]
                    assert relevant_adapter, "Couldn't find adapter in axon device"
                    sent_plugin['associated_adapter_plugin_name'] = relevant_adapter[0][PLUGIN_NAME]

                self._update_entity_with_tag(sent_plugin, entities_candidate, entities_db)
            elif association_type == 'Multitag':
                for device in entities_candidates:
                    # here we tag all adapter_devices per axonius device candidate
                    new_sent_plugin = dict(sent_plugin)
                    del new_sent_plugin['tags']
                    new_sent_plugin['associated_adapters'] = [
                        (adapter_device[PLUGIN_UNIQUE_NAME], adapter_device['data']['id'])
                        for adapter_device in device['adapters']
                    ]

                    for tag in sent_plugin['tags']:
                        self._update_entity_with_tag({**new_sent_plugin, **tag}, device, entities_db)
            elif association_type == 'Link':
                # in this case, we need to link (i.e. "merge") all entities_candidates
                # if there's only one, then the link is either associated only to
                # one entity (which is as irrelevant as it gets)
                # or all the entities are already linked. In any case, if a real merge isn't done
                # it means someone made a mistake.
                if len(entities_candidates) < 2:
                    return f'Found less than two candidates, got {len(entities_candidates)}'

                if len(associated_adapters) != 2:
                    return f'Link with wrong number of devices {len(associated_adapters)}'

                if associated_adapters[0] == associated_adapters[1]:
                    return f'Got link of the same device {associated_adapters}'

                self._link_entities(entities_candidates, entities_db)
            elif association_type == 'Unlink':
                if len(entities_candidates) != 1:
                    return f"All associated_adapters in an unlink operation must be from the same Axonius entity, in your case, they're from {len(entities_candidates)} entities."
                entity_to_split = entities_candidates[0]

                if len(entity_to_split['adapters']) == len(associated_adapters):
                    return "You can't remove all devices from an entity, that'll be unfair."

                self._unlink_entities(associated_adapters, entity_to_split, entities_db)
            if should_update_view:
                self._rebuild_entity_view(entity, [x['internal_axon_id'] for x in entities_candidates])

        # raw == parsed for plugin_data
        self._save_parsed_in_db(sent_plugin)  # save in parsed too

        return ""

    @add_rule("plugin_push", methods=["POST"])
    def plugin_push(self):
        """
        Digests 'Link', 'Unlink' and 'Tag' requests from plugin
        Link - links two or more adapter devices/users
        Unlink - unlinks exactly two adapter devices/users
        Tag - adds a tag to an adapter devices/users
        Refer to https://axonius.atlassian.net/wiki/spaces/AX/pages/86310913/Devices+DB+Correlation+Process for more
        :return:
        """
        # if ?rebuild=True/False is passed than this request will rebuild the db
        rebuild = request.args.get('rebuild', 'True') == 'True'
        sent_plugin = self.get_request_data_as_object()
        if sent_plugin is None:
            return return_error("Invalid data sent", 400)
        res = self._do_plugin_push(sent_plugin, should_update_view=rebuild)
        if res != '':
            logger.warning(f'plugin push failed {res}')
            return return_error(res)

        return ''

    @add_rule("multi_plugin_push", methods=["POST"])
    def multi_plugin_push(self):
        # if ?rebuild=True/False is passed than this request will rebuild the db
        rebuild = request.args.get('rebuild', 'True') == 'True'
        sent_plugin = self.get_request_data_as_object()
        should_rebuild_all = len(sent_plugin) > 50
        logger.info(f"Handling {len(sent_plugin)} pushes with rebuild = {rebuild}")
        results = [self._do_plugin_push(d, should_update_view=rebuild and not should_rebuild_all) for d in sent_plugin]
        if should_rebuild_all and rebuild:
            for entity_type in EntityType:
                self._rebuild_entity_view(entity_type)
        if any(x != "" for x in results):
            logger.info(f"Error handling {len(sent_plugin)} pushes {[x for x in results if x != '']}")
            return return_error("Errors took place", additional_data=[x for x in results if x != ''])

        logger.info(f"Finished handling {len(sent_plugin)} pushes")
        return ""

    def _unlink_entities(self, associated_adapters, axonius_entity_to_split, entities_db):
        """
        Unlinks the associated_adapters from axonius_entity_to_split
        :param associated_adapters: List of tuples, where each tuple is of form [unique_plugin_name, id]
        :param axonius_entity_to_split: An axnoius entity, with all tags and adapters
        :param entities_db: the relevant collection - i.e. devices_db or users_db
        """
        # we already tested that all adapters in data_sent are indeed from the single
        # entity we found, so the ids will match, so we don't have to check that.
        # We're building a new entity that has all the associated_adapters given from
        # the old axonius entity, and at the same time deleting from the old entity.
        internal_axon_id = uuid.uuid4().hex
        new_axonius_entity = {
            "internal_axon_id": internal_axon_id,
            "accurate_for_datetime": datetime.now(),
            "adapters": [],
            "tags": []
        }
        remaining_adapters = []

        # figure out which adapters should stay on the current entity (axonius_entity_to_split - remaining adapters)
        # and those that should move to the new axonius entity
        for adapter_entity in axonius_entity_to_split['adapters']:
            candidate = get_entity_id_for_plugin_name(associated_adapters,
                                                      adapter_entity[PLUGIN_UNIQUE_NAME])
            if candidate is not None and candidate == adapter_entity['data']['id']:
                new_axonius_entity['adapters'].append(adapter_entity)
            else:
                remaining_adapters.append(adapter_entity[PLUGIN_NAME])

        # figure out for each tag G (in the current entity, i.e. axonius_entity_to_split)
        # whether any of G.associated_adapters is in the `associated_adapters`, i.e.
        # whether G should be a part of the new axonius entity.
        # clarification: G should be a part of the new axonius entity if any of G.associated_adapters
        # >>>>>>>>>>>>>> is also part of the new axonius entity
        for tag in axonius_entity_to_split['tags']:
            for tag_plugin_unique_name, tag_adapter_id in tag['associated_adapters']:
                candidate = get_entity_id_for_plugin_name(associated_adapters, tag_plugin_unique_name)
                if candidate is not None and candidate == tag_adapter_id:
                    newtag = dict(tag)
                    # if the tags moves/copied to the new entity, it should 'forget' it's old
                    # associated adapters, because most of the them stay in the old device,
                    # and so the new G.associated_adapters are the associated_adapters
                    # that are also part of the new axonius entity
                    newtag['associated_adapters'] = list(x
                                                         for x
                                                         in associated_adapters
                                                         if x in newtag['associated_adapters'])
                    new_axonius_entity['tags'].append(newtag)

        # remove the adapters one by one from the DB, and also keep track in memory
        adapter_entities_left = list(axonius_entity_to_split['adapters'])
        for adapter_to_remove_from_old in new_axonius_entity['adapters']:
            entities_db.update_many({'internal_axon_id': axonius_entity_to_split['internal_axon_id']},
                                    {
                                        "$pull": {
                                            'adapters': {
                                                PLUGIN_UNIQUE_NAME: adapter_to_remove_from_old[
                                                    PLUGIN_UNIQUE_NAME],
                                                'data.id': adapter_to_remove_from_old['data']['id']
                                            }
                                        }
            })
            adapter_entities_left.remove(adapter_to_remove_from_old)

        # generate a list of (unique_plugin_name, id) from the adapter entities left
        adapter_entities_left_by_id = [
            [adapter[PLUGIN_UNIQUE_NAME], adapter['data']['id']]
            for adapter
            in adapter_entities_left
        ]

        # the old entity might and might not keep the tag:
        # if the tag contains an associated_adapter that is also part of the old entity
        # - then this tag is also associated with the old entity
        # if it does not
        # - this this tag is removed from the old entity

        # so now we generate a list of all tags that must be removed from the old entity
        # a tag will be removed if all of its associated_adapters are not in any of the
        # adapter entities left in the old device, i.e. all of its associated_adapters have moved
        pull_those = [tag_from_old
                      for tag_from_old
                      in axonius_entity_to_split['tags']
                      if all(assoc_adapter not in adapter_entities_left_by_id
                             for assoc_adapter
                             in tag_from_old['associated_adapters'])]

        set_query = {
            ADAPTERS_LIST_LENGTH: len(set(remaining_adapters))
        }
        if pull_those:
            pull_query = {
                'tags': {
                    "$or": [
                        {
                            PLUGIN_UNIQUE_NAME: pull_this_tag[PLUGIN_UNIQUE_NAME],
                            "name": pull_this_tag['name']
                        }
                        for pull_this_tag
                        in pull_those
                    ]

                }
            }
            full_query = {
                "$pull": pull_query,
                "$set": set_query
            }
        else:
            full_query = {
                "$set": set_query
            }
        entities_db.update_many({'internal_axon_id': axonius_entity_to_split['internal_axon_id']},
                                full_query)
        new_axonius_entity[ADAPTERS_LIST_LENGTH] = len(set([x[PLUGIN_NAME] for x in new_axonius_entity['adapters']]))
        entities_db.insert_one(new_axonius_entity)

    def _link_entities(self, entities_candidates, entities_db):
        """
        Link all given axonius entities, assuming 2 are given
        """
        collected_adapter_entities = [axonius_entity['adapters'] for axonius_entity in entities_candidates]
        all_unique_adapter_entities_data = [v for d in collected_adapter_entities for v in d]

        # Get all tags from all devices. If we have the same tag name and issuer, prefer the newest.
        # a tag is the same tag, if it has the same plugin_unique_name and name.
        def keyfunc(tag):
            return tag['plugin_unique_name'], tag['name']

        # first, lets get all tags and have them sorted. This will make the same tags be consecutive.
        all_tags = sorted((t for dc in entities_candidates for t in dc['tags']), key=keyfunc)
        # now we have the same tags ordered consecutively. so we want to group them, so that we
        # would have duplicates of the same tag in their identity key.
        all_tags = groupby(all_tags, keyfunc)
        # now we have them groupedby, lets select only the one which is the newest.
        tags_for_new_device = {tag_key: max(duplicated_tags, key=lambda tag: tag['accurate_for_datetime'])
                               for tag_key, duplicated_tags
                               in all_tags}
        internal_axon_id = uuid.uuid4().hex

        # now, let us delete all other AxoniusDevices
        entities_db.delete_many({'$or':
                                 [
                                     {'internal_axon_id': axonius_entity['internal_axon_id']}
                                     for axonius_entity in entities_candidates
                                 ]
                                 })
        entities_db.insert_one({
            "internal_axon_id": internal_axon_id,
            "accurate_for_datetime": datetime.now(),
            "adapters": all_unique_adapter_entities_data,
            ADAPTERS_LIST_LENGTH: len(set([x[PLUGIN_NAME] for x in all_unique_adapter_entities_data])),
            "tags": list(tags_for_new_device.values())  # Turn it to a list
        })

    def _save_data_from_adapters(self, adapter_unique_name):
        """
        Requests from the given adapter to insert its devices into the DB.
        :param str adapter_unique_name: The unique name of the adapter
        """

        start_time = time.time()
        logger.info(f"Starting to fetch device for {adapter_unique_name}")
        try:
            data = self._request_insertion_from_adapters(adapter_unique_name)
            for client_name, devices_per_client in data:
                logger.info(f"Got {devices_per_client} for client {client_name} in {adapter_unique_name}")

        except (AdapterOffline, ClientsUnavailable) as e:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            logger.warn(f"adapter {adapter_unique_name} might be offline. Reason {str(e)}")
        except Exception as e:
            logger.exception("Thread {0} encountered error: {1}".format(threading.current_thread(), str(e)))
            raise

        logger.info(f"Finished for {adapter_unique_name} took {time.time() - start_time} seconds")

    def _update_entity_with_tag(self, tag, axonius_entity, entities_db):
        """
        Updates the db to either add or update the given tag
        :param tag: tag from user
        :param axonius_entity: axonius entity from db
        :param entities_db: the db instance - devices db, users db, etc.
        :return: None
        """

        if any((x['name'] == tag['name'] and x['plugin_unique_name'] == tag['plugin_unique_name'] and x['type'] == tag[
                'type'])
                for x in axonius_entity['tags']):

            # We found the tag. If action_if_exists is replace just replace it. but if its update, lets
            # make a deep merge here. Note that the access to the db should be locked (happens in the calling function)
            if tag['action_if_exists'] == "update" and tag["type"] == "adapterdata":
                # Take the old value of this tag.
                final_data = [
                    x["data"] for x in axonius_entity["tags"] if x["plugin_unique_name"] == tag["plugin_unique_name"]
                    and x["type"] == "adapterdata"
                    and x["name"] == tag["name"]
                ]

                if len(final_data) != 1:
                    msg = f"Got tag {tag['plugin_unique_name']}/{tag['name']}/{tag['type']} with " \
                          f"action_if_exists=update, but final_data is not of length 1: {final_data}"
                    logger.error(msg)
                    raise ValueError(msg)

                final_data = final_data[0]

                # Merge. Note that we deep merge dicts but not lists, since lists are like fields
                # for us (for example ip). Usually when we get some list variable we get all of it so we don't need
                # any update things
                tag["data"] = deep_merge_only_dict(tag["data"], final_data)
                logger.debug("action if exists on tag!")

            result = entities_db.update_one({
                "internal_axon_id": axonius_entity['internal_axon_id'],
                "tags": {
                    "$elemMatch":
                        {
                            "name": tag['name'],
                            "plugin_unique_name": tag['plugin_unique_name'],
                            "type": tag['type']
                        }
                }
            }, {
                "$set": {
                    "tags.$": tag
                }
            })

            if result.modified_count != 1:
                msg = f"tried to update tag {tag}. expected modified_count == 1 but got {result.modified_count}"
                logger.error(msg)
                raise ValueError(msg)
        elif tag.get("plugin_name") == "gui" and tag['type'] == 'label' and tag['data'] is False:
            # Gui is a special plugin. It can delete any label it wants (even if it has come from
            # another service)

            result = entities_db.update_one({
                "internal_axon_id": axonius_entity['internal_axon_id'],
                "tags": {
                    "$elemMatch":
                        {
                            "name": tag['name'],
                            "type": "label"
                        }
                }
            }, {
                "$set": {
                    "tags.$.data": False
                }
            })

            if result.modified_count != 1:
                msg = f"tried to update label {tag}. expected modified_count == 1 but got {result.modified_count}"
                logger.error(msg)
                raise ValueError(msg)

        else:
            result = entities_db.update_one(
                {"internal_axon_id": axonius_entity['internal_axon_id']},
                {
                    "$addToSet": {
                        "tags": tag
                    }
                })

            if result.modified_count != 1:
                msg = f"tried to add tag {tag}. expected modified_count == 1 but got {result.modified_count}"
                logger.error(msg)
                raise ValueError(msg)

    @property
    def plugin_subtype(self):
        return "Core"

    def _notify_adapter_fetch_devices_finished(self, adapter_name, portion_of_adapters_left):
        self.request_remote_plugin('sub_phase_update', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json={
            'adapter_name': adapter_name, 'portion_of_adapters_left': portion_of_adapters_left})
