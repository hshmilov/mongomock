"""
AggregatorPlugin.py: A Plugin for the devices aggregation process
"""
from datetime import datetime
from itertools import groupby
import concurrent.futures

import pymongo
import requests
import threading
import uuid

from aggregator.exceptions import AdapterOffline, ClientsUnavailable
from axonius.adapter_base import is_plugin_adapter
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.parsing_utils import get_device_id_for_plugin_name
from axonius.mixins.triggerable import Triggerable
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, AGGREGATOR_PLUGIN_NAME, SYSTEM_SCHEDULER_PLUGIN_NAME
from axonius.threading_utils import LazyMultiLocker
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


def _is_tag_valid(tag):
    """
    A valid tag is a tag that has a `name` and `type` and they are both string
    """
    return isinstance(tag.get('name'), str) and isinstance(tag.get('type'), str)


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
        self.aggregator_db_connection = self._get_db_connection(True)[self.plugin_unique_name]
        self.insert_views()

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

        for create, view_on in [("devices_db_view", "devices_db"), ("users_db_view", "users_db")]:
            try:
                self.aggregator_db_connection.command({
                    "create": create,
                    "viewOn": view_on,
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
            self.logger.exception(f"{repr(e)}")
            raise AdapterOffline()
        if 'status' in clients and 'message' in clients:
            self.logger.error(
                f'Request for clients from {adapter} failed. Status: {clients.get("status", "")}, Message \'{clients.get("message", "")}\'')
            raise ClientsUnavailable()
        for client_name in clients:
            try:
                data = self.request_remote_plugin(f'insert_to_db?client_name={client_name}', adapter, method='PUT')
            except Exception as e:
                # request failed
                self.logger.exception(f"{repr(e)}")
                raise AdapterOffline()
            if data.status_code != 200:
                self.logger.warn(f"{client_name} client for adapter {adapter} is returned HTTP {data.status_code}. "
                                 f"Reason: {str(data.content)}")
                continue
            yield (client_name, from_json(data.content))

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
            self.logger.error(f"Error getting adapters from core. reason: "
                              f"{str(adapters.status_code)}, {str(adapters.content)}")
            return return_error('Could not fetch adapters', 500)

        adapters = adapters.json()

        if job_name != 'fetch_filtered_adapters':
            adapters = [adapter for adapter in adapters.values()
                        if adapter[PLUGIN_UNIQUE_NAME] == job_name]
        else:
            adapters = _filter_adapters_by_parameter(post_json, adapters)

        self.logger.debug("registered adapters = {}".format(adapters))

        return self._fetch_data_from_adapters(job_name, adapters)

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
                            self._save_data_from_adapter, adapter[PLUGIN_UNIQUE_NAME])] = adapter['plugin_name']

                    for future in concurrent.futures.as_completed(futures_for_adapter):
                        try:
                            num_of_adapters_to_fetch -= 1
                            future.result()
                            # notify the portion of adapters left to fetch, out of total required
                            self._notify_adapter_fetch_devices_finished(
                                futures_for_adapter[future], num_of_adapters_to_fetch / len(current_adapters))
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

        if association_type not in ['Tag', 'Multitag', 'Link', 'Unlink']:
            return return_error("Acceptable values for association_type are: 'Tag', 'Multitag', 'Link', 'Unlink'", 400)
        if not isinstance(associated_adapter_devices, list):
            return return_error("associated_adapter_devices must be a list", 400)

        if association_type == 'Tag':
            if len(associated_adapter_devices) != 1:
                return return_error("Tag must only be associated with a single adapter_device")
            if not _is_tag_valid(sent_plugin):
                return return_error("tag name and type must be provided as a string")

        if association_type == 'Multitag':
            if not isinstance(sent_plugin.get('tags'), list):
                return return_error("A multitag must have a list of tags in 'tags'")
            if any(not _is_tag_valid(tag) for tag in sent_plugin['tags']):
                return return_error("All tags in 'tags' must be valid tags, "
                                    "such as they have 'name' and 'type' as string")

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

            if len(axonius_device_candidates) == 0:
                return return_error("No devices given or all devices given don't exist")

            if association_type == 'Tag':
                if len(axonius_device_candidates) != 1:
                    # it has been checked that at most 1 device was provided (if len(associated_adapter_devices) != 1)
                    # then if it's not 1, its definitely 0
                    return return_error(
                        "A tag must be associated with just one adapter device, the device provided is unavailable")

                # take (assumed single) key from candidates
                self._update_device_with_tag(sent_plugin, axonius_device_candidates[0])
            elif association_type == 'Multitag':
                for device in axonius_device_candidates:
                    # here we tag all adapter_devices per axonius device candidate
                    new_sent_plugin = dict(sent_plugin)
                    del new_sent_plugin['tags']
                    new_sent_plugin['associated_adapter_devices'] = [
                        (adapter_device[PLUGIN_UNIQUE_NAME], adapter_device['data']['id'])
                        for adapter_device in device['adapters']
                    ]
                    for tag in sent_plugin['tags']:
                        self._update_device_with_tag({**new_sent_plugin, **tag}, device)
            elif association_type == 'Link':
                # in this case, we need to link (i.e. "merge") all axonius_device_candidates
                # if there's only one, then the link is either associated only to
                # one device (which is as irrelevant as it gets)
                # or all the devices are already linked. In any case, if a real merge isn't done
                # it means someone made a mistake.
                if len(axonius_device_candidates) < 2:
                    return return_error(f"Got a 'Link' with only {len(axonius_device_candidates)} candidates",
                                        400)

                self._link_devices(axonius_device_candidates)
            elif association_type == 'Unlink':
                if len(axonius_device_candidates) != 1:
                    return return_error(
                        "All associated_adapter_devices in an unlink operation must be from the same Axonius "
                        "device, in your case, they're from "
                        f"{len(axonius_device_candidates)} devices.")
                axonius_device_to_split = axonius_device_candidates[0]

                if len(axonius_device_to_split['adapters']) == len(associated_adapter_devices):
                    return return_error("You can't remove all devices from an AxoniusDevice, that'll be unfair.")

                self.__unlink_devices(associated_adapter_devices, axonius_device_to_split)

        # raw == parsed for plugin_data
        self._save_parsed_in_db(sent_plugin, db_type='raw')
        self._save_parsed_in_db(sent_plugin)  # save in parsed too

        return ""

    def __unlink_devices(self, associated_adapter_devices, axonius_device_to_split):
        """
        Unlinks the associated_adapter_devices from axonius_device_to_split
        """
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

    def _link_devices(self, axonius_device_candidates):
        """
        Link all given axonius devices, assuming 2 are given
        """
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

    def _save_data_from_adapter(self, adapter_unique_name):
        """
        Requests from the given adapter to insert its devices into the DB.
        :param str adapter_unique_name: The unique name of the adapter
        """

        self.logger.info(f"Starting to fetch device for {adapter_unique_name}")
        try:
            data = self._request_insertion_from_adapters(adapter_unique_name)
            for client_name, devices_per_client in data:
                self.logger.info(f"Got {devices_per_client} for client {client_name} in {adapter_unique_name}")

        except (AdapterOffline, ClientsUnavailable) as e:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            self.logger.warn(f"adapter {adapter_unique_name} might be offline. Reason {str(e)}")
        except Exception as e:
            self.logger.exception("Thread {0} encountered error: {1}".format(threading.current_thread(), str(e)))
            raise

        self.logger.info(f"Finished for {adapter_unique_name}")

    def _save_parsed_in_db(self, device, db_type='parsed'):
        """
        Save axonius device in DB
        :param device: AxoniusDevice or device list
        :param db_type: 'parsed' or 'raw
        :return: None
        """
        self.aggregator_db_connection[db_type].insert_one(device)

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

    def _notify_adapter_fetch_devices_finished(self, adapter_name, portion_of_adapters_left):
        self.request_remote_plugin('sub_phase_update', SYSTEM_SCHEDULER_PLUGIN_NAME, 'POST', json={
            'adapter_name': adapter_name, 'portion_of_adapters_left': portion_of_adapters_left})
