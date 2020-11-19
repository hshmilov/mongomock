import concurrent.futures
import itertools
import logging
import time
from datetime import datetime, timedelta
from enum import Enum, auto
import threading
from threading import Thread
from typing import List, Tuple, Dict

import pymongo
from pymongo.errors import CollectionInvalid, BulkWriteError

from aggregator.exceptions import AdapterOffline, ClientsUnavailable
from aggregator.historical import create_retrospective_historic_collections, MIN_DISK_SIZE
from axonius.db_migrations import db_migration
from axonius.modules.query.consts import PREFERRED_SUFFIX
from axonius.utils.datetime import parse_date
from axonius.utils.mongo_indices import common_db_indexes, non_historic_indexes
from axonius.adapter_base import is_plugin_adapter
from axonius.consts.adapter_consts import NON_THREAD_SAFE_CLEAN_DB_ADAPTERS, AXONIUS_INTERNAL_ID
from axonius.consts.adapter_consts import PREFERRED_FIELDS_PREFIX
from axonius.consts.gui_consts import ParallelSearch, PREFERRED_FIELDS, SPECIFIC_DATA_PREFIX_LENGTH, \
    MAX_DAYS_SINCE_LAST_SEEN
from axonius.consts.plugin_consts import (AGGREGATOR_PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME,
                                          PARALLEL_ADAPTERS,
                                          PLUGIN_NAME,
                                          ADAPTERS_LIST_LENGTH,
                                          CLIENT_ACTIVE, ACTIVE_DIRECTORY_PLUGIN_NAME)
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

    def _request_insertion_from_adapters_async(self, adapters_unique_name: str,
                                               adapters_clients: List[Dict[str, List[str]]]) -> Tuple[str, Dict]:
        """
        Handles all the requests to different adapters to fetch the clients data
        :param adapters_unique_name: list of adapters unique name to trigger.
        :param adapters_clients: List of objects, where key is adapter unique_name
        and the value is the list of the adapter's clients to trigger.
        :return: yields adapter unique name of each adapter and its final data count
        """
        def get_adapter_clients(_adapter_unique_name):
            if not adapters_clients.get(_adapter_unique_name):
                return self._get_db_connection()[_adapter_unique_name]['clients'].find(
                    filter={
                        CLIENT_ACTIVE: {'$ne': False}
                    },
                    projection={
                        'client_id': True,
                        '_id': False
                    })
            return adapters_clients.get(_adapter_unique_name)

        clients = {
            adapter_unique_name: [db_results['client_id']
                                  for adapter_unique_name in adapters_unique_name
                                  for db_results in get_adapter_clients(adapter_unique_name)
                                  ]
            for adapter_unique_name in adapters_unique_name
        }
        if clients and self._notify_on_adapters is True:
            self.create_notification(
                f'Starting to fetch device for {" ".join(adapters_unique_name)}')
        check_fetch_time = True
        for adapter_unique_name in adapters_unique_name:
            data = self._trigger_remote_plugin(adapter_unique_name, 'insert_to_db', data={
                'client_name': clients.get(adapter_unique_name, []),
                'check_fetch_time': check_fetch_time
            })
            try:
                if data and data.content and from_json(data.content).get('min_time_check') is True:
                    logger.info(f'got min_time_check in adapter {adapter_unique_name}: '
                                f'The minimum time between fetches hasn\'t been reached yet.')
                    break
            except Exception:
                logger.exception(f'Error parsing json data, content is: {data.content}')
            check_fetch_time = False
            yield adapter_unique_name, from_json(data.content)

    def get_adapter_clients(self, adapter_unique_name):
        # pylint: disable=C0330
        return [
            x['client_id'] for x in self._get_db_connection()[adapter_unique_name]['clients'].find(
                filter={
                    CLIENT_ACTIVE: {'$ne': False}
                },
                projection={
                    'client_id': True,
                    '_id': False
                }
            )
        ]

    def _request_insertion_from_adapters(self, adapter, clients):
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
        :param List clients: list of clients to execute fetch for.
        """
        data = None
        clients = clients or self.get_adapter_clients(adapter)
        if clients and self._notify_on_adapters is True:
            self.create_notification(f'Starting to fetch device for {adapter}')
        check_fetch_time = True
        for client_name in clients:
            try:
                data = self._trigger_remote_plugin(adapter, 'insert_to_db', data={
                    'client_name': client_name,
                    'check_fetch_time': check_fetch_time
                }, timeout=3600 * 48, stop_on_timeout=True)
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
                    '$addFields': {
                        'accurate_for_datetime': {
                            '$literal': date
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

        logger.info(f'Saving history. max_days_to_save: {str(settings.get("max_days_to_save"))}, '
                    f'save_raw_data: {str(settings.get("save_raw_data"))}')
        self._drop_old_historic_collections(entity_type)
        threads = [
            Thread(target=self.call_safe_collection_transfer,
                   args=(from_db.aggregate,
                         [{
                             '$project': {
                                 '_id': 0
                             }
                         }, {
                             '$addFields': {
                                 'accurate_for_datetime': {
                                     '$literal': now
                                 },
                                 'short_axon_id': {
                                     '$substrCP': [
                                         '$internal_axon_id', 0, 1
                                     ]
                                 }
                             }
                         }, {
                             '$merge': to_db.name
                         }])),
            Thread(target=self._create_daily_historic_collection,
                   args=(entity_type, from_db, now)
                   )
        ]

        if settings.get('save_raw_data'):
            threads.append(
                Thread(target=self.call_safe_collection_transfer,
                       args=(raw_from_db.aggregate, [
                           {
                               '$project': {
                                   '_id': 0
                               }
                           },
                           {
                               '$addFields': {
                                   'accurate_for_datetime': {
                                       '$literal': now
                                   }
                               }
                           },
                           {
                               '$merge': raw_to_db.name
                           }
                       ],))
            )
        # pylint: disable=expression-not-assigned
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

    def get_adapters_data(self, post_json: dict, job_name: str) -> List[Tuple[dict, List]]:
        """
        Get adapters data from list of plugin unique names or mongo filters
        :param post_json: trigger post json data
        :return: list of tuples where first element is adapter and second is client_ids to trigger.
        """
        if post_json and post_json.get('adapters'):
            adapters_list = post_json.pop('adapters', [])
            adapters_filter = {
                PLUGIN_UNIQUE_NAME: {
                    '$in': adapters_list
                }
            }
            adapters = [(adapter, None) for adapter in
                        self.get_available_plugins_from_core_uncached(adapters_filter).values()]
        else:
            adapters = self.get_available_plugins_from_core_uncached(post_json).values()
            adapters = list(self.filter_out_custom_discovery_adapters(adapters, job_name))
        return adapters

    @staticmethod
    def _last_resort_preferred_field(device_data, specific_property, sub_property):
        """
        return the first adapter with field that matched no matter the last_seen or which adapter property it has
        """
        last_seen, val, sub_property_val = datetime(1970, 1, 1, 0, 0, 0), '', ''
        for adapter in device_data['adapters']:
            if adapter.get('plugin_type', '') != 'Adapter':
                continue
            _adapter = adapter.get('data', {})
            if last_seen == datetime(1970, 1, 1, 0, 0, 0) and val == '' and \
                    sub_property is not None and specific_property in _adapter:
                try:
                    sub_property_val = _adapter[specific_property][sub_property] if \
                        isinstance(_adapter[specific_property], dict) else \
                        [x[sub_property] for x in _adapter[specific_property] if sub_property in x]
                # Field not in result
                except Exception:
                    sub_property_val = None
            if val != '':
                break
            if sub_property is not None and specific_property in _adapter and \
                    (sub_property_val != [] and sub_property_val is not None):
                val = sub_property_val
                break
            elif specific_property in _adapter and not isinstance(sub_property, str):
                val = _adapter[specific_property]
                break
            else:
                val = ''
        return val

    @staticmethod
    # pylint: disable=too-many-branches
    def _get_preferred_field_from_ad(device_data, specific_property, sub_property, preferred_field):
        val_changed_by_ad = False
        last_seen, val, sub_property_val = datetime(1970, 1, 1, 0, 0, 0), '', ''
        try:
            for ad_adapter in [ad.get('data', {}) for ad in device_data['adapters'] if
                               ad.get('plugin_name', '') == ACTIVE_DIRECTORY_PLUGIN_NAME]:
                tmp_val = ad_adapter.get(specific_property)
                tmp_last_seen = ad_adapter.get('last_seen')

                if tmp_val is None and tmp_last_seen is None:
                    break
                if tmp_last_seen < last_seen:
                    continue
                if tmp_val is not None and sub_property is not None:
                    try:
                        sub_property_val = tmp_val[sub_property] if isinstance(tmp_val,
                                                                               dict) else \
                            [x[sub_property] for x in tmp_val if sub_property in x]
                    # Field not in result
                    except Exception:
                        sub_property_val = None
                if tmp_val is not None and isinstance(sub_property, str) and \
                        (sub_property_val is not None and sub_property_val != []):
                    val = sub_property_val
                    last_seen = tmp_last_seen
                    val_changed_by_ad = True
                elif tmp_val is not None and sub_property is None:
                    val = tmp_val
                    last_seen = tmp_last_seen
                    val_changed_by_ad = True
                if val == '':
                    last_seen = datetime(1970, 1, 1, 0, 0, 0)
        except TypeError:
            val_changed_by_ad = False
        finally:
            # AD overrides them all
            if val_changed_by_ad:
                last_seen = datetime.now()
                if preferred_field == 'specific_data.data.hostname_preferred' and val:
                    # This is happening regardless of remove_domain_from_preferred_hostname.
                    # we remove the domain in case of AD always.
                    val = val.upper().split('.')[0]
            # pylint: disable=lost-exception
            return val, last_seen

    @staticmethod
    # pylint: disable=too-many-boolean-expressions
    def _get_preferred_field_from_agent_adapter(sub_property, specific_property, _adapter):
        last_seen, val, sub_property_val = datetime(1970, 1, 1, 0, 0, 0), '', ''
        if sub_property is not None and specific_property in _adapter:
            try:
                sub_property_val = _adapter[specific_property][sub_property] if \
                    isinstance(_adapter[specific_property], dict) else \
                    [x[sub_property] for x in _adapter[specific_property] if sub_property in x]
            # Field not in result
            except Exception:
                sub_property_val = None
        if sub_property is not None and specific_property in _adapter and \
                (sub_property_val != [] and sub_property_val is not None):
            val = sub_property_val
            last_seen = _adapter['last_seen']
        elif specific_property in _adapter and not isinstance(sub_property, str):
            val = _adapter[specific_property]
            last_seen = _adapter['last_seen']
        return val, last_seen

    @staticmethod
    def _get_preferred_field_from_assets_adapter(_adapter, sub_property, specific_property):
        last_seen, val, sub_property_val = datetime(1970, 1, 1, 0, 0, 0), '', ''
        if last_seen is None:
            last_seen = datetime(1970, 1, 1, 0, 0, 0)
        if 'adapter_properties' in _adapter and 'Assets' in _adapter['adapter_properties']:
            if sub_property is not None and specific_property in _adapter:
                try:
                    sub_property_val = _adapter[specific_property][sub_property] if \
                        isinstance(_adapter[specific_property], dict) else \
                        [x[sub_property] for x in _adapter[specific_property] if
                         sub_property in x]
                # Field not in result
                except Exception:
                    sub_property_val = None
            if sub_property is not None and specific_property in _adapter and \
                    (sub_property_val != [] and sub_property_val is not None):
                val = sub_property_val
                last_seen = _adapter['last_seen'] if 'last_seen' in _adapter else datetime.now()
            elif specific_property in _adapter and not isinstance(sub_property, str):
                val = _adapter[specific_property]
                last_seen = _adapter['last_seen'] if 'last_seen' in _adapter else datetime.now()
        return val, last_seen

    # pylint: disable=too-many-nested-blocks,too-many-branches,too-many-statements,too-many-boolean-expressions
    def update_device_preferred_fields(self, device_id, preferred_field, device_data, specific_property, sub_property):
        val, last_seen, type_used = '', datetime(1970, 1, 1, 0, 0, 0), None
        remove_domain_from_preferred_hostname = False
        try:
            # pylint: disable=protected-access
            remove_domain_from_preferred_hostname = PluginBase.Instance._remove_domain_from_preferred_hostname or False
            # pylint: enable=protected-access
        except Exception:
            pass
        for adapter in device_data['adapters']:
            if adapter.get('plugin_type', '') != 'Adapter':
                continue
            sub_property_val = ''
            _adapter = adapter.get('data', {})
            # IP addresses we take from cloud providers no matter what (AX-7875)
            if specific_property == 'network_interfaces' and sub_property == 'ips' and \
                    'adapter_properties' in _adapter and 'Cloud_Provider' in _adapter['adapter_properties']:
                try:
                    sub_property_val = _adapter[specific_property][sub_property] if \
                        isinstance(_adapter[specific_property], dict) else \
                        [x[sub_property] for x in _adapter[specific_property] if sub_property in x]
                # Field not in result
                except Exception:
                    sub_property_val = None
                if sub_property_val:
                    val = sub_property_val
                    last_seen = datetime.now()

            # First priority is the latest seen Agent adapter
            if 'adapter_properties' in _adapter and 'Agent' in _adapter['adapter_properties'] \
                    and 'last_seen' in _adapter and isinstance(_adapter['last_seen'], datetime) \
                    and (_adapter['last_seen'] > last_seen or type_used != 'Agent'):
                tmp_val, tmp_last_seen = self._get_preferred_field_from_agent_adapter(sub_property,
                                                                                      specific_property,
                                                                                      _adapter)
                if isinstance(tmp_last_seen, str):
                    tmp_last_seen = parse_date(tmp_last_seen)
                if tmp_val and (tmp_last_seen > last_seen or type_used != 'Agent'):
                    val, last_seen, type_used = tmp_val, tmp_last_seen, 'Agent'

            # Second priority is active-directory data
            if (val != '' and last_seen is not None and isinstance(last_seen, datetime) and
                (datetime.now() - last_seen).days > MAX_DAYS_SINCE_LAST_SEEN) or \
                    (last_seen == datetime(1970, 1, 1, 0, 0, 0) and val == ''):
                tmp_val, tmp_last_seen = self._get_preferred_field_from_ad(device_data,
                                                                           specific_property,
                                                                           sub_property,
                                                                           preferred_field)
                if isinstance(tmp_last_seen, str):
                    tmp_last_seen = parse_date(tmp_last_seen)
                if tmp_val and tmp_last_seen > last_seen:
                    val, last_seen, type_used = tmp_val, tmp_last_seen, 'AD'

            # Third priority is the latest seen Assets adapter
            if (val != '' and last_seen != datetime(1970, 1, 1, 0, 0, 0) and
                isinstance(last_seen, datetime) and
                (datetime.now() - last_seen).days > MAX_DAYS_SINCE_LAST_SEEN) or \
                    (last_seen == datetime(1970, 1, 1, 0, 0, 0) and val == ''):
                tmp_val, tmp_last_seen = self._get_preferred_field_from_assets_adapter(_adapter,
                                                                                       sub_property,
                                                                                       specific_property)
                if isinstance(tmp_last_seen, str):
                    tmp_last_seen = parse_date(tmp_last_seen)
                if tmp_val and tmp_last_seen > last_seen:
                    val, last_seen, type_used = tmp_val, tmp_last_seen, 'Assets'

        # Forth priority is first adapter that has the value
        if last_seen == datetime(1970, 1, 1, 0, 0, 0) and val == '':
            val = self._last_resort_preferred_field(device_data, specific_property, sub_property)

        if remove_domain_from_preferred_hostname:
            if preferred_field == 'specific_data.data.hostname_preferred':
                if isinstance(val, list):
                    val = [str(x).upper().split('.')[0] for x in val]
                val = val.upper().split('.')[0]
        if isinstance(val, list) and any(isinstance(x, list) for x in val):
            val = list(itertools.chain.from_iterable(val))
        if val:
            self.devices_db.update_one(
                {
                    AXONIUS_INTERNAL_ID: device_id
                },
                {
                    '$set': {
                        preferred_field.replace('specific_data.data', PREFERRED_FIELDS_PREFIX): val
                    }
                }
            )

    def update_preferred_fields_values(self, device_ids):
        if not device_ids:
            device_ids = self.devices_db.find({}, projection=[AXONIUS_INTERNAL_ID])
        for device_id in device_ids:
            if isinstance(device_id, dict):
                device_id = device_id.get(AXONIUS_INTERNAL_ID)
            device_data = self.devices_db.find_one({AXONIUS_INTERNAL_ID: device_id})
            if not device_data:
                continue
            for preferred_field in PREFERRED_FIELDS:
                specific_property = preferred_field[SPECIFIC_DATA_PREFIX_LENGTH:].replace(PREFERRED_SUFFIX, '')
                if specific_property.find('.') != -1:
                    specific_property, sub_property = specific_property.split('.')
                else:
                    sub_property = None
                try:
                    self.update_device_preferred_fields(device_id,
                                                        preferred_field,
                                                        device_data,
                                                        specific_property,
                                                        sub_property)
                except Exception as e:
                    logger.exception(f'Problem in creating preferred fields: {e}')
                    continue

    # pylint: disable=inconsistent-return-statements
    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name == 'clean_db':
            # No need for clients data for clean phase.
            adapters = self.get_adapters_data(post_json, job_name)
            adapters = [adapter for adapter, _ in adapters]
            self._clean_db_devices_from_adapters(adapters)
            return
        if job_name == 'fetch_filtered_adapters':
            adapters = self.get_adapters_data(post_json, job_name)
        elif job_name == 'calculate_preferred_fields':
            try:
                self.update_preferred_fields_values(post_json.get('device_ids', []) if post_json else [])
            except Exception:
                logger.error('Couldn\'t recalculate preferred fields values', exc_info=True)
            return
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
            # making adapters to match get_adapters_data return value - List[Tuple]
            # as we need to have clients to filter later on.
            adapters = [(adapter, None) for adapter in adapters]

        logger.debug(f'Fetching from registered adapters and clients = {adapters}')

        return self._fetch_data_from_adapters(adapters, run_identifier)

    def _request_clean_db_from_adapter(self, adapter_unique_list):
        """
        calls /clean_devices on the given adapter unique name
        :return:
        """
        for plugin_unique_name in adapter_unique_list:
            if self.devices_db.count_documents({f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name}, limit=1) or \
                    self.users_db.count_documents({f'adapters.{PLUGIN_UNIQUE_NAME}': plugin_unique_name}, limit=1):
                response = self._trigger_remote_plugin(plugin_unique_name, 'clean_devices')

                if response.status_code != 200:
                    logger.error(f'Failed cleaning db with adapter {plugin_unique_name}. ' +
                                 f'Reason: {str(response.content)}')
                    continue
                break

    def _clean_db_devices_from_adapters(self, current_adapters):
        ''' Function for cleaning the devices db.

        This function runs on all adapters and requests them to clean the db from their devices.
        '''
        try:
            futures_for_adapter = {}
            adapters_name_to_unique = dict()
            num_of_adapters_to_fetch = len(current_adapters)
            synchronic_requests = []
            for adapter in current_adapters:
                if not adapter.get('plugin_type') or not is_plugin_adapter(adapter['plugin_type']):
                    # This is not an adapter, not running
                    num_of_adapters_to_fetch -= 1
                    continue
                if adapter[PLUGIN_NAME] in NON_THREAD_SAFE_CLEAN_DB_ADAPTERS:
                    synchronic_requests.append(adapter[PLUGIN_UNIQUE_NAME])
                    continue
                if adapter[PLUGIN_NAME] not in adapters_name_to_unique:
                    adapters_name_to_unique[adapter[PLUGIN_NAME]] = []
                adapters_name_to_unique[adapter[PLUGIN_NAME]].append(adapter[PLUGIN_UNIQUE_NAME])
            # let's add jobs for all adapters
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._aggregation_max_workers) as executor:
                for adapter_name, adapter_unique_list in adapters_name_to_unique.items():
                    futures_for_adapter[executor.submit(
                        self._request_clean_db_from_adapter, adapter_unique_list)] = adapter_name

                for future in concurrent.futures.as_completed(futures_for_adapter):
                    try:
                        num_of_adapters_to_fetch -= 1
                        future.result()
                        logger.info(f'Finished adapter number {num_of_adapters_to_fetch} - '
                                    f'{futures_for_adapter[future]}')
                    except Exception:
                        logger.exception('An exception was raised while trying to get a result.')
            if synchronic_requests:
                self._request_clean_db_from_adapter(synchronic_requests)
                logger.info(f'Finished with synchronic adapters: {synchronic_requests}')
            logger.info('Finished cleaning all device data.')

        except Exception as e:
            logger.exception(f'Getting devices from all adapters failed, adapters = {current_adapters}. {repr(e)}')

    # pylint: disable=too-many-branches
    def _fetch_data_from_adapters(self, current_adapters_unfiltered: List[Tuple[dict, List]], run_identifier: RunIdentifier):
        """ Function for fetching devices from adapters.
        This function runs on all the received adapters and in a different thread fetches all of them.
        @:param current_adapters_unfiltered: List of tuples of adapters and its relevant clients to trigger.
        """
        # Get rid of adapters with no clients at all
        current_adapters = []
        for adapter, clients in current_adapters_unfiltered:
            if clients or self.get_adapter_clients(adapter[PLUGIN_UNIQUE_NAME]):
                current_adapters.append((adapter, clients))

        known_adapters_status = {}
        for adapter, _ in current_adapters:
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
                for adapter, clients in current_adapters:
                    if not adapter.get('plugin_type') or not is_plugin_adapter(adapter['plugin_type']):
                        # This is not an adapter, not running
                        num_of_adapters_to_fetch -= 1
                        continue

                    elif parallel_fetch and adapter.get('plugin_name') in PARALLEL_ADAPTERS:
                        async_adapters[adapter.get('plugin_name')].append((adapter[PLUGIN_UNIQUE_NAME], clients))
                        continue

                    futures_for_adapter[executor.submit(
                        self._save_data_from_adapters, adapter[PLUGIN_UNIQUE_NAME],
                        run_identifier, known_adapters_status, clients)] = adapter

                if parallel_fetch:
                    for async_adapter_tuples in async_adapters.values():
                        if not async_adapter_tuples:
                            continue
                        futures_for_adapter[executor.submit(
                            self._save_data_from_parallel_adapters, async_adapter_tuples,
                            run_identifier)] = async_adapter_tuples

                for future in concurrent.futures.as_completed(futures_for_adapter):
                    try:
                        if isinstance(futures_for_adapter[future], list):
                            for async_adapter_tuple in futures_for_adapter[future]:
                                adapter_unique_name = async_adapter_tuple[0]
                                known_adapters_status[adapter_unique_name] = AdapterStatuses.Done.name
                        else:
                            known_adapters_status[futures_for_adapter[future]
                                                  [PLUGIN_UNIQUE_NAME]] = AdapterStatuses.Done.name
                        run_identifier.update_status(known_adapters_status)

                        not_done_adapters = []
                        for kas_name, kas_status in known_adapters_status.items():
                            if kas_status != AdapterStatuses.Done.name:
                                not_done_adapters.append(f'{str(kas_name)}: {str(kas_status)}')

                        if not_done_adapters:
                            logger.info(f'Adapters still running or pending: {", ".join(not_done_adapters)}')
                        num_of_adapters_to_fetch -= 1 if not isinstance(futures_for_adapter[future], list) else \
                            len(futures_for_adapter[future])
                        # future.result()
                    except Exception as err:
                        logger.exception('An exception was raised while trying to get a result.')

            logger.info('Finished getting all device data.')

        except Exception as e:
            logger.exception(f'Getting devices from all requested adapters failed. {current_adapters}')

        return known_adapters_status

    def _save_data_from_parallel_adapters(self, adapters: List[Tuple[str, List]], run_identifier):
        """
        Responsible to update all the adapters status and pass it them all to the insertion function (and of course
        log everything going on).
        :param adapters: list Tuples of adapters to update their status and the relevant clients to trigger.
        :param run_identifier: The run identifier to save date to triggerable_history
        """
        start_time = time.time()
        adapter_unique_names = [adapter for adapter, _ in adapters]
        adapters_clients = {
            adapter_unique_name: clients
            for adapter_unique_name, clients in adapters
        }
        run_identifier.update_status({adapter_name: AdapterStatuses.Fetching.name for
                                      adapter_name in adapter_unique_names})

        logger.info(f'Starting to fetch device for {"".join(adapter_unique_names)}')
        try:
            data = self._request_insertion_from_adapters_async(adapter_unique_names, adapters_clients)
            for adapter_unique_names, devices_per_client in data:
                logger.info(f'Got {devices_per_client} for clients under adapter {"".join(adapter_unique_names)}')

        except (AdapterOffline, ClientsUnavailable) as e:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            logger.warning(f'adapters {"".join(adapter_unique_names)} might be offline. Reason {str(e)}')
        except Exception as e:
            logger.exception(f'Thread {threading.current_thread()} encountered error: {str(e)}')
            raise

        logger.info(f'Finished for {"".join(adapter_unique_names)} took {time.time() - start_time} seconds')

    def _save_data_from_adapters(self, adapter_unique_name, run_identifier, known_adapters_status, clients):
        """
        Requests from the given adapter to insert its devices into the DB.
        :param str adapter_unique_name: The unique name of the adapter
        :param RunIdentifier run_identifier: The run identifier to save date to triggerable_history
        :param dict known_adapters_status: The statuses dict to change and save
        :param List clients: list of clients to execute fetch for.
        """

        start_time = time.time()
        known_adapters_status[adapter_unique_name] = AdapterStatuses.Fetching.name
        run_identifier.update_status(known_adapters_status)

        all_clients = clients or self.get_adapter_clients(adapter_unique_name)
        logger.info(f'Starting to fetch device for {adapter_unique_name} with {len(all_clients)} clients')
        try:
            data = self._request_insertion_from_adapters(adapter_unique_name, clients)
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
                #pylint: disable=consider-using-set-comprehension
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

    @db_migration(raise_on_failure=False, logger=logger)
    def _update_async_schema_version_3(self):
        logger.info(f'Upgrading to schema version 3 - migrate wmi adapter hostname')
        try:
            to_fix = []
            internal_axon_id = None
            count = 0
            for device in self.devices_db.find(
                    {
                        'tags': {
                            '$elemMatch': {
                                '$and': [
                                    {
                                        'name': 'wmi_adapter_0'
                                    },
                                    {
                                        'data.hostname':
                                            {
                                                '$exists': True
                                            }
                                    }
                                ]
                            }
                        }
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
        except BulkWriteError as e:
            logger.error(f'BulkWriteError: {e.details}')
            raise
