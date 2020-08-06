import concurrent.futures
import logging
import threading
import time
from datetime import datetime, timedelta
from enum import Enum, auto
from threading import Thread
from typing import List

import pymongo
from pymongo.errors import CollectionInvalid, BulkWriteError

from aggregator.exceptions import AdapterOffline, ClientsUnavailable
from aggregator.historical import create_retrospective_historic_collections, MIN_DISK_SIZE
from axonius.db_migrations import db_migration
from axonius.utils.mongo_indices import common_db_indexes, non_historic_indexes
from axonius.adapter_base import is_plugin_adapter
from axonius.consts.adapter_consts import SHOULD_NOT_REFRESH_CLIENTS
from axonius.consts.gui_consts import ParallelSearch
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME,
                                          PARALLEL_ADAPTERS,
                                          PLUGIN_NAME,
                                          ADAPTERS_LIST_LENGTH,
                                          ACTIVE_DIRECTORY_PLUGIN_NAME)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import EntityType, PluginBase
from axonius.utils.files import get_local_config_file
from axonius.utils.host_utils import get_free_disk_space
from axonius.utils.json import from_json
from axonius.utils.threading import LazyMultiLocker

logger = logging.getLogger(f'axonius.{__name__}')
'''
AggregatorPlugin.py: A Plugin for the devices aggregation process
'''

RESET_BEFORE_CLIENT_FETCH_ADAPTERS = ['cisco_adapter']


class AdapterStatuses(Enum):
    Pending = auto()
    Fetching = auto()
    Done = auto()


