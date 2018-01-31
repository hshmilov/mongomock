"""
AggregatorPlugin.py: A Plugin for the devices aggregation process
"""
import functools
import requests
import threading
import pymongo
from datetime import datetime, timedelta
import uuid
from itertools import chain, groupby
from dateutil.parser import parse as dateparse

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from concurrent.futures import ThreadPoolExecutor

from promise import Promise

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.adapter_consts import DEVICE_SAMPLE_RATE
from axonius.device import LAST_SEEN_FIELD
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.parsing_utils import beautiful_adapter_device_name
from axonius.mixins.activatable import Activatable
from axonius.mixins.triggerable import Triggerable
from aggregator_exceptions import AdapterOffline, ClientsUnavailable
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, AGGREGATOR_PLUGIN_NAME
from axonius.threading_utils import MultiLockerLazy, run_in_executor_helper

get_devices_job_name = "Get device job"


def parsed_devices_match(first, second):
    """
    Whether or not two adapter devices (i.e. a single device as viewed by an adapter) match
    :param first: first adapter device to check
    :param second: second adapter device to check
    :return: bool
    """
    return first[PLUGIN_UNIQUE_NAME] == second[PLUGIN_UNIQUE_NAME] and \
        first['data']['id'] == second['data']['id']


def parsed_device_match_plugin(plugin_data, parsed_device):
    """
    Whether or not a plugin is referring a specific adapter device
    :param plugin_data: the plugin data
    :param parsed_device: a adapter device
    :return: bool
    """
    return plugin_data['associated_adapter_devices']. \
        get(parsed_device[PLUGIN_UNIQUE_NAME]) == parsed_device['data']['id']


def get_unique_name_from_plugin_unique_name_and_id(unique_plugin_name, _id):
    return f"{unique_plugin_name}{_id}"


def get_unique_name_from_device(parsed_data) -> str:
    """
    Returns a string that UUIDs a parsed adapter device
    :param parsed_data: parsed adapter device
    :return:
    """
    return get_unique_name_from_plugin_unique_name_and_id(parsed_data[PLUGIN_UNIQUE_NAME], parsed_data['data']['id'])


