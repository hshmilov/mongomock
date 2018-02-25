"""
AggregatorPlugin.py: A Plugin for the devices aggregation process
"""
import functools
from datetime import datetime, timedelta
from itertools import groupby
import concurrent.futures

from promise import Promise
import pymongo
import requests
import threading
import uuid

from aggregator.exceptions import AdapterOffline, ClientsUnavailable
from axonius.adapter_base import is_plugin_adapter
from axonius.consts.adapter_consts import IGNORE_DEVICE
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.parsing_utils import get_device_id_for_plugin_name
from axonius.mixins.triggerable import Triggerable
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, AGGREGATOR_PLUGIN_NAME, SYSTEM_SCHEDULER_PLUGIN_NAME
from axonius.threading_utils import LazyMultiLocker, run_in_executor_helper
from axonius.utils.files import get_local_config_file
from axonius.utils.json import from_json

get_devices_job_name = "Get device job"


def get_unique_name_from_plugin_unique_name_and_id(unique_plugin_name, _id):
    return f"{unique_plugin_name}{_id}"


def get_unique_name_from_device(parsed_data) -> str:
    """
    Returns a string that UUIDs a parsed adapter device
    :param parsed_data: parsed adapter device
    :return:
    """
    return get_unique_name_from_plugin_unique_name_and_id(parsed_data[PLUGIN_UNIQUE_NAME], parsed_data['data']['id'])


