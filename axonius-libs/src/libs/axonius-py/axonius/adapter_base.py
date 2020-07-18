"""
AdapterBase is an abstract class all adapters should inherit from.
It implements API calls that are expected to be present in all adapters.
"""
# pylint: disable=C0302
import concurrent.futures
import copy
import csv
import json
import logging
import sys
import os
from abc import ABC, abstractmethod
from codecs import BOM_UTF8
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from ipaddress import ip_network, ip_address
from threading import Event, RLock, Thread
from typing import Any, Dict, Iterable, List, Tuple, Optional

import requests

import func_timeout
from bson import ObjectId
from flask import jsonify, request
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from pymongo import ReturnDocument
from retrying import retry

from axonius.consts.adapter_consts import SHOULD_NOT_REFRESH_CLIENTS, CONNECTION_LABEL, \
    CLIENT_ID, VAULT_PROVIDER, DEFAULT_PARALLEL_COUNT, MAX_ASYNC_FETCH_WORKERS, LAST_FETCH_TIME
from axonius.consts.gui_consts import FeatureFlagsNames, ParallelSearch, ACTIVITY_PARAMS_COUNT
from axonius.consts.metric_consts import Adapters
from axonius.logging.audit_helper import (AuditCategory, AuditAction, AuditType)
from axonius.logging.metric_helper import log_metric
from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield
from axonius.thread_pool_executor import LoggedThreadPoolExecutor
from axonius.background_scheduler import LoggedBackgroundScheduler

from axonius import adapter_exceptions
from axonius.consts import adapter_consts
from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME, CORE_UNIQUE_NAME, \
    SYSTEM_SCHEDULER_PLUGIN_NAME, NODE_ID, DISCOVERY_CONFIG_NAME, ENABLE_CUSTOM_DISCOVERY, DISCOVERY_REPEAT_TYPE, \
    DISCOVERY_REPEAT_ON, DISCOVERY_REPEAT_EVERY, DISCOVERY_RESEARCH_DATE_TIME, INSTANCE_CONTROL_PLUGIN_NAME, \
    GUI_PLUGIN_NAME, PARALLEL_ADAPTERS, THREAD_SAFE_ADAPTERS, DEVICE_LOCATION_MAPPING, \
    CSV_IP_LOCATION_FILE
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.devices.device_adapter import LAST_SEEN_FIELD, DeviceAdapter, AdapterProperty, LAST_SEEN_FIELDS
from axonius.mixins.configurable import Configurable
from axonius.mixins.feature import Feature
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import EntityType, PluginBase, add_rule, return_error, RUNNING_ADD_RULES_COUNT
from axonius.thread_stopper import StopThreadException
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.json import to_json
from axonius.utils.mm import delayed_trigger_gc
from axonius.utils.parsing import get_exception_string
from axonius.utils.threading import timeout_iterator
from axonius.mock.adapter_mock import AdapterMock

logger = logging.getLogger(f'axonius.{__name__}')
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


def is_plugin_adapter(plugin_type: str) -> bool:
    """
    Whether or not a plugin is an adapter, according to the plugin_type
    :param plugin_type:
    :return:
    """
    return plugin_type == adapter_consts.ADAPTER_PLUGIN_TYPE