class AggregatorService(Triggerable, PluginBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        self.__db_locks = {
            entity: LazyMultiLocker()
            for entity in EntityType
        }
        self.__last_date = datetime.min
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=AGGREGATOR_PLUGIN_NAME, *args, **kwargs)
        self.local_db_schema_version = self.aggregator_db_connection['version']

    def _migrate_async_db(self):
        if self.db_async_schema_version < 1:
            self._update_async_schema_version_1()
        if self.db_async_schema_version < 2:
            self._update_async_schema_version_2()

        if self.db_async_schema_version != 2:
            logger.error(f'Upgrade failed, db_async_schema_version is {self.db_async_schema_version}')

    def _delayed_initialization(self):
        """
        See parent docs
        """
        super()._delayed_initialization()

        # Setting up db
        self.__insert_indexes()
        # Setting up historical
        logger.info(f'Creating historic collections')
        create_retrospective_historic_collections(self.aggregator_db_connection, self._historical_entity_views_db_map)

        try:
            self.run_all_migrations()
        except Exception:
            logger.exception('There was an error while migrating data asynchronicity')

        # Clean all raw data from the db and move it to the relevant db, only if they exist
        for entity_type in EntityType:
            count_of_entities = 0

            main_col = self._entity_db_map[entity_type]
            raw_col = self._raw_adapter_entity_db_map[entity_type]
            for entity in main_col.find({
                # pylint: disable=C0330
                'adapters.data.raw': {
                    '$exists': True,
                    '$nin': ['', None, {}, []]
                }
            }, projection={
                'adapters.data.raw': True,
                f'adapters.{PLUGIN_UNIQUE_NAME}': True,
                'adapters.data.id': True,
                '_id': True
            }):
                count_of_entities += 1
                for adapter_entity in entity['adapters']:
                    raw_col.update_one(
                        {
                            PLUGIN_UNIQUE_NAME: adapter_entity[PLUGIN_UNIQUE_NAME],
                            'id': adapter_entity['data']['id'],
                        },
                        {
                            '$set': {
                                'raw_data': adapter_entity['data'].get('raw')
                            }
                        },
                        upsert=True
                    )
                main_col.update_one({
                    '_id': entity['_id']
                }, {
                    '$set': {
                        'adapters.$[].data.raw': None
                    }
                })
            logger.info(f'Cleaned {count_of_entities} for {entity_type}')

    def __insert_indexes(self):
        """
        Insert useful indexes.
        :return: None

        jeo: 3.3 moved logic to _insert_indexes_entity so public API destroy endpoints can use
        """
        for entity_type in EntityType:
            self._insert_indexes_entity(entity_type=entity_type)

    def _request_insertion_from_adapters_async(self, adapters):
        """
        Handles all the requests to different adapters to fetch the clients data
        :param adapters: list of adapter clients
        :return: yields client of each adapter and its final data count
        """
        clients = {adapter_clients: [db_results['client_id'] for adapter_clients in adapters for
                                     db_results in
                                     self._get_db_connection()[adapter_clients]['clients'].find(projection={
                                         'client_id': True,
                                         '_id': False
                                     })] for adapter_clients in adapters}
        if clients and self._notify_on_adapters is True:
            self.create_notification(
                f'Starting to fetch device for {"".join(adapters)}')
        check_fetch_time = True
        for adapter_clients in adapters:
            data = self._trigger_remote_plugin(adapter_clients, 'insert_to_db', data={
                'client_name': clients[adapter_clients],
                'check_fetch_time': check_fetch_time
            })
            try:
                if data.content and from_json(data.content).get('min_time_check') is True:
                    logger.info(f'got min_time_check in adapter {adapter_clients}: '
                                f'The minimum time between fetches hasn\'t been reached yet.')
                    break
            except Exception:
                logger.exception(f'Error parsing json data, content is: {data.content}')
            check_fetch_time = False
            yield adapter_clients, from_json(data.content)

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
        data = None
        clients = [x['client_id']
                   for x
                   in self._get_db_connection()[adapter]['clients'].find(projection={
                       'client_id': True,
                       '_id': False
                   })]
        if clients and self._notify_on_adapters is True:
            self.create_notification(f'Starting to fetch device for {adapter}')
        check_fetch_time = True
        for client_name in clients:
            try:
                try:
                    if any(x in adapter for x in RESET_BEFORE_CLIENT_FETCH_ADAPTERS):
                        logger.info(f'Requesting adapter reload before fetch: {adapter}')
                        # Make this adapter not re-evaluate the clients on the next run.
                        adapter_plugin_name = '_'.join(adapter.split('_')[:-1])  # strip the number

                        if adapter_plugin_name:
                            adapter_plugin_settings = self.plugins.get_plugin_settings(adapter_plugin_name)
                            adapter_plugin_settings.plugin_settings_keyval[SHOULD_NOT_REFRESH_CLIENTS] = True

                            self._request_reload_uwsgi(adapter)
                except Exception:
                    logger.exception(f'Could not request uwsgi reload for {adapter!r}')

                data = self._trigger_remote_plugin(adapter, 'insert_to_db', data={
                    'client_name': client_name,
                    'check_fetch_time': check_fetch_time
                })
                try:
                    if data and data.content and from_json(data.content).get('min_time_check') is True:
                        logger.info(f'got min_time_check in adapter {adapter}: '
                                    f'The minimum time between fetches hasn\'t been reached yet.')
                        break
                except Exception:
                    logger.exception(f'Error parsing json data, content is: {data.content}')
                check_fetch_time = False
            except Exception as e:
                # request failed
                logger.exception(f'Exception while querying adapter {adapter} with client {client_name}: {repr(e)}')
            try:
                if data:
                    if data.status_code != 200 or not data.content:
                        logger.warning(
                            f'{client_name} client for adapter {adapter} is returned HTTP {data.status_code}.'
                            f' Reason: {str(data.content)}')
                        continue
                yield client_name, from_json(data.content)
            except Exception:
                try:
                    data_status_code = data.status_code
                except Exception:
                    data_status_code = 'unknown'
                logger.warning(
                    f'{client_name} client for adapter {adapter} is returned HTTP {data_status_code}.'
                    f' From unknown reason')
                continue

    def _create_daily_historic_collection(self, entity_type, col, date):
        if get_free_disk_space() < MIN_DISK_SIZE:
            logger.warning(f'No more space left for historical collections')
            return
        new_col_name = f'historical_{entity_type.value.lower()}_{date.strftime("%Y_%m_%d")}'
        try:
            new_col = self.aggregator_db_connection.create_collection(new_col_name)
        except CollectionInvalid:
            logger.error(f'Collection {new_col_name} already exists')
            return
        except Exception:
            logger.exception(f'Exception while creating collection {new_col_name}')
            return
        logger.info(f'Created new collection {new_col_name}')
        try:
            col.aggregate([
                {'$project': {'_id': 0}},
                {
                    "$addFields": {
                        "accurate_for_datetime": {
                            "$literal": date
                        }
                    }
                },
                {'$out': new_col_name},
            ])
            logger.info(f'Finished transfer for collection {new_col_name}')
            common_db_indexes(new_col)
            non_historic_indexes(new_col)
            logger.info(f'Finished index for collection {new_col_name}')
        except Exception as err:
            logger.error(f'Failed to create daily historic collections. Reason: {err}')
            self.aggregator_db_connection.drop_collection(new_col_name)

    def _drop_old_historic_collections(self, entity_type):
        for col_name in self.aggregator_db_connection.list_collection_names():
            if not col_name.startswith(f'historical_{entity_type.value.lower()}') or col_name.endswith('view'):
                continue
            # extract current date
            try:
                current_date = datetime.strptime(col_name.lstrip(f'historical_{entity_type.value.lower()}_'),
                                                 '%Y_%m_%d')
            except ValueError:
                logger.error(f'Failed to get date on collection {col_name}.')
                continue
            if (datetime.now() - current_date).days > 30:
                logger.info(f'dropping collection {col_name}')
                try:
                    self.aggregator_db_connection.drop_collection(col_name)
                except Exception as err:
                    logger.error(f'Failed to drop collection {col_name}. Reason: {err}')

    def _drop_old_historic_data_from_big_table(self, entity_type: EntityType, max_days: int):
        history_db = self._historical_entity_views_db_map[entity_type]
        history_raw_db = self._raw_adapter_historical_entity_db_map[entity_type]

        relative_delete_date = datetime.utcnow() - timedelta(days=max_days)
        query = {'accurate_for_datetime': {'$lt': relative_delete_date}}

        logger.info(f'Deleting history for {max_days} days - anything before {relative_delete_date}')
        history_db.delete_many(query)
        history_raw_db.delete_many(query)

    def _save_entity_views_to_historical_db(self, entity_type: EntityType, now, settings: dict):
        from_db = self._entity_db_map[entity_type]
        raw_from_db = self._raw_adapter_entity_db_map[entity_type]

        to_db = self._historical_entity_views_db_map[entity_type]
        raw_to_db = self._raw_adapter_historical_entity_db_map[entity_type]

        val = to_db.find_one(filter={},
                             sort=[('accurate_for_datetime', -1)],
                             projection={'accurate_for_datetime': 1})
        if val:
            val = val['accurate_for_datetime']
            if val.date() == now.date():
                logger.info(f'For {entity_type} not saving history: save only once a day - last saved at {val}')
                return 'skipping saved history'

        self._drop_old_historic_collections(entity_type)
        threads = [
            Thread(target=self.call_safe_collection_transfer,
                   args=(from_db.aggregate, [{
                       "$project": {
                           "_id": 0
                       }},
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
                           "$merge": to_db.name
                   }
                   ],)),
            Thread(target=self.call_safe_collection_transfer,
                   args=(raw_from_db.aggregate, [
                       {
                           "$project": {
                               "_id": 0
                           }
                       },
                       {
                           "$addFields": {
                               "accurate_for_datetime": {
                                   "$literal": now
                               }
                           }
                       },
                       {
                           "$merge": raw_to_db.name
                       }
                   ],)),
            Thread(target=self._create_daily_historic_collection,
                   args=(entity_type, from_db, now)
                   )
        ]
        [t.start() for t in threads]
        [t.join() for t in threads]
        try:
            if settings.get('max_days_to_save') and settings.get('max_days_to_save') > 0:
                self._drop_old_historic_data_from_big_table(entity_type, settings['max_days_to_save'])
        except Exception:
            logger.critical(f'Could not delete historical data from big history collection!')
        return 'saved history'

    @staticmethod
    def call_safe_collection_transfer(aggregate_func, *args):
        try:
            aggregate_func(*args)
        except Exception:
            logger.critical(f'history transfer func {aggregate_func} failed', exc_info=True)

    def get_adapters_data(self, post_json: dict) -> List[dict]:
        """
        Get adapters data from list of plugin unique names or mongo filters
        :param post_json: trigger post json data
        :return: adapters data
        """
        if post_json and post_json.get('adapters'):
            adapters_list = post_json.pop('adapters', [])
            adapters_filter = {
                PLUGIN_UNIQUE_NAME: {
                    '$in': adapters_list
                }
            }
            adapters = self.get_available_plugins_from_core_uncached(adapters_filter).values()
        else:
            adapters = self.get_available_plugins_from_core_uncached(post_json).values()
            adapters = list(self.filter_out_custom_discovery_adapters(adapters))
        return adapters

    # pylint: disable=inconsistent-return-statements
    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name == 'clean_db':
            adapters = self.get_adapters_data(post_json)
            self._clean_db_devices_from_adapters(adapters)
            return
        if job_name == 'fetch_filtered_adapters':
            adapters = self.get_adapters_data(post_json)
        elif job_name == 'save_history':
            now = datetime.utcnow()
            return {
                entity_type.name: self._save_entity_views_to_historical_db(entity_type, now, post_json)
                for entity_type
                in EntityType
            }
        else:
            adapters = self.get_available_plugins_from_core_uncached({
                PLUGIN_UNIQUE_NAME: job_name
            }).values()

        logger.debug(f'Fetching from registered adapters = {adapters}')

        return self._fetch_data_from_adapters(adapters, run_identifier)

    def _request_clean_db_from_adapter(self, plugin_unique_name):
        '''
        calls /clean_devices on the given adapter unique name
        :return:
        '''
        if self.devices_db.count_documents({f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name}, limit=1) or \
                self.users_db.count_documents({f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name}, limit=1):
            response = self._trigger_remote_plugin(plugin_unique_name, 'clean_devices')

            if response.status_code != 200:
                logger.error(f'Failed cleaning db with adapter {plugin_unique_name}. ' +
                             f'Reason: {str(response.content)}')

    def _clean_db_devices_from_adapters(self, current_adapters):
        ''' Function for cleaning the devices db.

        This function runs on all adapters and requests them to clean the db from their devices.
        '''
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
                        logger.info(f'Finished adapter number {num_of_adapters_to_fetch}')
                    except Exception as err:
                        logger.exception('An exception was raised while trying to get a result.')

            logger.info('Finished cleaning all device data.')

        except Exception as e:
            logger.exception(f'Getting devices from all adapters failed, adapters = {current_adapters}. {repr(e)}')

    def _fetch_data_from_adapters(self, current_adapters, run_identifier: RunIdentifier):
        """ Function for fetching devices from adapters.

        This function runs on all the received adapters and in a different thread fetches all of them.
        """
        known_adapters_status = {}
        for adapter in current_adapters:
            known_adapters_status[adapter[PLUGIN_UNIQUE_NAME]] = AdapterStatuses.Pending.name
        run_identifier.update_status(known_adapters_status)

        try:
            futures_for_adapter = {}
            parallel_fetch = self.feature_flags_config().get(ParallelSearch.root_key, {}).get(ParallelSearch.enabled,
                                                                                              False)
            logger.info(f'Parallel fetch status: {parallel_fetch}')
            async_adapters = {x: [] for x in PARALLEL_ADAPTERS}

            # let's add jobs for all adapters
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._aggregation_max_workers) as executor:
                num_of_adapters_to_fetch = len(current_adapters)
                for adapter in current_adapters:
                    if not adapter.get('plugin_type') or not is_plugin_adapter(adapter['plugin_type']):
                        # This is not an adapter, not running
                        num_of_adapters_to_fetch -= 1
                        continue

                    elif parallel_fetch and adapter.get('plugin_name') in PARALLEL_ADAPTERS:
                        async_adapters[adapter.get('plugin_name')].append(adapter[PLUGIN_UNIQUE_NAME])
                        continue

                    futures_for_adapter[executor.submit(
                        self._save_data_from_adapters, adapter[PLUGIN_UNIQUE_NAME],
                        run_identifier, known_adapters_status)] = adapter

                if parallel_fetch:
                    for async_adapter_clients in async_adapters.values():
                        if not async_adapter_clients:
                            continue
                        futures_for_adapter[executor.submit(
                            self._save_data_from_parallel_adapters, async_adapter_clients,
                            run_identifier)] = async_adapter_clients

                for future in concurrent.futures.as_completed(futures_for_adapter):
                    try:
                        if isinstance(futures_for_adapter[future], list):
                            for client in futures_for_adapter[future]:
                                known_adapters_status[client] = AdapterStatuses.Done.name
                        else:
                            known_adapters_status[futures_for_adapter[future]
                                                  [PLUGIN_UNIQUE_NAME]] = AdapterStatuses.Done.name
                        run_identifier.update_status(known_adapters_status)
                        num_of_adapters_to_fetch -= 1 if not isinstance(futures_for_adapter[future], list) else \
                            len(futures_for_adapter[future])
                        # future.result()
                    except Exception as err:
                        logger.exception('An exception was raised while trying to get a result.')

            logger.info('Finished getting all device data.')

        except Exception as e:
            logger.exception(f'Getting devices from all requested adapters failed. {current_adapters}')

        return known_adapters_status

    def _save_data_from_parallel_adapters(self, adapters, run_identifier):
        """
        Responsible to update all the adapters status and pass it them all to the insertion function (and of course
        log everything going on).
        :param adapters: list of adapters to update their status
        :param run_identifier: The run identifier to save date to triggerable_history
        """
        start_time = time.time()
        run_identifier.update_status({adapter_name: AdapterStatuses.Fetching.name for adapter_name in adapters})

        logger.info(f'Starting to fetch device for {"".join(adapters)}')
        try:
            data = self._request_insertion_from_adapters_async(adapters)
            for client_name, devices_per_client in data:
                logger.info(f'Got {devices_per_client} for clients under adapter {"".join(client_name)}')

        except (AdapterOffline, ClientsUnavailable) as e:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            logger.warning(f'adapters {"".join(adapters)} might be offline. Reason {str(e)}')
        except Exception as e:
            logger.exception(f'Thread {threading.current_thread()} encountered error: {str(e)}')
            raise

        logger.info(f'Finished for {"".join(adapters)} took {time.time() - start_time} seconds')

    def _save_data_from_adapters(self, adapter_unique_name, run_identifier, known_adapters_status):
        """
        Requests from the given adapter to insert its devices into the DB.
        :param str adapter_unique_name: The unique name of the adapter
        :param RunIdentifier run_identifier: The run identifier to save date to triggerable_history
        :param dict known_adapters_status: The statuses dict to change and save
        """

        start_time = time.time()
        known_adapters_status[adapter_unique_name] = AdapterStatuses.Fetching.name
        run_identifier.update_status(known_adapters_status)

        logger.info(f'Starting to fetch device for {adapter_unique_name}')
        try:
            data = self._request_insertion_from_adapters(adapter_unique_name)
            for client_name, devices_per_client in data:
                logger.info(f'Got {devices_per_client} for client {client_name} in {adapter_unique_name}')

        except (AdapterOffline, ClientsUnavailable) as e:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            logger.warning(f'adapter {adapter_unique_name} might be offline. Reason {str(e)}')
        except Exception as e:
            logger.exception(f'Thread {threading.current_thread()} encountered error: {str(e)}')
            raise

        logger.info(f'Finished for {adapter_unique_name} took {time.time() - start_time} seconds')

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.Core

    @db_migration(raise_on_failure=False, logger=logger)
    def _update_async_schema_version_1(self):
        logger.info(f'Upgrading to schema version 1 - migrate historic labels from tags')
        try:
            collections_devices = self.aggregator_db_connection.list_collection_names(
                filter={'name': {'$regex': r'historical_devices_\d{4}_\d{2}_\d{2}'}})
            collections_devices.sort()
            collections_devices = list(reversed(collections_devices))
            collections_users = self.aggregator_db_connection.list_collection_names(
                filter={'name': {'$regex': r'historical_users_\d{4}_\d{2}_\d{2}'}})
            collections_users.sort()
            collections_users = list(reversed(collections_users))
            collections = collections_devices + collections_users
            for entities_db in [self.aggregator_db_connection[x] for x in collections] + list(
                    self._historical_entity_views_db_map.values()):
                to_fix = []
                logger.info('Updating new entity type for collection {str(entities_db)}')
                count = 0
                for entity in entities_db.find({'tags': {'$elemMatch': {'type': 'label'}}}):
                    internal_axon_id = entity.get('internal_axon_id')
                    if not internal_axon_id:
                        continue
                    labels = []
                    new_tags = []
                    if 'labels' in entity or not 'tags' in entity:
                        continue
                    for tag in entity['tags']:
                        if tag.get('type') == 'label' and tag.get('label_value') and tag.get('data'):
                            labels.append(tag['label_value'])
                        elif tag.get('type') != 'label':
                            new_tags.append(tag)
                    to_fix.append(pymongo.operations.UpdateOne(
                        {'internal_axon_id': internal_axon_id},
                        {
                            '$set': {'tags': new_tags, 'labels': labels}
                        }
                    ))
                    if len(to_fix) % 2500 == 0:
                        count += 1
                        logger.info(f'{str(entities_db)}: Updated {count * 2500} entities')
                        entities_db.bulk_write(to_fix, ordered=False)
                        to_fix.clear()
                if to_fix:
                    logger.info(f'Finished updating {count * 2500 + len(to_fix)} entities')
                    entities_db.bulk_write(to_fix, ordered=False)
                    to_fix.clear()

        except BulkWriteError as e:
            logger.error(f'BulkWriteError: {e.details}')
            raise

    @db_migration(raise_on_failure=False, logger=logger)
    def _update_async_schema_version_2(self):
        logger.info(f'Upgrading to schema version 2 - fix adapter_list_length variable')
        try:
            to_fix = []
            count = 0
            for device in self.devices_db.find({}):
                internal_axon_id = device.get('internal_axon_id')
                correct_adapter_list_length = len(set([adapter[PLUGIN_NAME] for adapter in device.get('adapters', [])]))
                to_fix.append(pymongo.operations.UpdateOne(
                    {'internal_axon_id': internal_axon_id},
                    {
                        '$set': {ADAPTERS_LIST_LENGTH: correct_adapter_list_length}
                    }
                ))
                if len(to_fix) % 2500 == 0:
                    count += 1
                    logger.info(f'Updated {count * 2500} entities')
                    self.devices_db.bulk_write(to_fix, ordered=False)
                    to_fix.clear()
            if to_fix:
                logger.info(f'Finished updating {count * 2500 + len(to_fix)} entities')
                self.devices_db.bulk_write(to_fix, ordered=False)
                to_fix.clear()
        except BulkWriteError as e:
            logger.error(f'BulkWriteError: {e.details}')
            raise

    def _update_async_schema_version_2(self):
        logger.info(f'Upgrading to schema version 2 - migrate wmi adapter hostname')
        try:
            to_fix = []
            internal_axon_id = None
            count = 0
            for device in self.devices_db.find({
                'tags': {
                    '$elemMatch': {'$and': [
                        {'name': 'wmi_adapter_0'},
                        {'data.hostname': {'$exists': True}}
                    ]
                    }}
            }):
                try:
                    internal_axon_id = device.get('internal_axon_id')
                    try:
                        wmi_tag = [tag for tag in device.get('tags', []) if tag['name'] == 'wmi_adapter_0'][0]
                        associated_adapters = wmi_tag.get('associated_adapters', [])
                        wmi_tag_hostname = wmi_tag.get('data', {}).get('hostname', None)
                        if wmi_tag_hostname and associated_adapters:
                            associated_adapter_hostname = [
                                adapter for adapter in device.get('adapters', [])
                                if adapter[PLUGIN_UNIQUE_NAME] == associated_adapters[0][0]][0]. \
                                get('data', {}).get('hostname', None)
                        else:
                            continue
                    except Exception as e:
                        logger.debug(f'Error while getting hostname for {internal_axon_id}: {e}')
                        continue
                    if associated_adapter_hostname and wmi_tag_hostname and \
                            not associated_adapter_hostname.lower().startswith(wmi_tag_hostname.lower()):
                        new_tags_value = [
                            tag for tag in device.get('tags', []) if tag.get('name', '') != 'wmi_adapter_0'
                        ]
                        to_fix.append(pymongo.operations.UpdateOne(
                            {'internal_axon_id': internal_axon_id},
                            {
                                '$set': {'tags': new_tags_value}
                            }
                        ))
                    if len(to_fix) % 2500 == 0 and len(to_fix) != 0:
                        count += 1
                        logger.info(f'Updated {count * 2500} entities')
                        self.devices_db.bulk_write(to_fix, ordered=False)
                        to_fix.clear()
                except Exception as e:
                    logger.debug(f'Error while migrating device {internal_axon_id}: {e}')
                if to_fix:
                    logger.info(f'Finished updating {count * 2500 + len(to_fix)} entities')
                    self.devices_db.bulk_write(to_fix, ordered=False)
                    to_fix.clear()
            self.db_async_schema_version = 2
        except BulkWriteError as e:
            logger.error(f'BulkWriteError: {e.details}')
            raise
        except Exception as e:
            logger.exception(f'Exception while upgrading aggregator db to async version 2. Details: {e}')