class AggregatorPlugin(PluginBase, Activatable, Triggerable):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(requested_unique_plugin_name=AGGREGATOR_PLUGIN_NAME, *args, **kwargs)

        # Lock object for the global device list
        self.device_db_lock = MultiLockerLazy()

        # An executor dedicated to inserting devices to the DB
        self.__device_inserter = ThreadPoolExecutor(max_workers=200)

        # Open connection to the adapters db
        self.devices_db_connection = self._get_db_connection(True)[self.plugin_unique_name]
        self.devices_db = self.devices_db_connection['devices_db']

        # Scheduler for querying core for online adapters and querying the adapters themselves
        self._online_adapters_scheduler = None

        # insertion and link/unlink lock
        self.thread_manager_lock = threading.RLock()

        # Starting the managing thread
        self.start_activatable()

    def _start_activatable(self):
        assert self._online_adapters_scheduler is None, "Aggregator thinks we're already running but still got a " \
                                                        "/start request "

        executors = {'default': ThreadPoolExecutorApscheduler(10)}
        self._online_adapters_scheduler = LoggedBackgroundScheduler(self.logger, executors=executors)
        self._online_adapters_scheduler.add_job(func=self._adapters_thread_manager,
                                                trigger=IntervalTrigger(seconds=60),
                                                next_run_time=datetime.now(),
                                                name='adapters_thread_manager',
                                                id='adapters_thread_manager',
                                                max_instances=1)
        self._online_adapters_scheduler.start()

    def _stop_activatable(self):
        assert self._online_adapters_scheduler is not None, "Aggregator thinks we're not running but still got a " \
                                                            "/stop request "

        self._online_adapters_scheduler.remove_all_jobs()
        self._online_adapters_scheduler.shutdown(wait=True)
        self._online_adapters_scheduler = None

    def _is_work_in_progress(self) -> bool:
        assert self._online_adapters_scheduler is not None, "Aggregator isn't running"

        # if device_db_lock is taken, it means we're fetching devices
        if self.device_db_lock.is_any_locked():
            return True

        # if thread_manager_lock is taken, it means we're fetching adapters
        if self.thread_manager_lock.acquire(False):
            self.thread_manager_lock.release()
        else:
            return True

        return False

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
            yield (client_name, devices.json())

    def _triggered(self, job_name, post_json, *args):
        current_adapters = requests.get(self.core_address + '/register')

        assert current_adapters.status_code == 200, "Error getting devices from core. reason:" + \
                                                    f"{str(current_adapters.status_code)}, " + \
                                                    str(current_adapters.content)

        adapter = next((adapter for adapter in current_adapters.json().values()
                        if adapter[PLUGIN_UNIQUE_NAME] == job_name), None)
        if adapter is None:
            raise RuntimeError(f"Can't find plugin named {job_name}")
        self._save_devices_from_adapter(adapter['plugin_name'], adapter[PLUGIN_UNIQUE_NAME])

    def _adapters_thread_manager(self):
        """ Function for monitoring other threads activity.

        This function should run in a different thread. It runs forever and monitors the other collector threads.
        If a new adapter will register, this function will create a new thread for him.
        Currently the sampling rate is hard coded for 60 seconds.
        """
        try:
            with self.thread_manager_lock:
                current_adapters = requests.get(self.core_address + '/register')

                if current_adapters.status_code != 200:
                    self.logger.error(f"Error getting devices from core. reason: "
                                      f"{str(current_adapters.status_code)}, {str(current_adapters.content)}")

                    return

                current_adapters = current_adapters.json()

                self.logger.debug("registered adapters = {}".format(current_adapters))

                # let's add jobs for all adapters
                for adapter_name, adapter in current_adapters.items():
                    if adapter['plugin_type'] != "Adapter":
                        # This is not an adapter, not running
                        continue

                    if self._online_adapters_scheduler.get_job(adapter_name):
                        # We already have a running thread for this adapter
                        continue

                    sample_rate = int(adapter[DEVICE_SAMPLE_RATE])

                    self._online_adapters_scheduler.add_job(func=self._save_devices_from_adapter,
                                                            trigger=IntervalTrigger(seconds=sample_rate),
                                                            next_run_time=datetime.now(),
                                                            kwargs={PLUGIN_UNIQUE_NAME: adapter[PLUGIN_UNIQUE_NAME],
                                                                    'plugin_name': adapter['plugin_name']},
                                                            name=get_devices_job_name,
                                                            id=adapter_name,
                                                            max_instances=1)

                for job in self._online_adapters_scheduler.get_jobs():
                    if job.id not in current_adapters and job.name == get_devices_job_name:
                        # this means that the adapter has disconnected, so we stop fetching it
                        job.remove()

        except Exception as e:
            self.logger.critical('Managing thread got exception, '
                                 'must restart aggregator manually. Exception: {0}'.format(str(e)))

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
        if not isinstance(associated_adapter_devices, dict):
            return return_error("associated_adapter_devices must be a dict", 400)

        if association_type == 'Tag':
            if len(associated_adapter_devices) != 1:
                return return_error("Tag must only be associated with a single adapter_device")
            tagname = sent_plugin.get('tagname')
            if not isinstance(tagname, str):
                return return_error("tagname must be provided as a string")

        # user doesn't send this
        sent_plugin['accurate_for_datetime'] = datetime.now()

        # we might not trust the sender on this
        sent_plugin[PLUGIN_UNIQUE_NAME], sent_plugin['plugin_name'] = self.get_caller_plugin_name()

        with self.device_db_lock.get_lock(
                [get_unique_name_from_plugin_unique_name_and_id(name, associated_id) for name, associated_id in
                 associated_adapter_devices.items()]):
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
                for associated_plugin_unique_name, associated_id in associated_adapter_devices.items()
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

                all_plugin_unique_names = [v[PLUGIN_UNIQUE_NAME] for d in collected_adapter_devices for v in d]

                if len(set(all_plugin_unique_names)) != len(all_plugin_unique_names):
                    # this means we have a duplicate plugin_unique_name
                    # we strongly enforce the rule that there can't be two plugin_unique_name on the same
                    # AxoniusDevice
                    self.logger.critical(f"Contradiction detected, sent_plugin: \n{sent_plugin}")
                    return return_error("Contradiction detected. Please resync and check yourself.", 500)

                # now we can assume now that all all_plugin_unique_names are in fact unique
                # we merge all dictionaries!
                all_unique_adapter_devices_data = [v for d in collected_adapter_devices for v in d]

                # Get all tags from all devices. If we have the same tag name and issuer, prefer the newest.
                # a tag is the same tag, if it has the same plugin_unique_name and tagname.
                def keyfunc(tag): return (tag['plugin_unique_name'], tag['tagname'])

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
                    candidate = associated_adapter_devices.get(adapter_device[PLUGIN_UNIQUE_NAME])
                    if candidate is not None and candidate == adapter_device['data']['id']:
                        new_axonius_device['adapters'].append(adapter_device)

                for tag in axonius_device_to_split['tags']:
                    (tag_plugin_unique_name, tag_adapter_id), = tag['associated_adapter_devices'].items()

                    candidate = associated_adapter_devices.get(tag_plugin_unique_name)
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
                     tag_adapter_id), = tag_to_remove_from_old['associated_adapter_devices'].items()
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

    def _save_devices_from_adapter(self, plugin_name, plugin_unique_name):
        """ Function for getting all devices from specific adapter periodically.

        This function should be called in a different thread. It will run forever and periodically get all devices
        From a wanted adapter and save it to the local general db, and the historical db.abs

        :param str plugin_name: The name of the adapter
        :param str plugin_unique_name: The name of the adapter (unique name)
        """

        def insert_device_to_db(device_to_update, parsed_to_insert):
            """
            Insert a device into the DB in a locked way
            :return:
            """
            if LAST_SEEN_FIELD in parsed_to_insert['data']:
                try:
                    parsed_to_insert['data'][LAST_SEEN_FIELD] = dateparse(
                        parsed_to_insert['data'][LAST_SEEN_FIELD])
                except ValueError:
                    pass  # failed :( ? unchanged

            with self.device_db_lock.get_lock([get_unique_name_from_device(parsed_to_insert)]):
                modified_count = self.devices_db.update_one({
                    'adapters': {
                        '$elemMatch': {
                            PLUGIN_UNIQUE_NAME: parsed_to_insert[PLUGIN_UNIQUE_NAME],
                            'data.id': parsed_to_insert['data']['id']
                        }
                    }
                }, {"$set": device_to_update}).modified_count

                if modified_count == 0:
                    self.devices_db.insert_one({
                        "internal_axon_id": uuid.uuid4().hex,
                        "accurate_for_datetime": datetime.now(),
                        "adapters": [parsed_to_insert],
                        "tags": []
                    })

        self.logger.info("Starting to fetch device for {} {}".format(plugin_name, plugin_unique_name))
        promises = []
        try:
            devices = self._get_devices_data(plugin_unique_name)
            for client_name, devices_per_client in devices:
                time_before_client = datetime.now()
                # Saving the raw data on the historic db
                try:
                    self._save_data_in_history(devices_per_client['raw'],
                                               plugin_name,
                                               plugin_unique_name,
                                               "Adapter")
                except pymongo.errors.DocumentTooLarge:
                    # wanna see my "something too large"?
                    self.logger.warn(f"Got DocumentTooLarge for {plugin_unique_name} with client {client_name}.")

                # Here we have all the devices a single client sees
                for device in devices_per_client['parsed']:
                    device['pretty_id'] = beautiful_adapter_device_name(plugin_name, device['id'])
                    parsed_to_insert = {
                        'client_used': client_name,
                        'plugin_type': 'Adapter',
                        'plugin_name': plugin_name,
                        PLUGIN_UNIQUE_NAME: plugin_unique_name,
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
                            if len(field_of_device) > 0:
                                device_to_update[f"adapters.$.data.{field}"] = field_of_device
                        except TypeError:
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
                self.logger.info(f"Finished aggregating for client {client_name} from adapter {plugin_unique_name},"
                                 f" aggregation took {time_for_client.seconds} seconds and returned {devices_count}.")

        except (AdapterOffline, ClientsUnavailable) as e:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            self.logger.warn(f"adapter {plugin_unique_name} might be offline. Reason {str(e)}")
        except Exception as e:
            self.logger.exception("Thread {0} encountered error: {1}".format(threading.current_thread(), str(e)))
            raise

        self.logger.info("Finished for {} {}".format(plugin_name, plugin_unique_name))

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
        if any((x['tagname'] == tag['tagname'] and x['plugin_unique_name'] == tag['plugin_unique_name'])
               for x in axonius_device['tags']):
            self.devices_db.update_one({
                "internal_axon_id": axonius_device['internal_axon_id'],
                "tags.tagname": tag['tagname'],
                "tags.plugin_unique_name": tag['plugin_unique_name']
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