# pylint: disable=too-many-instance-attributes
class AdapterBase(Triggerable, PluginBase, Configurable, Feature, ABC):
    """
    Base abstract class for all adapters
    Terminology:
        'Adapter Source' - The source for data for this plugin. For example, a Domain Controller or AWS
        'Available Device' - A device that the adapter source knows and reports its existence.
                             Doesn't necessary means that the device is turned on or connected.
    """
    DEFAULT_LAST_SEEN_THRESHOLD_HOURS = 24 * 90
    DEFAULT_LAST_FETCHED_THRESHOLD_HOURS = 24 * 2
    DEFAULT_USER_LAST_SEEN = None
    DEFAULT_USER_LAST_FETCHED = 24 * 2
    DEFAULT_MINIMUM_TIME_UNTIL_NEXT_FETCH = None
    DEFAULT_CONNECT_CLIENT_TIMEOUT = 300
    DEFAULT_FETCHING_TIMEOUT = 43200
    DEFAULT_LAST_SEEN_PRIORITIZED = False
    DEFAULT_CLIENT_CONFIG_PARAMS = ['connection_label']
    PING_TUNNEL_CLIENT_CMD = 'docker exec -i openvpn-service ping -c 2 {ip}'
    DEFAULT_TUNNEL_CLIENT_IP = '192.167.255.2'
    PING_CMD_EXPECTED_RESULT = '2 packets transmitted, 2 packets received'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._clients_lock = RLock()
        self._clients = {}
        self._clients_collection = self._get_collection('clients')
        self.__adapter_mock = AdapterMock(self)

        self._send_reset_to_ec()

        self._update_clients_schema_in_db(self._clients_schema())
        self._update_discovery_schema()
        self._set_clients_ids()
        # If set, we do not re-evaluate the clients connections
        should_not_refresh_clients = self.plugin_settings.plugin_settings_keyval[SHOULD_NOT_REFRESH_CLIENTS]
        if should_not_refresh_clients is True:
            del self.plugin_settings.plugin_settings_keyval[SHOULD_NOT_REFRESH_CLIENTS]
            logger.info(f'Clients reevaluation: not evaluating')
        else:
            self._prepare_parsed_clients_config(False)

        self._thread_pool = LoggedThreadPoolExecutor(max_workers=50)

        # This will trigger an 'adapter page' cache clear for better CI stability
        self._request_gui_dashboard_cache_clear()

        self.existential_wondering = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutor(1)})
        self.existential_wondering.add_job(func=self.__check_for_reasons_to_live,
                                           trigger=IntervalTrigger(minutes=1),
                                           next_run_time=datetime.now() + timedelta(minutes=1),
                                           name='check_for_reasons_to_live',
                                           id='check_for_reasons_to_live',
                                           max_instances=1)
        self.existential_wondering.start()
        self.__has_a_reason_to_live = False

    @property
    def __last_fetch_time(self) -> Optional[datetime]:
        return self.plugin_settings.plugin_settings_keyval[LAST_FETCH_TIME]

    @__last_fetch_time.setter
    def __last_fetch_time(self, val: datetime):
        self.plugin_settings.plugin_settings_keyval[LAST_FETCH_TIME] = val

    def _on_config_update(self, config):
        logger.info(f'Loading AdapterBase config: {config}')

        # Devices older then the given deltas will be deleted:
        # Either by:
        self._last_seen_timedelta = timedelta(hours=config['last_seen_threshold_hours']) if \
            config['last_seen_threshold_hours'] else None
        # this is the delta used for 'last_seen' field from the adapter (if provided)

        # Or by:
        self._last_fetched_timedelta = timedelta(hours=config['last_fetched_threshold_hours']) if \
            config['last_fetched_threshold_hours'] else None
        # this is the delta used for comparing 'accurate_for_datetime' - i.e. the last time the devices was fetched

        self.__user_last_seen_timedelta = timedelta(hours=config['user_last_seen_threshold_hours']) if \
            config['user_last_seen_threshold_hours'] else None
        self.__user_last_fetched_timedelta = timedelta(hours=config['user_last_fetched_threshold_hours']) if \
            config['user_last_fetched_threshold_hours'] else None

        self.__next_fetch_timedelta = timedelta(hours=config['minimum_time_until_next_fetch']) if \
            config['minimum_time_until_next_fetch'] else None

        connect_client_timeout = config.get('connect_client_timeout')
        self.__connect_client_timeout = timedelta(seconds=connect_client_timeout) if connect_client_timeout else None

        fetching_timeout = config.get('fetching_timeout')
        self.__fetching_timeout = timedelta(seconds=fetching_timeout) if fetching_timeout else None

        self._is_last_seen_prioritized = config.get('last_seen_prioritized', False)

        self.__is_realtime = config.get('realtime_adapter', False)
        self._connect_via_tunnel = config.get('connect_via_tunnel', False)

        if self._connect_via_tunnel:
            self.request_remote_plugin(f'tunnel/{self.plugin_name}', method='PUT')
        else:
            self.request_remote_plugin(f'tunnel/{self.plugin_name}', method='DELETE')

        # pylint: disable=R0201

    def outside_reason_to_live(self) -> bool:
        """
        Override this to provide more reasons to live
        :return: bool
        """
        return False
        # pylint: enable=R0201

    def __check_for_reasons_to_live(self):
        lives_left = self._get_collection('lives_left').find_one_and_update({
            'lives_left': {
                '$exists': True
            }
        }, {
            '$inc': {
                'lives_left': -1
            }
        }, upsert=True, return_document=ReturnDocument.AFTER)['lives_left']
        if lives_left >= 0:
            logger.debug(f'Reason to live is {lives_left} lives left')
            return

        client_count = self._clients_collection.estimated_document_count()
        running_tasks = self.tasks_in_progress()
        if self.outside_reason_to_live() or running_tasks or client_count:
            logger.debug('Found reason to live')
            logger.debug(f'{client_count} clients exist')
            logger.debug(f'Tasks {", ".join(running_tasks)} are still running')
            self.__has_a_reason_to_live = True
            return

        if not self.__has_a_reason_to_live:
            logger.info('No reason to live. Goodbye!')
            try:
                self._trigger_remote_plugin(CORE_UNIQUE_NAME, f'stop:{self.plugin_unique_name}')
            except Exception:
                logger.critical('Cannot stop ourselves', exc_info=True)
        else:
            logger.info('No reason to live, marking for termination')
            self.__has_a_reason_to_live = False

    @classmethod
    def specific_supported_features(cls) -> list:
        return ['Adapter']

    def _send_reset_to_ec(self):
        """ Function for notifying the EC that this Adapted has been reset.
        """
        try:
            self.request_remote_plugin(
                'action_update/adapter_action_reset?unique_name={0}'.format(self.plugin_unique_name),
                plugin_unique_name='execution',
                method='POST')
        except Exception:
            logger.warning('Failed sending reset to EC')

    def _set_clients_ids(self):
        """
        Just set the self._clients dict with all of our current client ids.
        :return:
        """
        for client in self._get_clients_config():
            if 'client_config' not in client:
                logger.warning(f'Warning, weird client with no client config')
                continue
            client_id = self._get_client_id(client['client_config'])
            self._clients[client_id] = None

    def _prepare_parsed_clients_config(self, blocking=True):
        configured_clients = self._get_clients_config()
        event = Event()

        def refresh():
            with self._clients_lock:
                event.set()
                try:
                    for client in configured_clients:
                        # client id from DB not sent to verify it is updated
                        self._add_client(client['client_config'], client['_id'])
                except Exception:
                    logger.exception('Error while loading clients from config')
                    if blocking:
                        raise

        if blocking:
            refresh()
        else:
            thread = Thread(target=refresh)
            thread.start()
            event.wait()

    def __find_old_axonius_entities(self, entity_age_cutoff: Tuple[date, date], entity_db):
        """
        Scans the DB for axonius devices that have at least one old entity or are pending to be deleted
        :return: entity cursor
        """
        last_seen_cutoff, last_fetched_cutoff = entity_age_cutoff

        dates_for_device = [
            {
                'accurate_for_datetime': {
                    '$lt': last_fetched_cutoff
                }
            },
            {
                f'data.{LAST_SEEN_FIELD}': {
                    '$lt': last_seen_cutoff
                }
            }
        ]
        dbfilter = {
            '$or':
                [
                    {
                        'adapters':
                            {
                                '$elemMatch': {
                                    '$and': [
                                        {
                                            '$or': dates_for_device
                                        },
                                        {
                                            # and the device must be from this adapter
                                            PLUGIN_NAME: self.plugin_name
                                        }
                                    ]
                                }
                            }
                    },
                    {
                        'adapters':
                            {
                                '$elemMatch': {
                                    '$and': [
                                        {
                                            'pending_delete': True
                                        },
                                        {
                                            # and the device must be from this adapter
                                            PLUGIN_NAME: self.plugin_name
                                        }
                                    ]
                                }
                            }
                    }
                ]
        }
        return entity_db.find(dbfilter)

    def __clean_entity(self, age_cutoff, entity_type: EntityType):
        """
        Removes entities from given type from a given age cutoff
        :return:
        """
        db_to_use = self._entity_db_map.get(entity_type)
        futures = []
        with concurrent.futures.ThreadPoolExecutor(10) as r:
            for axonius_entity in self.__find_old_axonius_entities(age_cutoff, db_to_use):
                old_adapter_entities = self.__extract_old_entities_from_axonius_device(axonius_entity,
                                                                                       age_cutoff)
                futures.append(r.submit(self.__unlink_and_delete_entity,
                                        entity_type,
                                        old_adapter_entities))

        deleted_entities_count = sum(x.result() for x in concurrent.futures.wait(futures).done)
        return deleted_entities_count

    def __unlink_and_delete_entity(self, entity_type,
                                   adapter_entities_to_delete):
        counter = 0
        for index, entity_to_remove in enumerate(adapter_entities_to_delete):
            logger.debug(f'Deleting entity {entity_to_remove}')
            try:
                self.delete_adapter_entity(entity_type, *entity_to_remove)
                counter += 1
            except Exception:
                logger.exception(f'Error while unlink')
                continue

        return counter

    def clean_db(self, do_not_look_at_last_cycle=False):
        """
        Figures out which devices are too old and removes them from the db.
        Unlinks devices first if necessary.
        :return: Amount of deleted devices
        """
        device_age_cutoff = self.__device_time_cutoff()
        user_age_cutoff = self.__user_time_cutoff()
        try:
            last_cycle_start = self.__get_last_cycle_start_time()
            if do_not_look_at_last_cycle is False and last_cycle_start:
                # We want to delete all entities that are old. an old entity is an entity that has not been fetched in
                # a defined time, AND was not fetched in the last cycle.
                if device_age_cutoff[1]:
                    device_age_cutoff = (device_age_cutoff[0], min(last_cycle_start, device_age_cutoff[1]))
                if user_age_cutoff[1]:
                    user_age_cutoff = (user_age_cutoff[0], min(last_cycle_start, user_age_cutoff[1]))
        except Exception:
            logger.exception(f'Failed setting entities age cutoff with regards to last cycle start, continuing')
        self.send_external_info_log(f'Cleaning devices and users that are before '
                                    f'{device_age_cutoff}, {user_age_cutoff}')
        logger.info(f'Cleaning devices and users that are before {device_age_cutoff}, {user_age_cutoff}')
        devices_cleaned = self.__clean_entity(device_age_cutoff, EntityType.Devices)
        users_cleaned = self.__clean_entity(user_age_cutoff, EntityType.Users)
        if self._notify_on_adapters is True and (devices_cleaned or users_cleaned):
            self.create_notification(f'Cleaned {devices_cleaned} devices and {users_cleaned} users')
        logger.info(f'Cleaned {devices_cleaned} devices and {users_cleaned} users')
        self._log_activity_adapters_cleanup(EntityType.Devices, self.plugin_name, devices_cleaned)
        self._log_activity_adapters_cleanup(EntityType.Users, self.plugin_name, users_cleaned)
        return {
            EntityType.Devices.value: devices_cleaned,
            EntityType.Users.value: users_cleaned
        }

    # pylint: disable=R1710,too-many-branches
    def _handle_insert_to_db_async(self, client_name, check_fetch_time, log_fetch=True):
        """
        Handles all asymmetric fetching of devices data, by creating a threadpool to handle each fetch in a
        different thread, please notice that it only fetches the data asynchronously but parse in synchronously.
        :param client_name: either a string or a list with client names to fetch
        :param check_fetch_time: last fetch time as passed from the triggered function
        """
        data = {}
        try:
            if self.plugin_name in THREAD_SAFE_ADAPTERS:
                return (yield from self._handle_insert_to_db_async_thread_safe(client_name, check_fetch_time,
                                                                               log_fetch=log_fetch))
            if isinstance(client_name, list):
                for client in client_name:
                    data[client] = [x['raw'] for x in self.insert_data_to_db(client, check_fetch_time=check_fetch_time,
                                                                             parse_after_fetch=True,
                                                                             log_fetch=log_fetch)]
            elif client_name is None:
                # Probably realtime adapter with system_scheduler trigger
                for client in self._clients:
                    data[client] = [x['raw'] for x in self.insert_data_to_db(client, check_fetch_time=check_fetch_time,
                                                                             parse_after_fetch=True,
                                                                             log_fetch=log_fetch)]
            else:
                data[client_name] = [x['raw'] for x in self.insert_data_to_db(client_name,
                                                                              check_fetch_time=check_fetch_time,
                                                                              parse_after_fetch=True,
                                                                              log_fetch=log_fetch)]
            time_before_query = datetime.now()
            results = list(concurrent_multiprocess_yield([y for x in data for y in data[x] if y[0]],
                                                         DEFAULT_PARALLEL_COUNT))
            query_time = datetime.now() - time_before_query
            logger.info(f'Querying {data} took {query_time.seconds} seconds')

        except adapter_exceptions.AdapterException:
            try:
                problematic_client = client_name if isinstance(client_name, str) else client if\
                    isinstance(client, str) else data[client]
            except Exception:
                problematic_client = 'Unknown'
            logger.warning(f'Failed fetching data for client {problematic_client}', exc_info=True)
            yield data[client], ''
        except Exception as e:
            logger.error(f'Failed fetching data asynchronously: {str(e)}', exc_info=True)

        try:
            for client, entity_type, values in results:
                # Currently its only for devices
                if values and entity_type == 'devices':
                    yield client, \
                        self._parse_and_save_data_from_client(client,
                                                              raw_devices=values if isinstance(values, list)
                                                              else [values])
                elif values and entity_type == 'users':
                    yield client, \
                        self._parse_and_save_data_from_client(client,
                                                              raw_users=values if isinstance(values, list)
                                                              else [values])

        except adapter_exceptions.AdapterException:
            # pylint: disable=W0631
            logger.warning(f'Failed parse and save data for client {client}', exc_info=True)
            yield client, ''
        except Exception as e:
            # pylint: disable=W0631
            logger.error(f'Failed parsing and saving data: {str(e)}', exc_info=True)

    def _handle_insert_to_db_async_thread_safe(self, client_name, check_fetch_time, log_fetch=True):
        data = {}
        finished = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_ASYNC_FETCH_WORKERS) as executor:
            try:
                if isinstance(client_name, list):
                    for client in client_name:
                        data[executor.submit(self.insert_data_to_db, client, check_fetch_time=check_fetch_time,
                                             parse_after_fetch=True, thread_safe=True, log_fetch=log_fetch)] = client
                elif client_name is None:
                    # Probably realtime adapter with system_scheduler trigger
                    for client in self._clients:
                        data[executor.submit(self.insert_data_to_db, client, check_fetch_time=check_fetch_time,
                                             parse_after_fetch=True, thread_safe=True, log_fetch=log_fetch)] = client
                else:
                    data[executor.submit(self.insert_data_to_db, client_name, check_fetch_time=check_fetch_time,
                                         parse_after_fetch=True, thread_safe=True, log_fetch=log_fetch)] = client_name

                # Wait until all fetches finish
                for client in concurrent.futures.as_completed(data):
                    finished[data[client]] = client

            except adapter_exceptions.AdapterException:
                try:
                    problematic_client = client_name if isinstance(client_name, str) else client if \
                        isinstance(client, str) else data[client]
                except Exception:
                    problematic_client = 'Unknown'
                logger.warning(f'Failed fetching data for client {problematic_client}', exc_info=True)
                yield data[client], ''
            except Exception as e:
                logger.error(f'Failed fetching data asynchronously: {str(e)}', exc_info=True)

            try:
                for k, v in finished.items():
                    yield k, self._parse_and_save_data_from_client(k,
                                                                   raw_devices=v.result()[0]['raw'],
                                                                   raw_users=v.result()[1]['raw'])
            except adapter_exceptions.AdapterException:
                # pylint: disable=W0631
                logger.warning(f'Failed parse and save data for client {k}', exc_info=True)
                yield client, ''
            except Exception as e:
                # pylint: disable=W0631
                logger.error(f'Failed parsing and saving data: {str(e)}', exc_info=True)

    # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        self.__has_a_reason_to_live = True
        # pylint: disable=too-many-nested-blocks
        if job_name == 'insert_to_db':
            client_name = post_json and post_json.get('client_name')
            if self._connect_via_tunnel:
                res = self._trigger_remote_plugin(
                    INSTANCE_CONTROL_PLUGIN_NAME,
                    job_name='execute_shell',
                    data={'cmd': self.PING_TUNNEL_CLIENT_CMD.format(ip=self.DEFAULT_TUNNEL_CLIENT_IP)},
                    timeout=30,
                    stop_on_timeout=True,
                    priority=True
                )
                res.raise_for_status()
                if self.PING_CMD_EXPECTED_RESULT not in res.text:
                    self.log_activity(AuditCategory.Adapters, AuditAction.Skip, {
                        'adapter': self.plugin_name,
                        'client_id': client_name
                    })
                    self._update_client_status(client_name, 'error')
                    self._trigger_remote_plugin(GUI_PLUGIN_NAME, 'tunnel_is_down', blocking=False)
                    return to_json({'devices_count': 0, 'users_count': 0})
                self._trigger_remote_plugin(GUI_PLUGIN_NAME, 'tunnel_is_up', blocking=False)

            check_fetch_time = False
            if post_json and post_json.get('check_fetch_time'):
                check_fetch_time = post_json.get('check_fetch_time')
            log_fetch = True
            if post_json:
                log_fetch = post_json.get('log_fetch', True)
            parallel_fetch = self.feature_flags_config().get(ParallelSearch.root_key, {}).get(ParallelSearch.enabled,
                                                                                              False)
            try:
                try:
                    if self.plugin_name in PARALLEL_ADAPTERS and parallel_fetch:
                        res = {'devices_count': 0,
                               'users_count': 0
                               }
                        fetch_start_time = datetime.utcnow()
                        for client, result in self._handle_insert_to_db_async(client_name, check_fetch_time,
                                                                              log_fetch=log_fetch):
                            if result != '':
                                result = json.loads(result)
                                res['devices_count'] += result['devices_count']
                                res['users_count'] += result['users_count']
                            logger.info(f'Received from {client}: {result}')

                        if log_fetch:
                            self._log_activity_adapter_client_fetch_summary(self.plugin_unique_name,
                                                                            fetch_start_time,
                                                                            res['users_count'],
                                                                            res['devices_count'])
                        res = to_json(res)
                    else:
                        res = self.insert_data_to_db(client_name, check_fetch_time=check_fetch_time,
                                                     log_fetch=log_fetch)
                except adapter_exceptions.AdapterException:
                    logger.warning(f'Failed inserting data for client '
                                   f'{str(client_name)}', exc_info=True)
                    return ''
                for entity_type in EntityType:
                    if json.loads(res)[f'{entity_type.value.lower()}_count']:
                        self._save_field_names_to_db(entity_type)
                return res

            except BaseException:
                delayed_trigger_gc()
                raise
        elif job_name == 'clean_devices':
            do_not_look_at_last_cycle = False
            if post_json and post_json.get('do_not_look_at_last_cycle') is True:
                do_not_look_at_last_cycle = True
            return to_json(self.clean_db(do_not_look_at_last_cycle))
        elif job_name == 'update_clients_status':
            return self._update_clients_status()
        elif job_name == 'refetch_device':
            try:
                self.refetch_device(client_id=post_json.get('client_id'),
                                    device_id=post_json.get('device_id'))
                return ''
            except Exception as e:
                logger.exception(f'Bad Refetch')
                return str(e)
        else:
            raise RuntimeError('Wrong job_name')

    @add_rule('devices', methods=['GET'])
    def devices_callback(self):
        """ /devices Query adapter to fetch all available devices.
        An 'available' device is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available devices, and returns them
        """
        return jsonify(dict(self._query_data(EntityType.Devices)))

    # Users
    @add_rule('users', methods=['GET'])
    def users_callback(self):
        """ /users Query adapter to fetch all available users.
        An 'available' users is a device that is registered with the adapter source.

        Accepts:
           GET - Finds all available devices, and returns them
        """
        return to_json(dict(self._query_data(EntityType.Users)))

    def _route_query_users_by_client(self):
        """
        Just understands where to route the request, the real or mock adapter.
        :return:
        """
        if self.is_in_mock_mode:
            return self.__adapter_mock.mock_query_users_by_client
        return self._query_users_by_client

    # pylint: disable=R0201
    def _query_users_by_client(self, key, data):
        """
        See _query_devices_by_client
        :param key: the client key
        :param data: the client data
        :return: refer to users()
        """

        # This needs to be implemented by the adapter. However, if it is not implemented, don't
        # crash the system.
        return []

    # pylint: enable=R0201

    def _update_clients_status(self):
        """
        A function that iterate every client config on the adapter, and check its status.
        If the status is error and there is no other trigger while this function was called it tries
        to connect and fetch data, if it succeed it updates the status automatically
        :return:
        """
        # There would always be at least 1 instance of 'update_clients_status' running, just want to make sure that
        # there is no more than 1 instance (In case a whole cycle passed and the task didnt finish),
        # and no other task than that is currently in process
        if len(self.tasks_in_progress()) > 1 and RUNNING_ADD_RULES_COUNT.value > 0:
            return jsonify('Other tasks are running, waiting for next trigger')

        for client_config in self._get_clients_config():
            if client_config['status'] == 'success':
                continue
            try:
                self._clients[client_config['client_id']] = self.__connect_client_facade(client_config)
                self._update_client_status(client_config['client_id'], 'success')
                if self._connect_via_tunnel:
                    self._trigger_remote_plugin(GUI_PLUGIN_NAME, 'tunnel_is_up', blocking=False)
                logger.info(f'Client: {client_config["client_id"]} status was changed to success!')
            except Exception as e:
                logger.error(f'Couldn\'t initiate connection to client: '
                             f'{client_config["client_id"]}, keep it in error status')
                continue
            try:
                post_data = {'check_fetch_time': False, 'client_name': client_config['client_id']}
                self._trigger_remote_plugin_no_blocking(self.plugin_unique_name, 'insert_to_db', data=post_data)
            except Exception as e:
                logger.debug(f'An error happened while trying to insert data to db {str(e)}')
                continue
        return jsonify(f'Adapter {self.plugin_unique_name} finished updating clients status')

    def _parse_users_raw_data_hook(self, raw_users):
        """
        A hook before we call the real parse users.
        :param raw_users: the raw data.
        :return: a list of parsed user objects
        """
        skipped_count = 0
        users_ids = set()

        cutoff_last_seen, _ = self.__user_time_cutoff()

        for parsed_user in self._route_parse_users_raw_data()(raw_users):
            parsed_user.fetch_time = datetime.now()
            assert isinstance(parsed_user, UserAdapter)

            # There is no such thing as scanners for users, so we always check for id here.
            parsed_user_id = parsed_user.id  # we must have an id
            if parsed_user_id in users_ids:
                logger.debug(f'Error! user with id {parsed_user_id} already yielded! skipping')
                continue
            users_ids.add(parsed_user_id)

            parsed_user = parsed_user.to_dict()
            parsed_user = self._remove_big_keys(parsed_user, parsed_user.get('id', 'unidentified user'))
            if self.__is_entity_old_by_last_seen(parsed_user, cutoff_last_seen):
                skipped_count += 1
                continue

            yield parsed_user

        if skipped_count > 0:
            logger.info(f'Skipped {skipped_count} old users')
        else:
            logger.warning('No old users filtered (did you choose ttl period on the config file?)')

        self._save_field_names_to_db(EntityType.Users)

    def _route_parse_users_raw_data(self):
        if self.is_in_mock_mode:
            return self.__adapter_mock.mock_parse_users_raw_data
        return self._parse_users_raw_data

    # pylint: disable=R0201
    def _parse_users_raw_data(self, user) -> Iterable[UserAdapter]:
        """
        This needs to be implemented by the Adapter itself.
        :return:
        """

        return []

    # pylint: enable=R0201

    # End of users

    def _update_client_status(self, client_id, status, error_msg=None):
        with self._clients_lock:
            if error_msg:
                result = self._clients_collection.update_one({'client_id': client_id},
                                                             {'$set': {'status': status, 'error': error_msg}})
            else:
                result = self._clients_collection.update_one({'client_id': client_id},
                                                             {'$set': {'status': status, 'error': ''}})

            if not result or result.matched_count != 1:
                raise adapter_exceptions.CredentialErrorException(
                    f'Could not update client {client_id} with status {status}')

    # pylint: disable=dangerous-default-value
    def _parse_and_save_data_from_client(self, client_name, raw_devices=[], raw_users=[]):
        """
        Takes all the raw devices and users for the async fetching and parse it synchronously.
        :param client_name: the name of the fetched client
        :param raw_devices: list of raw devices data
        :param raw_users: list of raw users data
        :return: json with count of devices and users for this client
        """
        timeout = self.__fetching_timeout
        timeout = timeout.total_seconds() if timeout else None

        try:
            devices = {
                'raw': [],
                'parsed': timeout_iterator(self._parse_devices_raw_data_hook(raw_devices), timeout=timeout,
                                           maxsize=3000)
            }
            users = {
                'raw': [],
                'parsed': timeout_iterator(self._parse_users_raw_data_hook(raw_users), timeout=timeout,
                                           maxsize=3000)
            }
            devices_count = self._save_data_from_plugin(client_name, devices, EntityType.Devices)
            users_count = self._save_data_from_plugin(client_name, users, EntityType.Users)
        except Exception as e:
            self._handle_insert_and_parse_exceptions(client_name, e)

        self._update_client_status(client_name, 'success')
        return to_json({'devices_count': devices_count, 'users_count': users_count})

    def _handle_insert_and_parse_exceptions(self, client_name, execption):
        """
        Handles all the possiable exceptions during parsing the raw devices and users
        :param client_name: the client name
        :param execption: the exception while parsing
        """
        with self._clients_lock:
            current_client = self._clients_collection.find_one({'client_id': client_name})
            if not current_client or not current_client.get('client_config'):
                # No credentials to attempt reconnection
                raise adapter_exceptions.CredentialErrorException(
                    'No credentials found for client {0}. Reason: {1}'.format(client_name, str(execption)))
            self._decrypt_client_config(current_client.get('client_config'))
            self._clean_unneeded_client_config_fields(current_client.get('client_config'))
            if current_client.get('status') != 'success':
                self._log_activity_connection_failure(client_name, execption)
                raise Exception
        try:
            with self._clients_lock:
                self._clients[client_name] = self.__connect_client_facade(current_client['client_config'])
        except Exception as e2:
            # No connection to attempt querying
            error_msg = f'Adapter {self.plugin_name} had connection error' \
                        f' to server with the ID {client_name}. Error is {str(e2)}'
            self.create_notification(error_msg)
            self.send_external_info_log(error_msg)
            self._log_activity_connection_failure(client_name, execption)
            if self.mail_sender and self._adapter_errors_mail_address:
                email = self.mail_sender.new_email('Axonius - Adapter Stopped Working',
                                                   self._adapter_errors_mail_address.split(','))
                email.send(error_msg)
            if self._adapter_errors_webhook:
                try:
                    resposne = requests.post(url=self._adapter_errors_webhook,
                                             json={'error_message': error_msg},
                                             headers={'Content-Type': 'application/json',
                                                      'Accept': 'application/json'},
                                             verify=False)
                    resposne.raise_for_status()
                except Exception:
                    logger.exception(f'Problem sending webhook')
            try:
                opsgenie_connection = self.get_opsgenie_connection()
                if opsgenie_connection:
                    with opsgenie_connection:
                        opsgenie_connection.create_alert(message=error_msg)
            except Exception:
                logger.exception(f'Proble with Opsgenie message')

            logger.exception(f'Problem establishing connection for client {client_name}. Reason: {str(e2)}')
            log_metric(logger, metric_name=Adapters.CONNECTION_ESTABLISH_ERROR,
                       metric_value={client_name},
                       details=str(e2))
            self._update_client_status(client_name, 'error', str(e2))
            raise

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def insert_data_to_db(self, client_name: str = None, check_fetch_time: bool = False,
                          parse_after_fetch: bool = False, thread_safe: bool = False, log_fetch=True):
        """
        Will insert entities from the given client name (or all clients if None) into DB
        :return:
        """

        current_time = datetime.utcnow()
        # Checking that it's either the first time since a new client was added.
        # Or that the __next_fetch_timedelta has passed since last fetch.
        if check_fetch_time and self.__last_fetch_time is not None and self.__next_fetch_timedelta is not None \
                and current_time - self.__last_fetch_time < self.__next_fetch_timedelta:
            logger.info(f'{self.plugin_unique_name}: The minimum time between fetches hasn\'t been reached yet.')
            if self.__user_last_fetched_timedelta is not None and \
                    self.__user_last_fetched_timedelta < self.__next_fetch_timedelta:
                self.create_notification('Bad Adapter Configuration (\'Old user last fetched threshold hours\')',
                                         f'Please note that \'Old user last fetched threshold hours\' is smaller than'
                                         f' \'Minimum time until next fetch entities\' for {self.plugin_name} adapter.',
                                         'warning')

            if self._last_fetched_timedelta is not None and \
                    self._last_fetched_timedelta < self.__next_fetch_timedelta:
                self.create_notification('Bad Adapter Configuration (\'Old device last fetched threshold hours\')',
                                         f'Please note that \'Old device last fetched threshold hours\' is smaller than'
                                         f' \'Minimum time until next fetch entities\' for {self.plugin_name} adapter.',
                                         'warning')
            return to_json({'devices_count': 0, 'users_count': 0, 'min_time_check': True})

        self.__last_fetch_time = current_time
        if client_name:
            devices_count = 0
            users_count = 0
            try:
                if log_fetch:
                    self._log_activity_adapter_client_fetch_start(client_name)
                if parse_after_fetch:
                    return (self._get_data_by_client(client_name, EntityType.Devices,
                                                     parse_after_fetch=parse_after_fetch, thread_safe=thread_safe),
                            self._get_data_by_client(client_name, EntityType.Users,
                                                     parse_after_fetch=parse_after_fetch, thread_safe=thread_safe))

                devices_count = self._save_data_from_plugin(
                    client_name, self._get_data_by_client(client_name, EntityType.Devices), EntityType.Devices)
                users_count = self._save_data_from_plugin(
                    client_name, self._get_data_by_client(client_name, EntityType.Users), EntityType.Users)

                if log_fetch:
                    self._log_activity_adapter_client_fetch_summary(
                        client_name, current_time, users_count, devices_count)

            except Exception as e:
                self._handle_insert_and_parse_exceptions(client_name, e)

            self._update_client_status(client_name, 'success')
        else:
            if log_fetch:
                self._log_activity_adapter_client_fetch_start(client_name)
            devices_count = sum(
                self._save_data_from_plugin(*data, EntityType.Devices)
                for data
                in self._query_data(EntityType.Devices))
            users_count = sum(
                self._save_data_from_plugin(*data, EntityType.Users)
                for data
                in self._query_data(EntityType.Users))
            if log_fetch:
                self._log_activity_adapter_client_fetch_summary(client_name, current_time, users_count, devices_count)

        return to_json({'devices_count': devices_count, 'users_count': users_count})

    def _get_data_by_client(self, client_name: str, data_type: EntityType, parse_after_fetch: bool = False,
                            thread_safe: bool = False) -> dict:
        """
        Get all devices, both raw and parsed, from the given client name
        data_type is devices/users.
        """
        logger.info(f'Trying to query {data_type} from client {client_name}')
        with self._clients_lock:
            if client_name not in self._clients:
                logger.warning(f'client {client_name} does not exist')
                raise adapter_exceptions.ClientDoesntExist('Client does not exist')
        try:
            time_before_query = datetime.now()
            raw_data, parsed_data = self._try_query_data_by_client(client_name, data_type,
                                                                   parse_after_fetch=parse_after_fetch,
                                                                   thread_safe=thread_safe)
            if not parse_after_fetch:
                query_time = datetime.now() - time_before_query
                logger.info(f'Querying {client_name} took {query_time.seconds} seconds - {data_type}')
        except adapter_exceptions.CredentialErrorException as e:
            logger.exception(f'Credentials error for {client_name} on {self.plugin_unique_name}')
            raise adapter_exceptions.CredentialErrorException(
                f'Credentials error for {client_name} on {self.plugin_unique_name}')
        except adapter_exceptions.AdapterException as e:
            logger.exception(f'AdapterException for {client_name} on {self.plugin_unique_name}: {repr(e)}')
            raise adapter_exceptions.AdapterException(
                f'AdapterException for {client_name} on {self.plugin_unique_name}: {repr(e)}')
        except func_timeout.exceptions.FunctionTimedOut:
            logger.exception(f'Timeout for {client_name} on {self.plugin_unique_name}')
            raise adapter_exceptions.AdapterException(f'Fetching has timed out')
        except Exception as e:
            logger.exception(f'Error while trying to get {data_type} for {client_name}. Details: {repr(e)}')
            raise Exception(f'Error while trying to get {data_type} for {client_name}. Details: {repr(e)}')
        else:
            data_list = {'raw': [] if not parse_after_fetch else raw_data,  # AD-HOC: Not returning any raw values
                         'parsed': parsed_data}

            return data_list

    def _route_test_reachability(self, *args, **kwargs):
        if self.is_in_mock_mode:
            return self.__adapter_mock.mock_test_reachability()
        return self._test_reachability(*args, **kwargs)

    @abstractmethod
    def _test_reachability(self, client_config):
        """
        Given all details of a client belonging to the adapter, return consistent key representing it.
        This key must be 'unclassified' - not contain any sensitive information as it is disclosed to the user.

        :param client_config: A dictionary with connection credentials for adapter's client, according to stated in
        the appropriate schema (all required and any of optional)

        :type client_config: dict of objects, following structure stated by client schema

        :return: unique key for the client, composed by given field values, according to adapter's definition
        """

    @add_rule('client_test', methods=['POST'])
    def client_reachability_test(self):
        """ /client_test Returns all available clients, e.g. all DC servers.

        Accepts:
           POST - Triggers a refresh on all available clients from the DB and returns them
        """
        try:
            client_config = request.get_json(silent=True)
            if not client_config:
                return return_error('Invalid client')
            self._clean_unneeded_client_config_fields(client_config)
            return '' if self._route_test_reachability(client_config) \
                else return_error('Client is not reachable.')
        except Exception:
            logger.exception(f'Failed checking client reachability')
            raise

    @add_rule('clients', methods=['GET', 'POST', 'PUT'])
    def clients(self):
        """ /clients Returns all available clients, e.g. all DC servers.

        Accepts:
           GET  - Returns all available clients
           POST - Triggers a refresh on all available clients from the DB and returns them
           PUT (expects client data) - Adds a new client, or updates existing one, according to given data.
                                       Uniqueness compared according to _get_client_id value.
        """
        with self._clients_lock:
            if self.get_method() == 'PUT':
                self.__has_a_reason_to_live = True

                request_data = self.get_request_data_as_object()
                client_config = request_data['connection']
                if not client_config:
                    log_metric(logger, metric_name=Adapters.CREDENTIALS_CHANGE_ERROR, metric_value='invalid client')
                    return return_error('Invalid client')
                try:
                    client_id = self._get_client_id(client_config)
                except Exception as e:
                    err_msg = 'invalid client id - Please check the credentials'
                    log_metric(logger, metric_name=Adapters.CREDENTIALS_CHANGE_ERROR,
                               metric_value=f'{err_msg} - {e if os.environ.get("PROD") == "false" else ""}')
                    logger.warning(f'{err_msg}', exc_info=True)
                    return return_error(err_msg)
                add_client_result = self._add_client(client_config, connection_label=request_data.get(CONNECTION_LABEL))
                if not add_client_result:
                    log_metric(logger, metric_name=Adapters.CREDENTIALS_CHANGE_ERROR,
                               metric_value=f'_add_client failed for {client_id}')
                    return return_error('Could not save client with given config', 400)

                if add_client_result['status'] == 'success':
                    log_metric(logger, metric_name=Adapters.CREDENTIALS_CHANGE_OK, metric_value=client_id)
                else:
                    log_metric(logger, metric_name=Adapters.CREDENTIALS_CHANGE_ERROR,
                               metric_value=add_client_result)
                self.__last_fetch_time = None
                return jsonify(add_client_result), 200

            if self.get_method() == 'POST':
                self.__has_a_reason_to_live = True
                self._prepare_parsed_clients_config()

            return jsonify(self._clients.keys())

    @add_rule('clients/<client_unique_id>', methods=['DELETE'])
    def update_client(self, client_unique_id):
        """
        Update config of or delete an existing client for the adapter, by their client id

        :param client_key:
        :return:
        """
        with self._clients_lock:
            logger.info(f'Deleting client {client_unique_id}')
            client = self._clients_collection.find_one_and_delete({'_id': ObjectId(client_unique_id)})
            if client is None:
                return return_error('No such client')

            self._decrypt_client_config(client['client_config'])
            self._delete_client_connection_label(client)
            self._clean_unneeded_client_config_fields(client['client_config'])
            client_id = ''
            try:
                client_id = self._get_client_id(client['client_config'])
            except KeyError as e:
                logger.info('Problem creating client id, to remove from connected clients')
            try:
                del self._clients[client_id]
            except KeyError as e:
                logger.info(f'No connected client {client_id} to remove')
            return '', 200

    def _write_client_to_db(self, client_id, client_config, status, error_msg, upsert=True):
        if client_id is not None:
            logger.info(f'Updating new client status in db - {status}. client id: {client_id}')
            return self._clients_collection.replace_one({'client_id': client_id},
                                                        {'client_id': client_id,
                                                         'client_config': client_config,
                                                         'status': status,
                                                         'error': error_msg},
                                                        upsert=upsert)
        return None

    def _add_client(self, client_config: dict, object_id=None, new_client=True, connection_label=None):
        """
        Execute connection to client, according to given credentials, that follow adapter's client schema.
        Add created connection to adapter's clients dict, under generated key.

        :param client_config: Credential values representing a client of the adapter
        :param object_id: The mongo object id
        :param new_client: If this is a recycled client (i.e. from _prepare_parsed_clients_config) or a new one
        :return: Mongo id of created or updated document (updated should be the given client_unique_id)

        assumes self._clients_lock is locked by the current thread
        """
        client_id = None
        status = 'warning'
        error_msg = None
        encrypted_client_config = copy.deepcopy(client_config)
        self._encrypt_client_config(encrypted_client_config)
        try:
            client_id = self._get_client_id(client_config)
            # Writing initial client to db
            res = self._write_client_to_db(client_id, encrypted_client_config, status, error_msg, upsert=new_client)
            if res.matched_count == 0 and not new_client:
                logger.warning(f'Client {client_id} : {client_config} was deleted under our feet!')
                return None
            # add/update clients connection labels
            if connection_label is not None:
                self._write_client_connection_label(client_id, connection_label)

            status = 'error'  # Default is error
            self._clients[client_id] = self.__connect_client_facade(client_config)
            # Got here only if connection succeeded
            status = 'success'
            if self._connect_via_tunnel:
                self._trigger_remote_plugin(GUI_PLUGIN_NAME, 'tunnel_is_up', blocking=False)

        except (adapter_exceptions.ClientConnectionException, KeyError, Exception) as e:
            self._clients[client_id] = None
            error_msg = str(e)
            id_for_log = client_id if client_id else str(object_id or '')
            logger.exception(f'Got error while handling client {id_for_log} - '
                             f'possibly compliance problem with schema.')

        result = self._write_client_to_db(client_id, encrypted_client_config, status, error_msg, upsert=False)
        if result is None and object_id is not None:
            # Client id was not found due to some problem in given config data
            # If id of an existing document is given, update its status accordingly
            result = self._clients_collection.update_one(
                {'_id': object_id}, {'$set': {'status': status}})
        elif result is None:
            # No way of updating other than logs and no return value
            logger.error('Not updating client since no DB id and no client id exist')
            return None
        elif res.matched_count == 0 and not new_client:
            logger.warning(f'Client {client_id} : {client_config} was deleted under our feet!')
            return None

        # Verifying update succeeded and returning the matched id and final status
        if result.modified_count:
            object_id = self._clients_collection.find_one({'client_id': client_id}, projection={'_id': 1})['_id']
            return {'id': str(object_id), 'client_id': client_id, 'status': status, 'error': error_msg}

        return None

    def _write_client_connection_label(self, client_id: str, connection_label: str):
        """
        update client connection label mapping entry.
        DB aggregator, collection: adapters_client_labels

        :param client_id: adapter client ID ( a.k.a client_used )
        :param client_config: the client connection data set , include connection label
        """
        resp = self.adapter_client_labels_db.replace_one({
            CLIENT_ID: client_id,
            NODE_ID: self.node_id,
            PLUGIN_UNIQUE_NAME: self.plugin_unique_name
        }, {
            CLIENT_ID: client_id,
            CONNECTION_LABEL: connection_label,
            PLUGIN_UNIQUE_NAME: self.plugin_unique_name,
            PLUGIN_NAME: self.plugin_name,
            NODE_ID: self.node_id
        }, upsert=True)

        if not resp.acknowledged:
            logger.info(
                f'Failed to save connection label {connection_label} for client {client_id} on node {self.node_id}')

    def _delete_client_connection_label(self, client_config: dict):
        '''
        remove client connection label mapping entry.
        DB aggregator, collection: adapters_client_labels

        :param client_config: the client connection data set, include connection label
        '''
        if CLIENT_ID in client_config:
            resp = self.adapter_client_labels_db.delete_one({
                CLIENT_ID: client_config.get(CLIENT_ID),
                PLUGIN_UNIQUE_NAME: self.plugin_unique_name,
                NODE_ID: self.node_id
            })

            if resp.deleted_count == 0 and not resp.acknowledged:
                logger.warning(f'Connection Label deletion failure for client {client_config.get(CLIENT_ID)} '
                               f'from node {client_config.get(NODE_ID)} '
                               f'with Connection Label {client_config.get(CONNECTION_LABEL)}')

    @add_rule('correlation_cmds', methods=['GET'])
    def correlation_cmds(self):
        """ /correlation_cmds Get a dictionary between OS type and shell command that'll figure out the device ID
        refer to https://axonius.atlassian.net/wiki/spaces/AX/pages/90472522/Correlation+Implementation for more
        """
        return jsonify(self._correlation_cmds())

    @add_rule('parse_correlation_results', methods=['POST'])
    def parse_correlation_results(self):
        """ /parse_correlation_results Parses the given results (as string) into a device ID
        Assumes POST data has:
        {
            'result': 'some text',
            'os': 'Windows' # or Linux, or whatever else returned as a key from /correlation_cmds
        }
        :return: str
        """
        data = request.get_json(silent=True)
        if data is None:
            return return_error('No data received')
        if 'result' not in data or 'os' not in data:
            return return_error('Invalid data received')
        return jsonify(self._parse_correlation_results(data['result'], data['os']))

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def _update_action_data(self, action_id, status, output=None):
        """ A function for updating the EC on new action status.

        This function will initiate an POST request to the EC notifying on the new action status.

        :param str action_id: The action id of the related update
        :param str status: The new status of the action
        :param dict output: The output of the action (in case finished or error)
        """
        self.request_remote_plugin('action_update/{0}'.format(action_id),
                                   plugin_unique_name='execution',
                                   method='POST',
                                   timeout=10,
                                   data=json.dumps({'status': status, 'output': output or {}}))

    def _run_action_thread(self, func, device_data, action_id, **kwargs):
        """ Function for running new action.

        This function should run as a new thread an handle the running of the wanted action.
        It will call the correct abstract action function implemented by the adapter and wait for it
        To finish. This function assumes that the adapter action function is blocking until the action
        Is finished.

        :param func func: A pointer to the action function (according to the action type requested)
        :param json device_data: The raw device data for running the action
        :param str action_id: The id of the current action
        :param **kwargs: Another parameters needed for this specific action (retrieved from the request body)
        """
        # Sending update that this action has started
        try:
            self._update_action_data(action_id,
                                     status='started',
                                     output={'result': 'In Progress', 'product': 'In Progress'})
        except Exception:
            logger.warning(f'Error updating action status. action id:{action_id}', exc_info=True)
        try:
            # Running the function, it should block until action is finished
            result = func(device_data, **kwargs)
        except Exception:
            logger.warning(f'Failed running actionid {action_id}', exc_info=True)
            self._update_action_data(action_id, status='failed', output={
                'result': 'Failure', 'product': get_exception_string()})
            return

        # Sending the result to the issuer
        if str(result.get('result')).lower() == 'success':
            status = 'finished'
        else:
            status = 'failed'
        self._update_action_data(action_id, status=status, output=result)

    @add_rule('action/<action_type>', methods=['POST'])
    def rest_new_action(self, action_type):
        # Getting action id from the URL
        action_id = self.get_url_param('action_id')
        request_data = self.get_request_data_as_object()
        device_data = request_data.pop('device_data')

        if action_type not in ['get_files', 'put_files', 'execute_binary', 'execute_shell', 'execute_wmi_smb',
                               'delete_files', 'execute_axr']:
            return return_error('Invalid action type', 400)

        if action_type not in self.supported_execution_features():
            return return_error('Operation not implemented yet', 501)  # 501 -> Not implemented

        needed_action_function = getattr(self, action_type)

        logger.debug(f'Got action type {action_type}. Request data is {request_data}')

        self._thread_pool.submit(self._run_action_thread,
                                 needed_action_function,
                                 device_data,
                                 action_id,
                                 **request_data)
        return ''

    # pylint: disable=R0201
    def supported_execution_features(self):
        return []

    def put_files(self, device_data, files_path, files_content):
        raise RuntimeError('Not implemented yet')

    def get_files(self, device_data, files_path):
        raise RuntimeError('Not implemented yet')

    def execute_binary(self, device_data, binary_file_path, binary_params):
        raise RuntimeError('Not implemented yet')

    def execute_shell(self, device_data, extra_files, shell_commands):
        raise RuntimeError('Not implemented yet')

    def execute_axr(self, device_data, axr_commands):
        raise RuntimeError('Not implemented yet')

    def execute_wmi_smb(self, device_data, wmi_smb_commands=None):
        raise RuntimeError('Not implemented yet')

    def delete_files(self, device_data, files_path):
        raise RuntimeError('Not implemented yet')

    # pylint: enable=R0201

    @add_rule('get_client_id', methods=['POST'])
    def get_client_id(self):
        client_config = request.get_json(silent=True)
        return self._get_client_id(client_config), 200

    @abstractmethod
    def _get_client_id(self, client_config):
        """
        Given all details of a client belonging to the adapter, return consistent key representing it.
        This key must be 'unclassified' - not contain any sensitive information as it is disclosed to the user.

        :param client_config: A dictionary with connection credentials for adapter's client, according to stated in
        the appropriate schema (all required and any of optional)

        :type client_config: dict of objects, following structure stated by client schema

        :return: unique key for the client, composed by given field values, according to adapter's definition
        """

    def _get_password_fields_from_schema(self):
        """
            Get all the password fields from schema
        """
        return [item['name'] for item in self._clients_schema()['items'] if item.get('format') == 'password']

    def _normalize_password_fields(self, client_config):
        """
        Checks if a vault password needs to be fetched replaces.
        :return:
        """
        client_config_copy = copy.deepcopy(client_config)
        # Get all the password fields from schema
        password_fields = self._get_password_fields_from_schema()

        # Get all the vault fields from the client_config
        vault_connection_fields = [(field, client_config_copy[field])
                                   for field
                                   in password_fields
                                   if isinstance(client_config_copy.get(field), dict) and
                                   client_config_copy[field].get('type') == VAULT_PROVIDER]

        for adapter_field_name, vault_data in vault_connection_fields:
            client_config_copy[adapter_field_name] = self.vault_pwd_mgmt.query_password(adapter_field_name,
                                                                                        vault_data.get('data'))

        return client_config_copy

    def _clean_unneeded_client_config_fields(self, client_config):
        """
        clean default fields from client config like connection_label
        there is adapters that expect only their schema fields, unknown field will cause exceptions
        :param client_config: clean and ready to ship client_config
        """
        if not client_config:
            return

        for param in self.DEFAULT_CLIENT_CONFIG_PARAMS:
            if param in client_config:
                del client_config[param]

    def _route_connect_client(self, client_config, *args, **kwargs):
        if self.is_in_mock_mode:
            return self.__adapter_mock.mock_connect_client()
        self._clean_unneeded_client_config_fields(client_config)
        normalized_client_config = self._normalize_password_fields(client_config)
        return self._connect_client(normalized_client_config, *args, **kwargs)

    @abstractmethod
    def _connect_client(self, client_config):
        """
        Given all details of a client belonging to the adapter, tries connecting to it and creating a connection obj.
        If connection attempt failed, throws exception with the reason

        :param client_config: A dictionary with connection credentials for adapter's client, according to stated in
        the appropriate schema (all required and any of optional)

        :type client_config: dict of objects, following structure stated by client schema

        :returns: Adapter's connection object, if connection attempt succeeded with given credentials

        :raises AdapterExceptions.ClientConnectionException: In case of error connecting, return adapter's exception
        """

    def __connect_client_facade(self, client_config):
        """
        This calls _connect_client in safe, timeout based way.
        Parameters and return type are the same as _connect_client
        """
        timeout = self.__connect_client_timeout
        timeout = timeout.total_seconds() if timeout else None

        def call_connect_as_stoppable(*args, **kwargs):
            try:
                client = self._route_connect_client(*args, **kwargs)
                return client
            except BaseException as e:
                # this is called from an external thread so if it raises the exception is lost,
                # this allows forwarding exceptions back to the caller
                return e

        try:
            res = func_timeout.func_timeout(
                timeout=timeout,
                func=call_connect_as_stoppable,
                args=[client_config])
            if isinstance(res, BaseException):
                raise res
            return res
        except func_timeout.exceptions.FunctionTimedOut:
            logger.info(f'Timeout on connection for client config with {timeout} time')
            raise adapter_exceptions.ClientConnectionException(f'Connecting has timed out ({timeout} seconds)')
        except StopThreadException:
            logger.info(f'Stopped connecting for client config')
            raise adapter_exceptions.ClientConnectionException(f'Connecting has been stopped')

    def _route_query_devices_by_client(self):
        """
        Just understands where to route the request, the real or mock adapter.
        :return:
        """
        if self.is_in_mock_mode:
            return self.__adapter_mock.mock_query_devices_by_client
        return self._query_devices_by_client

    # pylint: disable=no-self-use
    def _refetch_device(self, client_id, client_data, device_id):
        raise Exception('Not implemented in adapter')

    # pylint: enable=no-self-use

    # pylint: disable=R0201
    def _query_devices_by_client(self, client_name, client_data):
        """
        Returns all devices from a specific client.
        Refer to devices(client) docs for the return type.

        :param client_name: str # valid values are from self._get_clients
        :param client_data: The data of the client, as returned from the _parse_clients_data function
        :return: adapter dependant
        """
        return []

    # pylint: enable=R0201

    def __is_old_entity(self, parsed_entity, cutoff: Tuple[date, date]) -> bool:
        """ Check if the entity is considered 'old'.

        :param parsed_entity: A parsed data of the entity
        :return: If the entity is old or not.
        """
        seen_cutoff, fetched_cutoff = cutoff
        return self.__is_entity_old_by_last_fetched(parsed_entity, fetched_cutoff) or \
            self.__is_entity_old_by_last_seen(parsed_entity['data'], seen_cutoff)

    @staticmethod
    def __is_entity_old_by_last_seen(parsed_entity_data, seen_cutoff: date):
        if not seen_cutoff:
            return False
        for last_seen_field in LAST_SEEN_FIELDS:
            if last_seen_field in parsed_entity_data:
                if parsed_entity_data[last_seen_field].astimezone(seen_cutoff.tzinfo) < seen_cutoff:
                    return True
        return False

    @staticmethod
    def __is_entity_old_by_last_fetched(parsed_entity, fetched_cutoff: date):
        if not fetched_cutoff:
            return False
        if 'accurate_for_datetime' in parsed_entity:
            return parsed_entity['accurate_for_datetime'].astimezone(fetched_cutoff.tzinfo) < fetched_cutoff
        return False

    def _is_adapter_old_by_last_seen(self, adapter_device, device_age_cutoff=None):
        seen_cutoff = device_age_cutoff or self.__device_time_cutoff()[0]
        return self.__is_entity_old_by_last_seen(adapter_device, seen_cutoff)

    def __extract_old_entities_from_axonius_device(self, axonius_device, entity_age_cutoff: Tuple[date, date]) \
            -> Iterable[Tuple[str, str]]:
        """
        Finds all entities that are old in an axonius device
        """
        for adapter in axonius_device['adapters']:
            if adapter[PLUGIN_NAME] == self.plugin_name:
                if self.__is_old_entity(adapter, entity_age_cutoff) or adapter.get('pending_delete') is True:
                    yield adapter[PLUGIN_UNIQUE_NAME], adapter['data']['id']

    def _remove_big_keys(self, key_to_check, entity_id):
        """ Function for removing big elements in data chanks.

        Function will recursively pass over known data types and remove big values

        :param key_to_check: A key to check size for
        :return: A key with no big data fields
        """
        if sys.getsizeof(key_to_check) < 1e5:  # Key smaller than ~100kb
            # Return small devices immediately
            return key_to_check

        # If we reached here it means that the key is too big, trying to clean known data types
        if isinstance(key_to_check, dict):
            key_to_check = {key: self._remove_big_keys(value, entity_id) for key, value in key_to_check.items()}

        elif isinstance(key_to_check, list):
            key_to_check = [self._remove_big_keys(val, entity_id) for val in key_to_check]

        # Checking if the key is small enough after the filtering big sub-keys
        if sys.getsizeof(key_to_check) < 1e5:  # Key smaller than ~100kb
            # Key is smaller now, we can return it
            return key_to_check
        # Data type not recognized or can't filter key, deleting the too big key
        logger.warning(f'Found too big key on entity (Device/User) {entity_id}. Deleting')
        return {'AXON_TOO_BIG_VALUE': sys.getsizeof(key_to_check)}

    def _parse_devices_raw_data_hook(self, raw_devices):
        """
        :param raw_devices: raw devices as fetched by adapter
        :return: iterator of processed raw device entries
        """
        skipped_count = 0
        last_seen_cutoff, _ = self.__device_time_cutoff()
        device_ids_and_last_seen = {}
        should_check_for_unique_ids = self.plugin_subtype == PluginSubtype.AdapterBase

        for parsed_device in self._route_parse_raw_data()(raw_devices):
            assert isinstance(parsed_device, DeviceAdapter)
            parsed_device.generate_direct_connected_devices()
            parsed_device.fetch_time = datetime.now()
            try:
                if self._uppercase_hostnames and parsed_device.hostname:
                    parsed_device.hostname = parsed_device.hostname.upper()
            except Exception:
                pass

            # All scanners should have this automatically
            if self.plugin_subtype == PluginSubtype.ScannerAdapter:
                parsed_device.scanner = True

            if should_check_for_unique_ids:
                parsed_device_id = parsed_device.id  # we must have an id (its definitely not a scanner)
                try:
                    parsed_device_last_seen = parsed_device.last_seen
                except Exception:
                    # not all adapters have that
                    parsed_device_last_seen = None
                if parsed_device_id in device_ids_and_last_seen.keys():
                    logger.debug(f'Error! device with id {parsed_device_id} already yielded! '
                                 f'First device last seen: {str(device_ids_and_last_seen.get(parsed_device_id))}, '
                                 f'current yielded last seen: {str(parsed_device_last_seen)}. skipping')
                    continue
                device_ids_and_last_seen[parsed_device_id] = parsed_device_last_seen

            try:
                parsed_device = self.__ip_to_location_csv(parsed_device)
            except Exception:
                logger.error('Error while trying to check and update ip location', exc_info=True)
            parsed_device = parsed_device.to_dict()
            parsed_device = self._remove_big_keys(parsed_device, parsed_device.get('id', 'unidentified device'))
            if self._is_adapter_old_by_last_seen(parsed_device, last_seen_cutoff):
                skipped_count += 1
                continue

            yield parsed_device

        if skipped_count > 0:
            logger.info(f'Skipped {skipped_count} old devices')
        else:
            logger.warning('No old devices filtered (did you choose ttl period on the config file?)')

        self._save_field_names_to_db(EntityType.Devices)

    def __ip_to_location_csv(self, device):
        """
        Checks every device that have ip address in its network interfaces, if the ip_to_location_csv option
        is enabled and the csv is valid then it adds another field to the network_interfaces with the desired location
        :param device: a Device dict
        :return: Device with location in its network interfaces
        """
        static_analysis_settings = self._static_analysis_settings
        if static_analysis_settings and static_analysis_settings.get(DEVICE_LOCATION_MAPPING, {}).get('enabled') and \
                static_analysis_settings.get(DEVICE_LOCATION_MAPPING, {}).get(CSV_IP_LOCATION_FILE):

            csv_file = self._grab_file_contents(
                static_analysis_settings.get(
                    DEVICE_LOCATION_MAPPING)[CSV_IP_LOCATION_FILE],
                stored_locally=False).replace(BOM_UTF8, b'').decode('utf-8')

            reader = csv.DictReader(self.lower_and_strip_first_line(StringIO(csv_file)))
            ip_location_map = [(ip_network(row['subnet'], strict=False), row) for row in reader]

            nics = device.network_interfaces
            for i, nic in enumerate(nics):
                ip_locations = self.get_geolocation_of_ip(ip_location_map, nic['ips'] if
                                                          isinstance(nic, dict) and 'ips' in nic else nic.ips)
                if ip_locations:
                    for ip_location in ip_locations:
                        # Handle basic fields
                        del ip_location['subnet']
                        locations = []
                        if 'location' in ip_location and ip_location['location'].strip():
                            locations.append(ip_location['location'].strip())
                            del ip_location['location']
                        if 'location_name' in ip_location and ip_location['location_name'].strip():
                            locations.append(ip_location['location_name'].strip())
                            del ip_location['location_name']
                        if locations:
                            if (isinstance(nic, dict) and 'locations' in nic) or hasattr(nic, 'locations'):
                                nic['locations'] = list(set(nic['locations'] + locations))
                            else:
                                nic['locations'] = locations

                        # Handle complex fields
                        for detail in ip_location:
                            if not ip_location[detail].strip():
                                continue
                            if (isinstance(nic, dict) and detail in nic) or hasattr(nic, detail):
                                nic[detail] = list(set(nic[detail] + [ip_location[detail].strip()]))
                            else:
                                nic[detail] = [ip_location[detail].strip()]
        return device

    @staticmethod
    def get_geolocation_of_ip(ip_location_map, ips):
        """
        Return the geo locations of ips if listed in the map, otherwise return []
        :param ip_location_map: a list with tuples of (IP, Location)
        :param ips: IP addresses
        :return: Location or []
        """
        all_details = []
        for subnet, details in ip_location_map:
            for ip in ips:
                if ip_address(ip) in subnet:
                    all_details.append(details)
        return all_details

    def _try_query_data_by_client(self, client_id, entity_type: EntityType, use_cache=True, parse_after_fetch=False,
                                  thread_safe=False):
        """
        Try querying data for given client. If fails, try reconnecting to client.
        If successful, try querying data with new connection to the original client, up to 3 times.

        This is an attempt to resolve problems with fetching data that may be caused by an outdated connection
        or to discover a real problem fetching devices, despite a working connection.

        :return: Raw and parsed data list if fetched successfully, whether immediately or with fresh connection
        :raises Exception: If client connection or client data query errored 3 times
        """

        def _get_raw_and_parsed_data():
            mapping = {
                EntityType.Devices: (self._route_query_devices_by_client(), self._parse_devices_raw_data_hook),
                EntityType.Users: (self._route_query_users_by_client(), self._parse_users_raw_data_hook)
            }
            raw, parse = mapping[entity_type]

            def call_raw_as_stoppable(*args, **kwargs):
                try:
                    return raw(*args, **kwargs)
                except func_timeout.exceptions.FunctionTimedOut as e:
                    logger.error(f'Timeout for {client_id} on {self.plugin_unique_name}')

                    self.create_notification(f'Timeout after {timeout} seconds for \'{client_id}\''
                                             f' client on {self.plugin_unique_name}'
                                             f' while fetching {entity_type.value}', repr(e))
                except StopThreadException:
                    raise
                except BaseException:
                    logger.exception('Unexpected exception')

            timeout = self.__fetching_timeout
            timeout = timeout.total_seconds() if timeout else None

            try:
                self._clients[client_id] = self.__connect_client_facade(self._get_client_config_by_client_id(client_id))
                self._update_client_status(client_id, 'success')
                if self._connect_via_tunnel:
                    self._trigger_remote_plugin(GUI_PLUGIN_NAME, 'tunnel_is_up', blocking=False)
            except Exception as e:
                self._clients[client_id] = None
                self._update_client_status(client_id, 'error', str(e))
                raise
            if not parse_after_fetch or thread_safe:
                _raw_data = func_timeout.func_timeout(
                    timeout=timeout,
                    func=call_raw_as_stoppable,
                    args=(client_id, self._clients[client_id]))
                logger.info('Got raw')
            else:
                # Multiprocess date fetch
                _raw_data = \
                    (
                        # pylint: disable=no-member
                        self._query_devices_by_client_parallel() if entity_type.value == 'devices'
                        else self._query_users_by_client_parallel()
                        if hasattr(self.__class__, '_query_users_by_client_parallel') else [],
                        (),
                        {'client_name': client_id, 'client_data': self._clients[client_id]}
                    )

            # maxsize=3000 means we won't hold more than 3k devices in memory
            # and will reduce the chances of thread exhaustion between the fetching thread (the adapter code)
            # and the insertion to db threads (plugin_base code)
            if parse_after_fetch:
                return _raw_data, []
            _parsed_data = timeout_iterator(parse(_raw_data), timeout=timeout, maxsize=3000)

            logger.info('Got parsed')
            return _raw_data, _parsed_data

        self._save_field_names_to_db(entity_type)
        raw_data, parsed_data = _get_raw_and_parsed_data()
        if parse_after_fetch:
            return raw_data, parsed_data
        return [], parsed_data  # AD-HOC: Not returning any raw values

    def refetch_device(self, client_id, device_id):
        client_data = self.__connect_client_facade(self._get_client_config_by_client_id(client_id))
        # pylint: disable=assignment-from-no-return
        parsed_device = self._refetch_device(client_id, client_data, device_id)
        # pylint: enable=assignment-from-no-return
        parsed_device.generate_direct_connected_devices()
        parsed_device.fetch_time = datetime.now()
        try:
            if self._uppercase_hostnames and parsed_device.hostname:
                parsed_device.hostname = parsed_device.hostname.upper()
        except Exception:
            pass

        # All scanners should have this automatically
        if self.plugin_subtype == PluginSubtype.ScannerAdapter:
            parsed_device.scanner = True
        self._save_data_from_plugin(
            client_id,
            {'raw': [], 'parsed': [parsed_device.to_dict()]},
            EntityType.Devices, False)
        self._save_field_names_to_db(EntityType.Devices)

    def _query_data(self, entity_type: EntityType) -> Iterable[Tuple[Any, Dict[str, Any]]]:
        """
        Synchronously returns all available data types (devices/users) from all clients.
        """
        with self._clients_lock:
            clients = self._clients.copy()
            if len(clients) == 0:
                logger.info(f'{self.plugin_unique_name}: Trying to fetch devices but no clients found')
                return

        # Running query on each device
        for client_name in clients:
            try:
                raw_data, parsed_data = self._try_query_data_by_client(client_name, entity_type)
            except adapter_exceptions.CredentialErrorException as e:
                logger.warning(f'Credentials error for {client_name} on {self.plugin_unique_name}: {repr(e)}')
                self.create_notification(f'Credentials error for {client_name} on {self.plugin_unique_name}', repr(e))
                raise
            except adapter_exceptions.AdapterException as e:
                logger.exception(f'Error for {client_name} on {self.plugin_unique_name}: {repr(e)}')
                self.create_notification(f'Error for {client_name} on {self.plugin_unique_name}', repr(e))
                raise
            except func_timeout.exceptions.FunctionTimedOut as e:
                logger.error(f'Timeout on {client_name}')
                self.create_notification(f'Timeout for \'{client_name}\' client on {self.plugin_unique_name}'
                                         f' while fetching {entity_type.value}', repr(e))
                raise adapter_exceptions.AdapterException(f'Fetching has timed out')
            except Exception as e:
                logger.exception(f'Unknown error for {client_name} on {self.plugin_unique_name}: {repr(e)}')
                raise
            else:
                data_list = {'raw': raw_data,
                             'parsed': parsed_data}

                yield (client_name, data_list)

    @abstractmethod
    def _clients_schema(self):
        """
        To be implemented by inheritors
        Represents the set of keys the plugin expects from clients config

        :return: JSON Schema to, check out https://jsonschema.net/#/editor
        """

    def _route_parse_raw_data(self):
        if self.is_in_mock_mode:
            return self.__adapter_mock.mock_parse_raw_data
        return self._parse_raw_data

    # pylint: disable=R0201
    def _parse_raw_data(self, devices_raw_data) -> Iterable[DeviceAdapter]:
        """
        To be implemented by inheritors
        Will convert 'raw data' of one device (as the inheritor pleases to refer to it) to 'parsed'

        :param devices_raw_data: raw data as received by /devices/client, i.e. without the client->data association
        :return: parsed data as iterable Device collection
        """
        return []

    def _correlation_cmds(self):
        """
        To be implemented by inheritors, otherwise leave empty.
        Returns dict between OS type and shell, e.g.
        {
            'Linux': 'curl http://169.254.169.254/latest/meta-data/instance-id',
            'Windows': 'powershell -Command \'& Invoke-RestMethod -uri http://.../latest/meta-data/instance-id\""
        }
        :return: shell commands that help collerations
        """
        return {}

    # pylint: enable=R0201

    # pylint: disable=R0201
    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        To be implemented by inheritors, otherwise leave empty.
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        raise adapter_exceptions.AdapterException('Not Supported')

    # pylint: enable=R0201

    def _get_clients_config(self):
        """Returning the data inside 'clients' Collection on <plugin_unique_name> db.
        """
        clients = self._clients_collection.find()
        for client in clients:
            client_config = client.get('client_config')
            if client_config:
                self._decrypt_client_config(client_config)
            yield client

    def _get_client_config_by_client_id(self, client_id: str):
        """Returning the data inside 'clients' Collection on <plugin_unique_name> db.
        """
        current_client = self._clients_collection.find_one({'client_id': client_id})
        if not current_client or not current_client.get('client_config'):
            # No credentials to attempt reconnection
            raise adapter_exceptions.CredentialErrorException(f'No credentials found for client {client_id} in the db.')
        client_config = current_client['client_config']
        self._decrypt_client_config(client_config)
        self._clean_unneeded_client_config_fields(client_config)
        return self._normalize_password_fields(client_config)

    def _update_clients_schema_in_db(self, schema):
        """
        Every adapter has to update the DB about the scheme it expects for its clients.
        This logic is ran when the adapter starts
        :return:
        """
        self.plugin_settings.adapter_client_schema = schema

    def _create_axonius_entity(self, client_name, data, entity_type: EntityType,
                               plugin_identity: Tuple[str, str, str]):
        """
        See doc for super class
        """
        if entity_type == EntityType.Devices:
            if not data.get('adapter_properties'):
                data['adapter_properties'] = [x.name for x in self.adapter_properties()]

        parsed_to_insert = super()._create_axonius_entity(client_name, data, entity_type, plugin_identity)
        return parsed_to_insert

    @property
    def plugin_type(self):
        return adapter_consts.ADAPTER_PLUGIN_TYPE

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.AdapterBase

    def __get_last_cycle_start_time(self) -> datetime:
        try:
            state_response = self.request_remote_plugin('state', SYSTEM_SCHEDULER_PLUGIN_NAME)
            if state_response.status_code != 200:
                raise RuntimeError(f'Error fetching status of system scheduler. Reason: {state_response.text}')

            state_response = state_response.json()
            return parse_date(state_response['last_start_time'])
        except Exception:
            logger.exception(f'Failed getting cycle last_start_time')
            raise

    def __device_time_cutoff(self) -> Tuple[datetime, datetime]:
        """
        Gets a cutoff date (last_seen, last_fetched) that represents the oldest a device can be
        until it is considered 'old'
        """
        now = datetime.now(timezone.utc)
        return (now - self._last_seen_timedelta if self._last_seen_timedelta else None,
                now - self._last_fetched_timedelta if self._last_fetched_timedelta else None)

    def __user_time_cutoff(self) -> Tuple[datetime, datetime]:
        """
        Gets a cutoff date (last_seen, last_fetched) that represents the oldest a device can be
        until it is considered 'old'
        """
        now = datetime.now(timezone.utc)
        return (now - self.__user_last_seen_timedelta if self.__user_last_seen_timedelta else None,
                now - self.__user_last_fetched_timedelta if self.__user_last_fetched_timedelta else None)

    def log_if_not_realtime(self, *args, **kwargs):
        """
        :param args: same arguments as passed to logger.log
        :param kwargs: same arguments as passed to logger.log
        """
        if not self.__is_realtime:
            logger.log(*args, **kwargs)

    @classmethod
    @abstractmethod
    def adapter_properties(cls) -> List[AdapterProperty]:
        """
        Returns a list of all properties of the adapter, they will be displayed in GUI
        """

    @classmethod
    def _db_config_schema(cls) -> dict:
        schema = {
            'items': [
                {
                    'name': 'last_seen_threshold_hours',
                    'title': 'Ignore devices that have not been seen by the source in the last X hours',
                    'type': 'number',
                },
                {
                    'name': 'last_fetched_threshold_hours',
                    'title': 'Delete devices that have not been returned from the source in the last X hours',
                    'type': 'number',
                },
                {
                    'name': 'user_last_seen_threshold_hours',
                    'title': 'Ignore users that have not been seen by the source in the last X hours',
                    'type': 'number',
                },
                {
                    'name': 'user_last_fetched_threshold_hours',
                    'title': 'Delete users that have not been returned from the source in the last X hours',
                    'type': 'number',
                },
                {
                    'name': 'minimum_time_until_next_fetch',
                    'title': 'Override the global discovery schedule for this adapter to wait X hours before fetching',
                    'type': 'number',
                },
                {
                    'name': 'connect_client_timeout',
                    'title': 'Wait for a connection to the source for up to X seconds',
                    'type': 'number',
                },
                {
                    'name': 'fetching_timeout',
                    'title': 'Wait for a response from the source for up to X seconds',
                    'type': 'number',
                },
                {
                    'name': 'last_seen_prioritized',
                    'title': 'Ignore matching assets from the source if a subsequent asset was seen by the source '
                             'before the previously fetched asset',
                    'type': 'bool',
                },
                {
                    'name': 'realtime_adapter',
                    'title': 'Enable real-time adapter (Ignores all discovery cycle settings and continuously '
                             'repeats fetches from the source)',
                    'type': 'bool',
                }
            ],
            'required': [
                'last_seen_prioritized',
                'realtime_adapter'
            ],
            'pretty_name': 'Adapter Configuration',
            'type': 'array'
        }
        if cls.feature_flags_config(cls.Instance).get(FeatureFlagsNames.EnableSaaS, False):
            schema['items'].append({
                'name': 'connect_via_tunnel',
                'title': 'Use Tunnel to connect to source',
                'type': 'bool',
            })
            schema['required'].append('connect_via_tunnel')
        return schema

    @classmethod
    def _db_config_default(cls):
        default_schema = \
            {
                'last_seen_threshold_hours': cls.DEFAULT_LAST_SEEN_THRESHOLD_HOURS,
                'last_fetched_threshold_hours': cls.DEFAULT_LAST_FETCHED_THRESHOLD_HOURS,
                'user_last_seen_threshold_hours': cls.DEFAULT_USER_LAST_SEEN,
                'user_last_fetched_threshold_hours': cls.DEFAULT_USER_LAST_FETCHED,
                'minimum_time_until_next_fetch': cls.DEFAULT_MINIMUM_TIME_UNTIL_NEXT_FETCH,
                'connect_client_timeout': cls.DEFAULT_CONNECT_CLIENT_TIMEOUT,
                'fetching_timeout': cls.DEFAULT_FETCHING_TIMEOUT,
                'last_seen_prioritized': cls.DEFAULT_LAST_SEEN_PRIORITIZED,
                'realtime_adapter': False
            }
        if cls.feature_flags_config(cls.Instance).get(FeatureFlagsNames.EnableSaaS, False):
            default_schema['connect_via_tunnel'] = False
        return default_schema

    @classmethod
    def _discovery_schema(cls) -> dict:

        return {
            'items': [
                {
                    'name': ENABLE_CUSTOM_DISCOVERY,
                    'title': 'Enable custom discovery schedule',
                    'type': 'bool'
                },
                {
                    'name': DISCOVERY_RESEARCH_DATE_TIME,
                    'title': 'Scheduled discovery time',
                    'type': 'string',
                    'format': 'time'
                },
                {
                    'name': DISCOVERY_REPEAT_TYPE,
                    'title': 'Repeat scheduled discovery',
                    'enum': [
                        {
                            'name': DISCOVERY_REPEAT_EVERY,
                            'title': 'Every x days'
                        },
                        {
                            'name': DISCOVERY_REPEAT_ON,
                            'title': 'Days of week'
                        }
                    ],
                    'type': 'string'
                },
                {
                    'name': DISCOVERY_REPEAT_EVERY,
                    'title': 'Repeat scheduled discovery every (days)',
                    'type': 'number'
                },
                {
                    'name': DISCOVERY_REPEAT_ON,
                    'title': 'Repeat scheduled discovery on',
                    'type': 'array',
                    'items': [{'name': day.lower(), 'title': day, 'type': 'bool'} for day in WEEKDAYS],
                    'required': [day.lower() for day in WEEKDAYS]
                }
            ],
            'pretty_name': 'Discovery Configuration',
            'required': [ENABLE_CUSTOM_DISCOVERY, DISCOVERY_RESEARCH_DATE_TIME, DISCOVERY_REPEAT_TYPE,
                         DISCOVERY_REPEAT_EVERY, DISCOVERY_REPEAT_ON],
            'type': 'array'
        }

    @classmethod
    def _discovery_schema_default(cls) -> dict:
        return {
            ENABLE_CUSTOM_DISCOVERY: False,
            DISCOVERY_RESEARCH_DATE_TIME: '13:00',
            DISCOVERY_REPEAT_TYPE: DISCOVERY_REPEAT_EVERY,
            DISCOVERY_REPEAT_EVERY: 1,
            DISCOVERY_REPEAT_ON: {
                day.lower(): True for day in WEEKDAYS
            }
        }

    def _update_discovery_schema(self):
        self.update_schema(DISCOVERY_CONFIG_NAME, self._discovery_schema(), self._discovery_schema_default())

    def _log_activity_connection_failure(self, client_id: str, connection_exception: Exception):
        """
        audit logger for ConnectionException base events
        i.e , connection timeout, dns resolve, ssl errors
        :param client_id: adapter client connection id
        :param connection_exception: <T extend ConnectionException >
        """
        try:
            if isinstance(connection_exception.__context__, (adapter_exceptions.ClientConnectionException,
                                                             request.ConnectTimeout)):
                error_msg = str(connection_exception.__context__).strip()
                error = error_msg[len('Error:'):] if error_msg.startswith('Error:') else error_msg
            elif isinstance(connection_exception.__context__, requests.exceptions.SSLError):
                error = str(connection_exception).split('SSLError')[-1]
            else:
                error = 'fatal error during client connection'

        except Exception:
            error = 'fatal error during client connection'

        self.log_activity(AuditCategory.Adapters, AuditAction.Failure, {
            'adapter': self.plugin_name,
            'client_id': client_id,
            'error': error
        }, AuditType.Error)

    def _log_activity_adapters_cleanup(self, asset: EntityType, plugin_name: str, entity_cleaned: int):
        if not entity_cleaned:
            logger.info(f'Skipping audit of empty Clean adapter {plugin_name} for entity {asset.value}')
        else:
            self.log_activity(AuditCategory.Adapters, AuditAction.Clean, {
                'asset': asset.value,
                'adapter': self.plugin_name,
                ACTIVITY_PARAMS_COUNT: str(entity_cleaned)
            })

    def _log_activity_adapter_client_fetch_start(self, client_name: str):
        """
        log audit for adapter client fetch start
        """
        try:
            self.log_activity(AuditCategory.Adapters, AuditAction.Start, {
                'adapter': self.plugin_name,
                'client_id': client_name or ''
            })

        except Exception:
            logger.exception(f'Error logging audit for client name {client_name}')

    def _log_activity_adapter_client_fetch_summary(self, client_name: str, fetch_start_time: datetime,
                                                   users_count: int = 0, devices_count: int = 0):
        """
        log audit for adapter client fetch ( devices and users ) summary
        """
        try:
            duration = str(datetime.utcnow() - fetch_start_time).split('.')[0]
            self.log_activity(AuditCategory.Adapters, AuditAction.Complete, {
                'adapter': self.plugin_name,
                'client_id': client_name or '',
                'users_count': str(users_count),
                'devices_count': str(devices_count),
                'duration': duration
            })

        except Exception:
            logger.exception(f'Error logging audit for client name {client_name}')
