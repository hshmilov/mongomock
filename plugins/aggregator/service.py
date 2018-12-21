import concurrent.futures
import logging
import threading
import time
from datetime import datetime
from typing import List

import pymongo
from axonius.adapter_base import is_plugin_adapter
from axonius.consts.plugin_consts import (ADAPTERS_LIST_LENGTH,
                                          AGGREGATOR_PLUGIN_NAME, PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import EntityType, PluginBase
from axonius.utils.files import get_local_config_file
from axonius.utils.json import from_json
from axonius.utils.threading import LazyMultiLocker
from funcy import chunks
from pymongo.errors import CollectionInvalid

from aggregator.exceptions import AdapterOffline, ClientsUnavailable

logger = logging.getLogger(f'axonius.{__name__}')
"""
AggregatorPlugin.py: A Plugin for the devices aggregation process
"""

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
                        '$and': [
                            {
                                '$eq': ['$$tag.type', 'data']
                            },
                            {
                                '$ne': ['$$tag.data', False]
                            }
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


class AggregatorService(PluginBase, Triggerable):
    # This is the amount of delay we should wait before performing a full db rebuild again and again,
    # to introduce some latency over entity_db so other processes can take place
    MIN_DELAY_BETWEEN_FULL_DB_REBUILD = 10

    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        self.__db_locks = {
            entity: LazyMultiLocker()
            for entity in EntityType
        }

        self.__rebuild_db_view_lock = {
            entity: threading.RLock()
            for entity in EntityType
        }

        self.__rebuild_and_wait_db_view_lock = {
            entity: threading.RLock()
            for entity in EntityType
        }

        # the last time the DB has been rebuilt
        self.__last_full_db_rebuild = {
            entity: datetime.utcnow()
            for entity in EntityType
        }

        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=AGGREGATOR_PLUGIN_NAME, *args, **kwargs)

        try:
            # devices are inserted to this collection only via transactions on the 'clean devices'
            # it's impossible to create collections (even implicitly using insert) withing a transaction
            # https://docs.mongodb.com/manual/core/transactions/
            # > Operations that affect the database catalog, such as creating or dropping a collection or an index,
            # > are not allowed in multi-document transactions.
            # > For example, a multi-document transaction cannot include an insert operation
            # > that would result in the creation of a new collection. See Restricted Operations.
            # for this reason, we create the collection ahead of time
            self.aggregator_db_connection.create_collection('old_device_archive')
        except CollectionInvalid:
            # if the collection already exists - that's OK
            pass

    def _delayed_initialization(self):
        """
        See parent docs
        """
        super()._delayed_initialization()

        # Setting up db
        self.__insert_indexes()

        # perform an initial rebuild for consistency
        for entity_type in EntityType:
            self._rebuild_entity_view(entity_type)

    def __insert_indexes(self):
        """
        Insert useful indexes.
        :return: None
        """
        def common_view_indexes(db):
            # used for querying by it directly
            db.create_index([('internal_axon_id', pymongo.ASCENDING)], background=True)
            # used as a trick to split all devices by it relatively equally
            # this will always be a single char, 1-9a-f (hex)
            # then you can split the whole db using it to hack mongo
            # into using multiple cores when aggregating
            # https://axonius.atlassian.net/wiki/spaces/AX/pages/740229240/Implementing+and+integrating+historical+views
            db.create_index([('short_axon_id', pymongo.ASCENDING)], background=True)
            # those used for querying by it
            db.create_index([('specific_data.data.id', pymongo.ASCENDING)], background=True)
            db.create_index([(f'specific_data.{PLUGIN_NAME}', pymongo.ASCENDING)], background=True)
            db.create_index([(f'specific_data.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING)], background=True)
            db.create_index([(f'specific_data.data.adapter_properties', pymongo.ASCENDING)], background=True)
            # this is used for when you want to see a single snapshot in time
            db.create_index([(f'accurate_for_datetime', pymongo.ASCENDING)], background=True)
            # this is commonly filtered by
            db.create_index([(f'adapters', pymongo.ASCENDING)], background=True)
            # this is commonly sorted by
            db.create_index([(ADAPTERS_LIST_LENGTH, pymongo.DESCENDING)], background=True)
            # this is used all the time by the GUI
            db.create_index([(f'labels', pymongo.ASCENDING)], background=True)

        def common_db_indexes(db):
            db.create_index(
                [(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING), ('adapters.data.id', pymongo.ASCENDING)
                 ], unique=True, background=True)
            db.create_index([(f'adapters.{PLUGIN_NAME}', pymongo.ASCENDING)], background=True)
            db.create_index([('internal_axon_id', pymongo.ASCENDING)], unique=True, background=True)
            db.create_index([(ADAPTERS_LIST_LENGTH, pymongo.DESCENDING)], background=True)
            db.create_index([('adapters.client_used', pymongo.DESCENDING)], background=True)
            db.create_index([(PLUGIN_UNIQUE_NAME, pymongo.DESCENDING)], background=True)

        for entity_type in EntityType:
            common_db_indexes(self._entity_db_map[entity_type])
            common_view_indexes(self._historical_entity_views_db_map[entity_type])
            common_view_indexes(self._entity_views_db_map[entity_type])

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
        if clients and self._notify_on_adapters is True:
            self.create_notification(f"Starting to fetch device for {adapter}")
        for client_name in clients:
            try:
                data = self.request_remote_plugin(f'trigger/insert_to_db', adapter, method='POST',
                                                  json={
                                                      'client_name': client_name
                                                  })
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
        logger.debug(f"Performance: Starting partial rebuild for {len(internal_axon_ids)} devices")

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

        logger.debug("Performance: Done partial rebuild")

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

        if internal_axon_ids:
            with self.__rebuild_db_view_lock[entity_type]:
                return self.__rebuild_partial_view(from_db, to_db, internal_axon_ids)

        with self.__rebuild_and_wait_db_view_lock[entity_type]:
            # this is an expensive routine, and this may be called a lot,
            last_rebuild = self.__last_full_db_rebuild[entity_type]
            seconds_ago = (datetime.utcnow() - last_rebuild).total_seconds()
            if seconds_ago < self.MIN_DELAY_BETWEEN_FULL_DB_REBUILD:
                time.sleep(self.MIN_DELAY_BETWEEN_FULL_DB_REBUILD - seconds_ago)

            with self.__rebuild_db_view_lock[entity_type]:
                tmp_collection = self._get_db_connection()[to_db.database.name][f"temp_{to_db.name}"]
                logger.debug("Performance: starting aggregating to tmp collection")
                from_db.aggregate([
                    {
                        "$out": tmp_collection.name
                    }
                ])
                logger.debug("Performance: starting aggregating to actual collection")
                tmp_collection.aggregate([
                    *aggregation_stages_for_entity_view,
                    {
                        "$out": to_db.name
                    }
                ])
                logger.debug("Performance: starting drop temp collection")
                tmp_collection.drop()
                logger.debug("Performance: finished")

            self.__last_full_db_rebuild[entity_type] = datetime.utcnow()

    def _save_entity_views_to_historical_db(self, entity_type: EntityType, now):
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

        adapters = self.get_available_plugins_from_core_uncached()

        if job_name == 'clean_db':
            self._clean_db_devices_from_adapters(adapters.values())
            return
        elif job_name == 'fetch_filtered_adapters':
            adapters = _filter_adapters_by_parameter(post_json, adapters)
        elif job_name == 'save_history':
            now = datetime.utcnow()
            for entity_type in EntityType:
                self._save_entity_views_to_historical_db(entity_type, now)
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

        return self._fetch_data_from_adapters(adapters)

    def _request_clean_db_from_adapter(self, plugin_unique_name):
        """
        calls /clean_devices on the given adapter unique name
        :return:
        """
        response = self.request_remote_plugin(f'trigger/clean_devices', plugin_unique_name, method='POST')
        if response.status_code != 200:
            logger.warning(f"Failed cleaning db with adapter {plugin_unique_name}. " +
                           f"Reason: {str(response.content)}")

    def _clean_db_devices_from_adapters(self, current_adapters):
        """ Function for cleaning the devices db.

        This function runs on all adapters and requests them to clean the db from their devices.
        """
        try:
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

        except Exception as e:
            logger.exception(f'Getting devices from all adapters failed, adapters = {current_adapters}. {repr(e)}')

    def _fetch_data_from_adapters(self, current_adapters):
        """ Function for fetching devices from adapters.

        This function runs on all the received adapters and in a different thread fetches all of them.
        """
        try:
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

        except Exception as e:
            logger.exception(f'Getting devices from all requested adapters failed. {current_adapters}')

    def _save_data_from_adapters(self, adapter_unique_name):
        """
        Requests from the given adapter to insert its devices into the DB.
        :param str adapter_unique_name: The unique name of the adapter
        """

        start_time = time.time()
        if self._notify_on_adapters is True:
            self.create_notification(f"Starting to fetch device for {adapter_unique_name}")
        self.send_external_info_log(f"Starting to fetch device for {adapter_unique_name}")
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

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.Core

    def _notify_adapter_fetch_devices_finished(self, adapter_name, portion_of_adapters_left):
        self.request_remote_plugin('sub_phase_update', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json={
            'adapter_name': adapter_name, 'portion_of_adapters_left': portion_of_adapters_left})
