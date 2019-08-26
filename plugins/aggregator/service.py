import concurrent.futures
import logging
import threading
import time
from datetime import datetime

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


class AggregatorService(Triggerable, PluginBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        self.__db_locks = {
            entity: LazyMultiLocker()
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

    def __insert_indexes(self):
        """
        Insert useful indexes.
        :return: None
        """

        def non_historic_indexes(db):
            db.create_index(
                [(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING), ('adapters.data.id', pymongo.ASCENDING)
                 ], unique=True, background=True)
            db.create_index([('internal_axon_id', pymongo.ASCENDING)], unique=True, background=True)

        def historic_indexes(db):
            db.create_index(
                [(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING), ('adapters.data.id', pymongo.ASCENDING)
                 ], background=True)
            db.create_index([('internal_axon_id', pymongo.ASCENDING)], background=True)
            db.create_index([('short_axon_id', pymongo.ASCENDING)], background=True)
            db.create_index([('accurate_for_datetime', pymongo.ASCENDING)], background=True)

        def common_db_indexes(db):
            db.create_index([(f'adapters.{PLUGIN_NAME}', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING)], background=True)
            db.create_index([(ADAPTERS_LIST_LENGTH, pymongo.DESCENDING)], background=True)
            db.create_index([('adapters.client_used', pymongo.DESCENDING)], background=True)

            # this is commonly filtered by the GUI
            db.create_index([('adapters.data.id', pymongo.ASCENDING)], background=True)
            db.create_index([('adapters.pending_delete', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.adapter_properties', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.os.type', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.os.distribution', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.last_seen', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.hostname', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.name', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.network_interfaces.mac', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.network_interfaces.ips', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.last_used_users', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.username', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.installed_software.name', pymongo.ASCENDING)], background=True)
            db.create_index([(f'adapters.data.fetch_time', pymongo.ASCENDING)], background=True)

            db.create_index([('tags.data.id', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.{PLUGIN_NAME}', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.type', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.adapter_properties', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.os.type', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.os.distribution', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.last_seen', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.hostname', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.name', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.network_interfaces.mac', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.network_interfaces.ips', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.last_used_users', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.username', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.data.fetch_time', pymongo.ASCENDING)], background=True)

            # For labels
            db.create_index([(f'tags.name', pymongo.ASCENDING)], background=True)
            db.create_index([(f'tags.label_value', pymongo.ASCENDING)], background=True)

            # this is commonly sorted by
            db.create_index([('adapter_list_length', pymongo.DESCENDING)], background=True)

        for entity_type in EntityType:
            common_db_indexes(self._entity_db_map[entity_type])
            non_historic_indexes(self._entity_db_map[entity_type])

            common_db_indexes(self._historical_entity_views_db_map[entity_type])
            historic_indexes(self._historical_entity_views_db_map[entity_type])

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
        clients = [x['client_id']
                   for x
                   in self._get_db_connection()[adapter]['clients'].find(projection={
                       'client_id': True,
                       '_id': False
                   })]
        if clients and self._notify_on_adapters is True:
            self.create_notification(f"Starting to fetch device for {adapter}")
        check_fetch_time = True
        for client_name in clients:
            try:
                data = self._trigger_remote_plugin(adapter, 'insert_to_db', data={
                    'client_name': client_name,
                    'check_fetch_time': check_fetch_time
                })
                check_fetch_time = False
            except Exception as e:
                # request failed
                logger.exception(f"{repr(e)}")
                raise AdapterOffline()
            if data.status_code != 200:
                logger.warn(f"{client_name} client for adapter {adapter} is returned HTTP {data.status_code}. "
                            f"Reason: {str(data.content)}")
                continue
            yield (client_name, from_json(data.content))

    def _save_entity_views_to_historical_db(self, entity_type: EntityType, now):
        from_db = self._entity_db_map[entity_type]
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
        if job_name == 'clean_db':
            self._clean_db_devices_from_adapters(self.get_available_plugins_from_core_uncached().values())
            return
        elif job_name == 'fetch_filtered_adapters':
            adapters = self.get_available_plugins_from_core_uncached(post_json).values()
        elif job_name == 'save_history':
            now = datetime.utcnow()
            for entity_type in EntityType:
                self._save_entity_views_to_historical_db(entity_type, now)
            return
        else:
            adapters = self.get_available_plugins_from_core_uncached({
                PLUGIN_UNIQUE_NAME: job_name
            }).values()

        logger.debug("Fetching from registered adapters = {}".format(adapters))

        return self._fetch_data_from_adapters(adapters)

    def _request_clean_db_from_adapter(self, plugin_unique_name):
        """
        calls /clean_devices on the given adapter unique name
        :return:
        """
        if self.devices_db.count_documents({
            f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
        }, limit=1) or self.users_db.count_documents({
            f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name
        }, limit=1):
            response = self._trigger_remote_plugin(plugin_unique_name, 'clean_devices')

            if response.status_code != 200:
                logger.error(f"Failed cleaning db with adapter {plugin_unique_name}. " +
                             f"Reason: {str(response.content)}")

    def _clean_db_devices_from_adapters(self, current_adapters):
        """ Function for cleaning the devices db.

        This function runs on all adapters and requests them to clean the db from their devices.
        """
        try:
            futures_for_adapter = {}

            # let's add jobs for all adapters
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._aggregation_max_workers) as executor:
                num_of_adapters_to_fetch = len(current_adapters)
                for adapter in current_adapters:
                    if not adapter.get('plugin_type') or not is_plugin_adapter(adapter['plugin_type']):
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
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._aggregation_max_workers) as executor:
                num_of_adapters_to_fetch = len(current_adapters)
                for adapter in current_adapters:
                    if not adapter.get('plugin_type') or not is_plugin_adapter(adapter['plugin_type']):
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
