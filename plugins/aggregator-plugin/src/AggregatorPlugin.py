"""
AggregatorPlugin.py: A Plugin for the devices aggregation process
"""

__author__ = "Ofir Yefet"

import requests
import threading
import pymongo
from builtins import RuntimeError
from datetime import datetime
import uuid
from itertools import chain

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from axonius.PluginBase import PluginBase, add_rule, return_error
from axonius.ParsingUtils import beautiful_adapter_device_name
from flask import jsonify, request
from exceptions import AdapterOffline


def parsed_devices_match(first, second):
    """
    Whether or not two adapter devices (i.e. a single device as viewed by an adapter) match
    :param first: first adapter device to check
    :param second: second adapter device to check
    :return: bool
    """
    return first['plugin_unique_name'] == second['plugin_unique_name'] and \
        first['data']['id'] == second['data']['id']


def parsed_device_match_plugin(plugin_data, parsed_device):
    """
    Whether or not a plugin is referring a specific adapter device
    :param plugin_data: the plugin data
    :param parsed_device: a adapter device
    :return: bool
    """
    return plugin_data['associated_adapter_devices']. \
        get(parsed_device['plugin_unique_name']) == parsed_device['data']['id']


class AggregatorPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)
        # Lock object for the global device list
        # this is a reentrant lock
        self.device_db_lock = threading.RLock()
        # Open connection to the adapters db
        self.devices_db_connection = self._get_db_connection(True)[
            self.plugin_unique_name]
        # Scheduler for querying core for online adapters and querying the adapters themselves
        self._online_adapters_scheduler = None
        # Load devices DB, or create an empty one
        self._load_devices_from_persistent_db()
        # Starting the managing thread
        self._start_managing_thread()

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
        devices = self.request_remote_plugin('devices', adapter)
        if devices.status_code != 200:
            raise AdapterOffline()
        return devices.json()

    @add_rule("online_devices")
    def get_online_devices(self):
        """ Exported function for returning all current known devices.

        Accepts:
            GET - for getting all devices
        """
        return jsonify(self.devices_db)

    @add_rule("online_device/<device_id>")
    def get_online_device(self, device_id):
        """ Exported function for returning all current known devices.

        Accepts:
            GET - for getting all devices
        """
        return jsonify(self.devices_db[device_id])

    @add_rule("query_devices", methods=["POST"])
    def query_devices(self):
        jobs = self._online_adapters_scheduler.get_jobs()
        for job in jobs:
            self.logger.info("resetting time for {0}".format(job.name))
            job.modify(next_run_time=datetime.now())
        self.online_plugins_scheduler.wakeup()
        return ""

    def _adapters_thread_manager(self):
        """ Function for monitoring other threads activity.

        This function should run in a different thread. It runs forever and monitors the other collector threads.
        If a new adapter will register, this function will create a new thread for him.
        Currently the sampling rate is hard coded for 60 seconds.
        """
        try:
            current_adapters = requests.get(
                self.core_address + '/register').json()

            self.logger.info(
                "registered adapters = {}".format(current_adapters))

            get_devices_job_name = "Get device job"

            # let's add jobs for all adapters
            for adapter_name, adapter in current_adapters.items():
                if adapter['plugin_type'] != "Adapter":
                    # This is not an adapter, not running
                    continue

                if self._online_adapters_scheduler.get_job(adapter_name):
                    # We already have a running thread for this adapter
                    continue

                sample_rate = adapter['device_sample_rate']

                self._online_adapters_scheduler.add_job(func=self._save_devices_from_adapter,
                                                        trigger=IntervalTrigger(
                                                            seconds=sample_rate),
                                                        next_run_time=datetime.now(),
                                                        kwargs={'plugin_unique_name': adapter['plugin_unique_name'],
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

    def _start_managing_thread(self):
        """
        Getting data from all adapters.
        """

        if self._online_adapters_scheduler is None:
            executors = {'default': ThreadPoolExecutor(10)}
            self._online_adapters_scheduler = BackgroundScheduler(
                executors=executors)
            self._online_adapters_scheduler.add_job(func=self._adapters_thread_manager,
                                                    trigger=IntervalTrigger(
                                                        seconds=60),
                                                    next_run_time=datetime.now(),
                                                    name='adapters_thread_manager',
                                                    id='adapters_thread_manager',
                                                    max_instances=1)
            self._online_adapters_scheduler.start()

        else:
            raise RuntimeError("Already running")

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
        associated_adapter_devices = sent_plugin.get(
            'associated_adapter_devices')

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

        # now let's update our db
        with self.device_db_lock:
            # figure out all axonius devices that at least one of its adapter_device are in the
            # given plugin's association
            axonius_device_candidates_dict = {axonius_id: axonius_device for axonius_id, axonius_device in
                                              self.devices_db.items() if
                                              # this is equivalent to:
                                              # is `sent_plugin` matching with any of axonius_device['adapters']?
                                              any(parsed_device_match_plugin(sent_plugin, axon_adapter_device)
                                                  for axon_adapter_device in
                                                  axonius_device['adapters'].values(
                                              )
                                                  if axon_adapter_device['plugin_type'] == 'Adapter')}
            if association_type == 'Tag':
                if len(axonius_device_candidates_dict) != 1:
                    # it has been checked that at most 1 device was provided (if len(associated_adapter_devices) != 1)
                    # then if it's not 1, its definitely 0
                    return return_error(
                        "A tag must be associated with just one adapter device, the device provided is unavailable")
                # take (assumed single) key from dictionary
                axonius_device_id, = axonius_device_candidates_dict
                self._update_device_with_tag(sent_plugin, axonius_device_id)
            elif association_type == 'Link':
                # in this case, we need to link (i.e. "merge") all axonius_device_candidates_dict
                # if there's only one, then the link is either associated only to
                # one device (which is as irrelevant as it gets)
                # or all the devices are already linked. In any case, if a real merge isn't done
                # it means someone made a mistake.
                if len(axonius_device_candidates_dict) < 2:
                    return return_error(f"Got a 'Link' with only {len(axonius_device_candidates_dict)} candidates",
                                        400)

                collected_adapter_devices_dicts = [axonius_device['adapters'] for axonius_device in
                                                   axonius_device_candidates_dict.values()]
                all_plugin_unique_names = list(chain.from_iterable(
                    d.keys() for d in collected_adapter_devices_dicts))
                if len(set(all_plugin_unique_names)) != len(all_plugin_unique_names):
                    # this means we have a duplicate plugin_unique_name
                    # we strongly enforce the rule that there can't be two plugin_unique_name on the same
                    # AxoniusDevice
                    self.logger.critical(
                        f"Contradiction detected, sent_plugin: \n{sent_plugin}")
                    return return_error("Contradiction detected. Please resync and check yourself.", 500)

                # now we can assume now that all all_plugin_unique_names are in fact unique
                # we merge all dictionaries!
                all_unique_adpater_devices_data = {
                    k: v for d in collected_adapter_devices_dicts for k, v in d.items()}

                internal_axon_id = uuid.uuid4().hex
                self.devices_db[internal_axon_id] = {
                    "internal_axon_id": internal_axon_id,
                    "accurate_for_datetime": datetime.now(),
                    "adapters": all_unique_adpater_devices_data,
                    "tags": list(chain(*(axonius_device['tags'] for axonius_device in
                                         axonius_device_candidates_dict.values())))
                }

                # now, let us delete all other AxoniusDevices
                for axonius_device_id in axonius_device_candidates_dict:
                    del self.devices_db[axonius_device_id]
            elif association_type == 'Unlink':
                if len(axonius_device_candidates_dict) != 1:
                    return return_error(
                        "All associated_adapter_devices in an unlink operation must be from the same Axonius "
                        "device, in your case, they're from "
                        f"{len(axonius_device_candidates_dict)} devices.")
                axonius_device_to_split = list(
                    axonius_device_candidates_dict.values())[0]

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
                    "adapters": {
                        associated_adapter_device: axonius_device_to_split['adapters'].pop(
                            associated_adapter_device)
                        for associated_adapter_device in associated_adapter_devices
                    },
                    "tags": []
                }
                for adapter_device in new_axonius_device['adapters'].values():
                    # "split" the tags on an adapter basis
                    new_axonius_device['tags'] += [tag for tag in axonius_device_to_split['tags']
                                                   if parsed_device_match_plugin(tag, adapter_device)]
                    axonius_device_to_split['tags'] = [tag for tag in axonius_device_to_split['tags']
                                                       if not parsed_device_match_plugin(tag, adapter_device)]

                self.devices_db[internal_axon_id] = new_axonius_device

            self._save_devices_db_to_persistent_db()

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
        self.logger.info("Starting to fetch device for {} {}".format(
            plugin_name, plugin_unique_name))
        try:
            devices = self._get_devices_data(plugin_unique_name)
            # This is locked although this is a (relatively) lengthy process we can't allow linking or unlinking during
            # this process, because the behavior will be complicated and could introduce weird bugs in the future.
            # Perhaps a less restrictive lock could be used, say, an 'adapter based' lock,
            # but that will be quite difficult, and might have big overhead thus having
            # a negative performance effect overall.
            # In any case, this is a per adapter lock, so at most it will be locked for all the inserts per a specific
            # adapter, which is not that bad. The only slow thing here is the DB insertion, which
            # shouldn't be so slow anyway.
            with self.device_db_lock:
                # if this is true after going through all devices, the persistent devices db will be updated
                added_new_device = False
                for client_name, devices_per_client in devices:
                    # Here we have all the devices a single client sees
                    for device in devices_per_client['parsed']:
                        device['pretty_id'] = beautiful_adapter_device_name(
                            plugin_name, device['id'])
                        parsed_to_insert = {
                            'client_used': client_name,
                            'plugin_type': 'Adapter',
                            'plugin_name': plugin_name,
                            'plugin_unique_name': plugin_unique_name,
                            'accurate_for_datetime': datetime.now(),
                            'data': device
                        }

                        device_key = self._find_device_by_adapter(
                            parsed_to_insert)

                        if device_key:
                            # We need to update the device data
                            self._update_device_with_adapter(parsed_to_insert, device_key,
                                                             parsed_to_insert['accurate_for_datetime'])
                        else:
                            self._create_device(parsed_to_insert)
                            added_new_device = True
                        self._save_parsed_in_db(parsed_to_insert)

                    # Saving the raw data on the historic db
                    self._save_data_in_history(devices_per_client['raw'],
                                               plugin_name,
                                               plugin_unique_name,
                                               "Adapter")

                self._save_devices_db_as_is_to_persistent_db()
                if added_new_device:
                    self._save_devices_db_to_historical_persistent_db()

        except AdapterOffline:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            self.logger.warn(
                "adapter {} might be offline".format(plugin_unique_name))
        except Exception as e:
            self.logger.error("Thread {0} encountered error: {1}".format(
                threading.current_thread(), str(e)))
            raise

        self.logger.info("Finished for {} {}".format(
            plugin_name, plugin_unique_name))

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
                                                          'plugin_unique_name': plugin_unique_name,
                                                          'plugin_type': plugin_type})
        except pymongo.errors.PyMongoError as e:
            self.logger.error("Error in pymongo. details: {}".format(e))

    def _create_device(self, device_parsed):
        """ Creates a new device in the devices_db

        Generates a unique id for the device.

        :param dict device_parsed: dict
        """
        with self.device_db_lock:
            internal_axon_id = uuid.uuid4().hex
            self.devices_db[internal_axon_id] = {
                "internal_axon_id": internal_axon_id,
                "accurate_for_datetime": datetime.now(),
                "adapters": {
                    device_parsed['plugin_unique_name']: device_parsed
                },
                "tags": []
            }

    def _update_device_with_tag(self, tag, axonius_device_id):
        """
        Updates the devices db to either add or update the given tag
        :param tag: tag from user
        :param axonius_device_id: axonius id
        :return: None
        """
        with self.device_db_lock:
            axonius_device_to_change = self.devices_db[axonius_device_id]
            associated_tag = next((candidate_tag for candidate_tag in axonius_device_to_change['tags']
                                   if candidate_tag['plugin_unique_name'] == tag['plugin_unique_name'] and
                                   candidate_tag['tagname'] == tag['tagname'] and
                                   candidate_tag['associated_adapter_devices'] == tag['associated_adapter_devices']),
                                  None)
            if associated_tag is None:
                axonius_device_to_change['tags'].append(tag)
            else:
                associated_tag['tagvalue'] = tag['tagvalue']
            axonius_device_to_change['accurate_for_datetime'] = tag.get(
                'accurate_for_datetime')

    def _update_device_with_adapter(self, adapter_parsed, axonius_device_id, accurate_for_datetime=None):
        """ Updates a device in the devices_db using adapter.

        :param dict adapter_parsed: dict
        :param str axonius_device_id: The unique id of the device
        """
        added_device_plugin_unique_name = adapter_parsed['plugin_unique_name']
        with self.device_db_lock:
            axonius_device_to_change = self.devices_db[axonius_device_id]
            # add or update the adapter_device within the axonius device
            axonius_device_to_change['adapters'][added_device_plugin_unique_name] = adapter_parsed
            # update the timestamp
            axonius_device_to_change['accurate_for_datetime'] = accurate_for_datetime if accurate_for_datetime \
                else datetime.now()

    def _find_device_by_adapter(self, adapter_device):
        """ Find a device in the db. This will allow for us to update our data using the newly acquired
        parsed_device. If it's already in the DB (it has been returned previously by an adapter) we'll find it

        :param dict adapter_device: A parsed device data we try to find in the devices db

        :returns unique_id: The id of the found device (None if not found)
        """
        # Try to find according to same adapter id
        with self.device_db_lock:
            # figure out which axonius_devices have a matching adapter_device in their ['data']
            potential_candidate = [axonius_id for axonius_id, axonius_device in self.devices_db.items() if

                                   # this is equivalent to:
                                   # is `adapter_device` matching with any of axonius_device['adapters'] ?
                                   any(parsed_devices_match(adapter_device, axon_adapter_device)
                                       for axon_adapter_device in
                                       axonius_device['adapters'].values())]

            if len(potential_candidate) > 1:
                raise RuntimeError(
                    f"Data inconsistency: {len(potential_candidate)} axonius devices have the same device")
            if len(potential_candidate) == 1:
                return potential_candidate[0]

            return None

    def _save_devices_db_to_persistent_db(self):
        """
        Makes everything persistent as its supposed to be
        :return:
        """
        with self.device_db_lock:
            self._save_devices_db_as_is_to_persistent_db()
            self._save_devices_db_to_historical_persistent_db()

    def _save_devices_db_as_is_to_persistent_db(self):
        """
        Saves `self.devices_db` as-is into `devices_db` in the persistent db, overriding everything that is there.
        :return:
        """
        devices_to_save = []
        for device in self.devices_db.values():
            device = dict(device)
            device['adapters'] = list(device['adapters'].values())
            devices_to_save.append(device)

        if len(devices_to_save) != 0:
            self.devices_db_connection['devices_db'].delete_many({})
            self.devices_db_connection['devices_db'].insert_many(
                devices_to_save)

    def _save_devices_db_to_historical_persistent_db(self):
        """
        Saves the current devices db (`self.devices_db`) to the historical persistent (mongo) db 'db_historical'
        This doesn't save everything, rather it saves just the devices ids and tags associations.
        :return:
        """
        with self.device_db_lock:
            device_db_snapshot = {}
            for axon_device_id, axon_device in self.devices_db.items():
                axon_device_snapshot = {
                    'accurate_for_datetime': axon_device['accurate_for_datetime'],
                    'adapters': [],
                    'tags': axon_device['tags']
                }
                for plugin_unique_name, adapter_device in axon_device['adapters'].items():
                    # taking all fields, for both plugins and adapters, except the data field that'll be cleaned
                    # in case of adapters, to not overflow the db too soon
                    axon_adapter_device_snapshot = {k: v for k, v in adapter_device.items() if k in
                                                    ('_id',
                                                     'accurate_for_datetime', 'client_used', 'plugin_name',
                                                     'plugin_type', 'plugin_unique_name')}
                    axon_adapter_device_snapshot['data'] = {
                        'id': adapter_device['data']['id']}
                    axon_device_snapshot['adapters'].append(axon_adapter_device_snapshot)

                device_db_snapshot[axon_device_id] = axon_device_snapshot

            self.devices_db_connection['db_historical'].insert_one(
                {"devices_db": device_db_snapshot})

    def _load_devices_from_persistent_db(self):
        """
        Will rewrite self.devices_db with whatever's in the database
        :return:
        """
        with self.device_db_lock:
            self.devices_db = {}
            for axon_device in self.devices_db_connection['devices_db'].find():
                axon_device['adapters'] = {adapter['plugin_unique_name']: adapter for adapter in
                                           axon_device['adapters']}
                self.devices_db[axon_device['internal_axon_id']] = axon_device