class AggregatorService(PluginBase, Triggerable):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=AGGREGATOR_PLUGIN_NAME, *args, **kwargs)

        self._index_lock = threading.RLock()
        self._index = 0

        # Lock object for the global device list
        self.device_db_lock = LazyMultiLocker()

        # An executor dedicated to inserting devices to the DB
        self.__device_inserter = concurrent.futures.ThreadPoolExecutor(max_workers=200)

        # Setting up db
        self.devices_db_connection = self._get_db_connection(True)[self.plugin_unique_name]
        self.insert_views()
        self.devices_db_actual_collection = self.devices_db_connection['devices_db']
        self.devices_db_view = self.devices_db_connection['devices_db_view']

        # insertion and link/unlink lock
        self.fetch_lock = {}

        self._activate('fetch_filtered_adapters')

        self._default_activity = True

    def insert_views(self):
        """
        Insert useful views.
        :return: None
        """

        # The following creates a view that has all adapters and tags
        # of type "adapterdata" inside one (unsorted!) array.

        try:
            self.devices_db_connection.command({
                "create": "devices_db_view",
                "viewOn": "devices_db",
                "pipeline": [
                    {'$project': {'internal_axon_id': 1,
                                  'generic_data':
                                      {'$filter': {'input': '$tags', 'as': 'tag',
                                                   'cond': {'$eq': ['$$tag.type', 'data']}}},
                                  'specific_data':
                                      {'$concatArrays': ['$adapters',
                                                         {'$filter': {'input': '$tags', 'as': 'tag', 'cond':
                                                                      {'$eq': ['$$tag.type', 'adapterdata']}}}]},
                                  'adapters': '$adapters.plugin_name',
                                  'labels': {'$filter': {'input': '$tags', 'as': 'tag', 'cond':
                                                         {'$and': [{'$eq': ['$$tag.type', 'label']},
                                                                   {'$eq': ['$$tag.data', True]}]}
                                                         }
                                             }
                                  }
                     },
                    {'$project': {'internal_axon_id': 1, 'generic_data': 1, 'adapters': 1, 'labels': '$labels.name',
                                  'adapters_data': {'$map': {'input': '$specific_data', 'as': 'data', 'in': {
                                      '$arrayToObject': {'$concatArrays': [[], [{'k': '$$data.plugin_name',
                                                                                 'v': '$$data.data'}]]}}}},
                                  'specific_data': 1}
                     }
                ]
            })
        except pymongo.errors.OperationFailure as e:
            if "already exists" not in str(e):
                raise

    @property
    def devices_db(self):
        """
        We override devices_db of pluginbase to be more efficient.
        :return: A mongodb collection.
        """

        return self.devices_db_actual_collection

    def _get_devices_data(self, adapter):
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
            self.logger.exception(f"{repr(e)}")
            raise AdapterOffline()
        if 'status' in clients and 'message' in clients:
            self.logger.error(
                f'Request for clients from {adapter} failed. Status: {clients.get("status", "")}, Message \'{clients.get("message", "")}\'')
            raise ClientsUnavailable()
        for client_name in clients:
            try:
                devices = self.request_remote_plugin(f'devices_by_name?name={client_name}', adapter)
            except Exception as e:
                # request failed
                self.logger.exception(f"{repr(e)}")
                raise AdapterOffline()
            if devices.status_code != 200:
                self.logger.warn(f"{client_name} client for adapter {adapter} is returned HTTP {devices.status_code}. "
                                 f"Reason: {str(devices.content)}")
                continue
            yield (client_name, from_json(devices.content))

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
            self.logger.error(f"Error getting devices from core. reason: "
                              f"{str(adapters.status_code)}, {str(adapters.content)}")
            return return_error('Could not fetch adapters', 500)

        adapters = adapters.json()

        if job_name != 'fetch_filtered_adapters':
            adapters = [adapter for adapter in adapters.values()
                        if adapter[PLUGIN_UNIQUE_NAME] == job_name]
        else:
            adapters = _filter_adapters_by_parameter(post_json, adapters)

        self.logger.debug("registered adapters = {}".format(adapters))

        return self._fetch_devices_from_adapters(job_name, adapters)

    def _fetch_devices_from_adapters(self, job_name, current_adapters=None):
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
                            self._save_devices_from_adapter, adapter['plugin_name'], adapter[PLUGIN_UNIQUE_NAME],
                            adapter['plugin_type'])] = adapter['plugin_name']

                    for future in concurrent.futures.as_completed(futures_for_adapter):
                        try:
                            num_of_adapters_to_fetch -= 1
                            future.result()
                            # notify_adapter_fetch_devices finished
                            self._notify_adapter_fetch_devices_finished(
                                futures_for_adapter[future], num_of_adapters_to_fetch)
                        except Exception as err:
                            self.logger.exception("An exception was raised while trying to get a result.")

                self.logger.info("Finished getting all device data.")

                return ''  # raw_detailed_devices

        except Exception as e:
            self.logger.exception('Getting devices from all requested adapters failed.')

    @add_rule("plugin_push", methods=["POST"])
    def save_data_from_plugin(self):
        """
        Digests 'Link', 'Unlink' and 'Tag' requests from plugin
        Link - links two or more adapter devices
        Unlink - unlinks exactly two adapter devices
        Tag - adds a tag to an adapter devices
        Refer to https://axonius.atlassian.net/wiki/spaces/AX/pages/86310913/Devices+DB+Correlation+Process for more
        :return:
        """
        sent_plugin = self.get_request_data_as_object()
        if sent_plugin is None:
            return return_error("Invalid data sent", 400)

        association_type = sent_plugin.get('association_type')
        associated_adapter_devices = sent_plugin.get('associated_adapter_devices')

        if association_type not in ['Tag', 'Link', 'Unlink']:
            return return_error("Acceptable values for association_type are: 'Tag', 'Link', 'Unlink'", 400)
        if not isinstance(associated_adapter_devices, list):
            return return_error("associated_adapter_devices must be a list", 400)

        if association_type == 'Tag':
            if len(associated_adapter_devices) != 1:
                return return_error("Tag must only be associated with a single adapter_device")
            if not isinstance(sent_plugin.get('name'), str) or not isinstance(sent_plugin.get('type'), str):
                return return_error("tag name and data must be provided as a string")

        # user doesn't send this
        sent_plugin['accurate_for_datetime'] = datetime.now()

        # we might not trust the sender on this
        sent_plugin[PLUGIN_UNIQUE_NAME], sent_plugin['plugin_name'] = self.get_caller_plugin_name()

        with self.device_db_lock.get_lock(
                [get_unique_name_from_plugin_unique_name_and_id(name, associated_id) for name, associated_id in
                 associated_adapter_devices]):
            # now let's update our db

            # figure out all axonius devices that at least one of its adapter_device are in the
            # given plugin's association
            axonius_device_candidates = list(self.devices_db.find({"$or": [
                {
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: associated_plugin_unique_name,
                            'data.id': associated_id
                        }
                    }
                }
                for associated_plugin_unique_name, associated_id in associated_adapter_devices
            ]}))
            if association_type == 'Tag':
                if len(axonius_device_candidates) != 1:
                    # it has been checked that at most 1 device was provided (if len(associated_adapter_devices) != 1)
                    # then if it's not 1, its definitely 0
                    return return_error(
                        "A tag must be associated with just one adapter device, the device provided is unavailable")

                # take (assumed single) key from candidates
                self._update_device_with_tag(sent_plugin, axonius_device_candidates[0])
            elif association_type == 'Link':
                # in this case, we need to link (i.e. "merge") all axonius_device_candidates
                # if there's only one, then the link is either associated only to
                # one device (which is as irrelevant as it gets)
                # or all the devices are already linked. In any case, if a real merge isn't done
                # it means someone made a mistake.
                if len(axonius_device_candidates) < 2:
                    return return_error(f"Got a 'Link' with only {len(axonius_device_candidates)} candidates",
                                        400)

                collected_adapter_devices = [axonius_device['adapters'] for axonius_device in axonius_device_candidates]

                all_unique_adapter_devices_data = [v for d in collected_adapter_devices for v in d]

                # Get all tags from all devices. If we have the same tag name and issuer, prefer the newest.
                # a tag is the same tag, if it has the same plugin_unique_name and name.
                def keyfunc(tag):
                    return tag['plugin_unique_name'], tag['name']

                # first, lets get all tags and have them sorted. This will make the same tags be consecutive.
                all_tags = sorted((t for dc in axonius_device_candidates for t in dc['tags']), key=keyfunc)

                # now we have the same tags ordered consecutively. so we want to group them, so that we
                # would have duplicates of the same tag in their identity key.
                all_tags = groupby(all_tags, keyfunc)

                # now we have them groupedby, lets select only the one which is the newest.
                tags_for_new_device = {tag_key: max(duplicated_tags, key=lambda tag: tag['accurate_for_datetime'])
                                       for tag_key, duplicated_tags
                                       in all_tags}

                internal_axon_id = uuid.uuid4().hex
                self.devices_db.insert_one({
                    "internal_axon_id": internal_axon_id,
                    "accurate_for_datetime": datetime.now(),
                    "adapters": all_unique_adapter_devices_data,
                    "tags": list(tags_for_new_device.values())  # Turn it to a list
                })

                # now, let us delete all other AxoniusDevices
                self.devices_db.delete_many({'$or':
                                             [
                                                 {'internal_axon_id': axonius_device['internal_axon_id']}
                                                 for axonius_device in axonius_device_candidates
                                             ]
                                             })
            elif association_type == 'Unlink':
                if len(axonius_device_candidates) != 1:
                    return return_error(
                        "All associated_adapter_devices in an unlink operation must be from the same Axonius "
                        "device, in your case, they're from "
                        f"{len(axonius_device_candidates)} devices.")
                axonius_device_to_split = axonius_device_candidates[0]

                if len(axonius_device_to_split['adapters']) == len(associated_adapter_devices):
                    return return_error("You can't remove all devices from an AxoniusDevice, that'll be unfair.")

                # we already tested that all adapter_devices in data_sent are indeed from the single
                # AxoniusDevice we found, so the ids will match, so we don't have to check that.
                # We're building a new AxoniusDevice that has all the associated_adapter_devices given from
                # the old axonius device, and at the same time deleting from the old device.

                internal_axon_id = uuid.uuid4().hex
                new_axonius_device = {
                    "internal_axon_id": internal_axon_id,
                    "accurate_for_datetime": datetime.now(),
                    "adapters": [],
                    "tags": []
                }

                for adapter_device in axonius_device_to_split['adapters']:
                    candidate = get_device_id_for_plugin_name(associated_adapter_devices,
                                                              adapter_device[PLUGIN_UNIQUE_NAME])
                    if candidate is not None and candidate == adapter_device['data']['id']:
                        new_axonius_device['adapters'].append(adapter_device)

                for tag in axonius_device_to_split['tags']:
                    (tag_plugin_unique_name, tag_adapter_id), = tag['associated_adapter_devices']
                    candidate = get_device_id_for_plugin_name(associated_adapter_devices, tag_plugin_unique_name)
                    if candidate is not None and candidate == tag_adapter_id:
                        new_axonius_device['tags'].append(tag)

                self.devices_db.insert_one(new_axonius_device)

                for adapter_to_remove_from_old in new_axonius_device['adapters']:
                    self.devices_db.update_many({'internal_axon_id': axonius_device_to_split['internal_axon_id']},
                                                {
                                                    "$pull": {
                                                        'adapters': {
                                                            PLUGIN_UNIQUE_NAME: adapter_to_remove_from_old[
                                                                PLUGIN_UNIQUE_NAME],
                                                        }
                                                    }
                    })

                for tag_to_remove_from_old in new_axonius_device['tags']:
                    (tag_plugin_unique_name,
                     tag_adapter_id), = tag_to_remove_from_old['associated_adapter_devices']
                    self.devices_db.update_many({'internal_axon_id': axonius_device_to_split['internal_axon_id']},
                                                {
                                                    "$pull": {
                                                        'tags': {
                                                            f'associated_adapter_devices.{tag_plugin_unique_name}': tag_adapter_id
                                                        }
                                                    }})

        # raw == parsed for plugin_data
        self._save_parsed_in_db(sent_plugin, db_type='raw')
        self._save_parsed_in_db(sent_plugin)  # save in parsed too

        return ""

    def _get_pretty_id(self):
        with self._index_lock:
            index = self._index
            self._index += 1
        return f'AX-{index}'

    def _save_devices_from_adapter(self, adapter_name, adapter_unique_name, plugin_type):
        """ Function for getting all devices from specific adapter periodically.

        This function should be called in a different thread. It will run forever and periodically get all devices
        From a wanted adapter and save it to the local general db, and the historical db.abs

        :param str adapter_name: The name of the adapter
        :param str adapter_unique_name: The name of the adapter (unique name)
        """

        def insert_device_to_db(device_to_update, parsed_to_insert):
            """
            Insert a device into the DB in a locked way
            :return:
            """
            # if `device_to_update` has a `correlates` field
            # then it's similar to a correlation, so we need to lock both devices
            lock_indexes = [get_unique_name_from_device(parsed_to_insert)]
            correlates = parsed_to_insert['data'].get('correlates')
            if correlates == IGNORE_DEVICE:
                # special case: this is a device we shouldn't handle
                self._save_parsed_in_db(parsed_to_insert, db_type='ignored_scanner_devices')
                return

            if correlates:
                # this is to support case B: see `find_correlation` in `scanner_adapter_base.py`
                lock_indexes.append(get_unique_name_from_plugin_unique_name_and_id(*correlates))

            with self.device_db_lock.get_lock(lock_indexes):
                # trying to update the device if it is already in the DB
                modified_count = self.devices_db.update_one({
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: parsed_to_insert[PLUGIN_UNIQUE_NAME],
                            'data.id': parsed_to_insert['data']['id']
                        }
                    }
                }, {"$set": device_to_update}).modified_count

                if modified_count == 0:
                    # if it's not in the db then,

                    if correlates:
                        # for scanner adapters this is case B - see "scanner_adapter_base.py"
                        # we need to add this device to the list of adapters in another device
                        correlate_plugin_unique_name, correlated_id = correlates
                        modified_count = self.devices_db.update_one({
                            'adapters': {
                                '$elemMatch': {
                                    PLUGIN_UNIQUE_NAME: correlate_plugin_unique_name,
                                    'data.id': correlated_id
                                }
                            }},
                            {
                                "$addToSet": {
                                    "adapters": parsed_to_insert
                                }
                        })
                        if modified_count == 0:
                            self.logger.error("No devices update for case B for scanner device "
                                              f"{parsed_to_insert['data']['id']} from "
                                              f"{parsed_to_insert[PLUGIN_UNIQUE_NAME]}")
                    else:
                        # this is regular first-seen device, make its own value
                        self.devices_db.insert_one({
                            "internal_axon_id": uuid.uuid4().hex,
                            "accurate_for_datetime": datetime.now(),
                            "adapters": [parsed_to_insert],
                            "tags": []
                        })

        self.logger.info(f"Starting to fetch device for {adapter_name} {adapter_unique_name}")
        promises = []
        try:
            devices = self._get_devices_data(adapter_unique_name)
            for client_name, devices_per_client in devices:
                time_before_client = datetime.now()
                # Saving the raw data on the historic db
                try:
                    self._save_data_in_history(devices_per_client['raw'],
                                               adapter_name,
                                               adapter_unique_name,
                                               plugin_type)
                except pymongo.errors.DocumentTooLarge:
                    # wanna see my "something too large"?
                    self.logger.warn(f"Got DocumentTooLarge for {adapter_unique_name} with client {client_name}.")

                # Here we have all the devices a single client sees
                for device in devices_per_client['parsed']:
                    device['pretty_id'] = self._get_pretty_id()
                    parsed_to_insert = {
                        'client_used': client_name,
                        'plugin_type': plugin_type,
                        'plugin_name': adapter_name,
                        PLUGIN_UNIQUE_NAME: adapter_unique_name,
                        'accurate_for_datetime': datetime.now(),
                        'data': device
                    }
                    device_to_update = {f"adapters.$.{key}": value
                                        for key, value in parsed_to_insert.items() if key != 'data'}

                    promises.append(Promise(functools.partial(run_in_executor_helper,
                                                              self.__device_inserter,
                                                              self._save_parsed_in_db,
                                                              args=[dict(parsed_to_insert)])))

                    fields_to_update = device.keys() - ['id']
                    for field in fields_to_update:
                        field_of_device = device.get(field, [])
                        try:
                            if type(field_of_device) in [list, dict, str] and len(field_of_device) == 0:
                                # We don't want to insert empty values, only one that has a valid data
                                continue
                            else:
                                device_to_update[f"adapters.$.data.{field}"] = field_of_device
                        except TypeError:
                            self.logger.error(f"Got TypeError while getting field {field}")
                            continue
                    device_to_update['accurate_for_datetime'] = datetime.now()

                    promises.append(Promise(functools.partial(run_in_executor_helper,
                                                              self.__device_inserter,
                                                              insert_device_to_db,
                                                              args=[device_to_update, parsed_to_insert])))
                devices_count = len(promises)
                promise_all = Promise.all(promises)
                Promise.wait(promise_all, timedelta(minutes=5).total_seconds())
                promises = []
                if promise_all.is_rejected:
                    self.logger.error("Error in insertion to DB", exc_info=promise_all.reason)
                time_for_client = datetime.now() - time_before_client
                self.logger.info(
                    f"Finished aggregating for client {client_name} from adapter {adapter_unique_name},"
                    f" aggregation took {time_for_client.seconds} seconds and returned {devices_count}.")

        except (AdapterOffline, ClientsUnavailable) as e:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            self.logger.warn(f"adapter {adapter_unique_name} might be offline. Reason {str(e)}")
        except Exception as e:
            self.logger.exception("Thread {0} encountered error: {1}".format(threading.current_thread(), str(e)))
            raise

        self.logger.info("Finished for {} {}".format(adapter_name, adapter_unique_name))
        return ''

    def _save_parsed_in_db(self, device, db_type='parsed'):
        """
        Save axonius device in DB
        :param device: AxoniusDevice or device list
        :param db_type: 'parsed' or 'raw
        :return: None
        """
        self.devices_db_connection[db_type].insert_one(device)

    def _save_data_in_history(self, device, plugin_name, plugin_unique_name, plugin_type):
        """ Function for saving raw data in history.

        This function will save the data on mongodb. the db name is 'devices' and the collection is 'raw' always!

        :param device: The raw data of the current device
        :param str plugin_name: The name of the plugin
        :param str plugin_unique_name: The unique name of the plugin
        :param str plugin_type: The type of the plugin
        """
        try:
            self.devices_db_connection['raw'].insert_one({'raw': device,
                                                          'plugin_name': plugin_name,
                                                          PLUGIN_UNIQUE_NAME: plugin_unique_name,
                                                          'plugin_type': plugin_type})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception("Error in pymongo. details: {}".format(e))

    def _update_device_with_tag(self, tag, axonius_device):
        """
        Updates the devices db to either add or update the given tag
        :param tag: tag from user
        :param axonius_device: axonius device from db
        :return: None
        """

        if any((x['name'] == tag['name'] and x['plugin_unique_name'] == tag['plugin_unique_name'])
               for x in axonius_device['tags']):
            self.devices_db.update_one({
                "internal_axon_id": axonius_device['internal_axon_id'],
                "tags": {
                    "$elemMatch":
                        {
                            "name": tag['name'],
                            "plugin_unique_name": tag['plugin_unique_name']
                        }
                }
            }, {
                "$set": {
                    "tags.$": tag
                }
            })
        else:
            self.devices_db.update_one({
                "internal_axon_id": axonius_device['internal_axon_id'],
            }, {
                "$addToSet": {
                    "tags": tag
                }
            })

    @property
    def plugin_subtype(self):
        return "Core"

    def _notify_adapter_fetch_devices_finished(self, adapter_name, num_of_adapters_left):
        self.request_remote_plugin('sub_phase_update', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json={
                                   'adapter_name': adapter_name, 'num_of_adapters_left': num_of_adapters_left})
