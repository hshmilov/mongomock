"""
AggregatorPlugin.py: A Plugin for the devices aggregation process
"""

__author__ = "Ofir Yefet"

import requests
import random
import threading
import time
import pymongo
from builtins import RuntimeError
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from axonius.PluginBase import PluginBase, add_rule
from flask import jsonify

# The needed keys in the mapped data
NEEDED_KEYS = ['name', 'os']


class AdapterOffline(Exception):
    pass


class AggregatorPlugin(PluginBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)
        self.devices_db = dict()
        # Lock object for the global device list
        self.device_list_lock = threading.Lock()
        # Open connection to the adapters db
        self.devices_db_connection = self._get_db_connection(True)[self.unique_plugin_name]
        # Managing thread
        self._managing_thread = None

    def start_serve(self):
        """Overriding PluginBase function in order to start our managing thread first.
        """
        self._start_managing_thread()
        super().start_serve()

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
        if devices.status_code == 400:
            raise AdapterOffline()
        return devices.json()

    @add_rule("online_devices")
    def get_online_devices(self):
        """ Exported function for returning all current known devices.

        Accepts:
            GET - for getting all devices
        """
        return jsonify(self.devices_db)

    def _adapters_thread_manager(self):
        """ Function for monitoring other threads activity.

        This function should run in a different thread. It runs forever and monitors the other collector threads.
        If a new adapter will register, this function will create a new thread for him.
        Currently the sampling rate is hard coded for 60 seconds.
        """
        try:
            executors = {'default': ThreadPoolExecutor(10)}
            scheduler = BackgroundScheduler(executors=executors)
            scheduler.start()
            while True:
                current_adapters = requests.get(self.core_address + '/register').json()

                # let's add jobs for all adapters
                for adapter_name, adapter in current_adapters.items():
                    adapter_type = adapter['plugin_type']

                    if adapter['plugin_type'] != "Adapter":
                        # This is not an adapter, not running
                        continue

                    if scheduler.get_job(adapter_name):
                        # We already have a running thread for this adapter
                        continue

                    sample_rate = adapter['device_sample_rate']
                    scheduler.add_job(func=self._save_devices_from_adapter,
                                      trigger=IntervalTrigger(seconds=sample_rate),
                                      next_run_time=datetime.now(),
                                      kwargs={'adapter_name': adapter_name,
                                              'adapter_type': adapter_type},
                                      name="Fetching job for adapter={}".format(adapter_name),
                                      id=adapter_name,
                                      max_instances=1)

                for job in scheduler.get_jobs():
                    if job.id not in current_adapters:
                        # this means that the adapter has disconnected, so we stop fetching it
                        job.remove()

                time.sleep(60)
        except Exception as e:
            self.logger.critical('Managing thread got exception, '
                                 'must restart aggregator manually. Exception: {0}'.format(str(e)))

    def _start_managing_thread(self):
        """Getting data from all adapters.
        """
        if self._managing_thread is None or not self._managing_thread.isAlive():
            self._managing_thread = threading.Thread(target=self._adapters_thread_manager,
                                                     name=self.unique_plugin_name)
            self._managing_thread.start()
        else:
            raise RuntimeError("Already running")

    def _save_devices_from_adapter(self, adapter_name, adapter_type):
        """ Function for getting all devices from specific adapter periodically.

        This function should be called in a different thread. It will run forever and periodically get all devices
        From a wanted adapter and save it to the local general db, and the historical db.abs

        :param str adapter_name: The name of the adapter (unique name)
        :param str adapter_type: The type of the adapter (for example, "ad_adapter")
        """
        try:
            # Creating a connection to the DB
            devices = self._get_devices_data(adapter_name)
            for client_name, devices_per_client in devices:
                # Here we have all the devices a single client sees
                for device in devices_per_client['parsed']:
                    device['client_used'] = client_name
                    device['adapter_type'] = adapter_type
                    device_in_db, device_key = self._general_find_device(device)

                    device_for_db = {k: device[k] for k in NEEDED_KEYS if k in device}
                    device_for_db[adapter_type + '_id'] = device['id']
                    device_for_db[adapter_name + '_raw'] = device['raw']

                    if device_in_db:
                        # We need to update the device data
                        self._general_update_device(device_for_db, device_key)
                    else:
                        self._general_create_device(device_for_db)
                    self._save_parsed_in_db(device)

                # Saving the raw data on the historic db
                self._save_device_in_history(devices_per_client['raw'],
                                             adapter_name,
                                             adapter_type)
        except AdapterOffline:
            # not throwing - if the adapter is truly offline, then Core will figure it out
            # and then the scheduler will remove this task
            self.logger.warn("adapter {} might be offline".format(adapter_name))
        except Exception as e:
            self.logger.error("Thread {0} encountered error: {1}".format(threading.current_thread(), str(e)))
            raise

    def _save_parsed_in_db(self, device):
        self.devices_db_connection['parsed'].insert_one(device)

    def _save_device_in_history(self, device, adapter_name, adapter_type):
        """ Function for saving raw data of a device in history.

        This function will save the data on mongodb. the db name is 'devices' and the collection is 'raw' always!

        :param device: The raw data of the current device
        :param str adapter_name: The name of the adapter
        :param str adapter_type: The type of the adapter
        """
        try:
            self.devices_db_connection['raw'].insert_one({'raw': device,
                                                          'adapter_name': adapter_name,
                                                          'adapter_type': adapter_type})
        except pymongo.errors.PyMongoError as e:
            self.logger.error("Error in pymongo. details: {}".format(e))

    def _general_create_device(self, device_parsed):
        """ Creates a new device in the devices_db.

        Generates a unique id for the device.abs

        :param dict device_parsed: A dict with all the parsed data of the device
        """
        with self.device_list_lock:
            while True:
                unique_key = random.getrandbits(32)
                if unique_key not in self.devices_db:
                    break

            self.devices_db[unique_key] = device_parsed

    def _general_update_device(self, device_parsed, unique_id):
        """ Updates a device in the devices_db.

        :param dict device_parsed: A dict with all the parsed data of the device
        :param int unique_id: The uniqe id of the device
        """
        # Finding the device according to the unique field
        # TODO: Check that the device_parsed is at the wanted format
        with self.device_list_lock:
            self.devices_db[unique_id] = device_parsed

    def _general_find_device(self, device):
        """ Find a matching device in the device db.

        This should hold the main logic of the aggregator. This function is trying to find, or match
        A device that supposed to be the same identity of the given device.

        :param dict device: A parsed device data we try to find in the devices db

        :returns device: The device data (None if not found)
        :returns unique_id: The id of the found device (None if not found)
        """
        # Try to find according to same adapter id
        with self.device_list_lock:
            adapter_id_field = device['adapter_type'] + '_id'
            for unique_id, current_device in self.devices_db.items():
                if current_device.get(adapter_id_field) == device['id']:
                    # Found with same ID
                    return current_device, unique_id

            # Try finding according to hostname
            for unique_id, current_device in self.devices_db.items():
                if current_device.get('name') == device.get('name', None):
                    # Found a device with same name
                    return current_device, unique_id

        return None, None
