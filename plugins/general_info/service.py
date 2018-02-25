import time
import threading
import functools

from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.devices.device import Device
from axonius.mixins.triggerable import Triggerable
from axonius.parsing_utils import get_exception_string
from axonius.utils.files import get_local_config_file
from general_info.subplugins.basic_computer_info import GetBasicComputerInfo
from general_info.subplugins.installed_softwares import GetInstalledSoftwares
from general_info.subplugins.last_user_logon import GetLastUserLogon


MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS = 30
SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS = 5


class GeneralInfoService(PluginBase, Triggerable):
    class MyDevice(Device):
        pass

    def __init__(self, *args, **kargs):
        super().__init__(get_local_config_file(__file__), *args, **kargs)

        self.work_lock = threading.RLock()
        self.is_enabled = False  # Are we enabled?
        self._execution_manager_lock = threading.Lock()  # This is not an RLock. it can be acquired only once.
        self._number_of_active_execution_requests_var = 0  # Number of active execution requests
        self.subplugins = []  # All of our subplugins.

    def _triggered(self, job_name: str, post_json: dict, *args):
        """
        Returns any errors as-is.
        :return:
        """
        if job_name != 'execute':
            self.logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)

        acquired = False
        try:
            if self.work_lock.acquire(False):
                acquired = True
                self._gather_general_info()
            else:
                raise RuntimeError("General info gathering is already taking place, try again later")
        finally:
            if acquired:
                self.work_lock.release()

    @property
    def number_of_active_execution_requests(self):
        """
        A variable indicating the number of execution requests that we sent but did not return yet.
        Its a property since we wanna have a lock here - multiple threads access it.
        :return: the var.
        """

        with self._execution_manager_lock:
            return self._number_of_active_execution_requests_var

    @number_of_active_execution_requests.setter
    def number_of_active_execution_requests(self, value):
        """
        A setter function for _number_of_active_execution_requests.
        :return:
        """

        with self._execution_manager_lock:
            self._number_of_active_execution_requests_var = value

    def _gather_general_info(self):
        """
        Runs wmi queries on windows devices to understand important stuff.
        """

        self.logger.info("Gathering General info started.")
        with self.work_lock:
            self.logger.debug("acquired work lock")

            # Reinitialize all subplugins. We do that in each run, to refresh cached data.
            self.subplugins = [GetLastUserLogon(self), GetInstalledSoftwares(self), GetBasicComputerInfo(self)]

            """
            1. Get a list of windows devices
            2. Get wmi queries to run from all subplugins
            2. Execute a wmi queries on them
            3. Pass the result to the subplugins
            """

            windows_devices = self.devices_db.find(
                {"adapters.data.os.type": "Windows"},
                projection={'internal_axon_id': True,
                            'adapters.data.id': True,
                            'adapters.plugin_unique_name': True,
                            'adapters.client_used': True})

            windows_devices = list(windows_devices)  # no cursors needed.
            self.logger.info(f"Found {len(windows_devices)} windows devices to run queries on.")

            # We don't wanna burst thousands of queries here, so we are going to have a thread that always
            # keeps count of the number of requests, and shoot new ones in case needed.
            self.number_of_active_execution_requests = 0

            for device in windows_devices:
                if self.number_of_active_execution_requests >= MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS:
                    # Wait a few sec to re-check again.
                    time.sleep(SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS)

                else:
                    # shoot another one!
                    self.number_of_active_execution_requests = self.number_of_active_execution_requests + 1
                    internal_axon_id = device["internal_axon_id"]

                    self.logger.debug(f"Going to request action on {internal_axon_id}")

                    # Get all wmi queries from all subadapters.
                    wmi_commands = []
                    for subplugin in self.subplugins:
                        wmi_commands.extend(subplugin.get_wmi_commands())

                    # Now run all queries you have got on that device.
                    p = self.request_action("execute_wmi", internal_axon_id,
                                            {"wmi_commands": wmi_commands})

                    p.then(did_fulfill=functools.partial(self._handle_wmi_execution_success, device),
                           did_reject=functools.partial(self._handle_wmi_execution_failure, device))

    def _handle_wmi_execution_success(self, device, data):
        try:
            self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1

            # Now get some info depending on the adapter that ran the execution
            executer_info = dict()
            executer_info["adapter_unique_name"] = data["responder"]
            executer_info["adapter_unique_id"] = \
                [adap for adap in device["adapters"] if adap["plugin_unique_name"]
                    == executer_info["adapter_unique_name"]][0]["data"]["id"]

            # We have got many requests. Lets call the handler of each of our subplugins.
            # We go through the amount of queries each subplugin requested, linearly.
            queries_response = data["output"]["product"]
            queries_response_index = 0

            # Create a new device, since these subplugins will have some generic info enrichments.
            adapterdata_device = self._new_device()

            for subplugin in self.subplugins:
                subplugin_num_queries = len(subplugin.get_wmi_commands())
                subplugin_result = queries_response[queries_response_index:
                                                    queries_response_index + subplugin_num_queries]
                subplugin.handle_result(device, executer_info, subplugin_result, adapterdata_device)

                # Update the response index.
                queries_response_index = queries_response_index + subplugin_num_queries

            # All of these plugins might have inserted new devices, lets save the device & format.
            self.add_adapterdata_to_device(
                (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]), adapterdata_device.to_dict())

            # Fixme: That is super inefficient, we save the fields upon each wmi success instead when we finish
            # Fixme: running all queries.
            self._save_field_names_to_db()

        except Exception as e:
            self.logger.exception("An error occured while processing wmi result: {0}, {1}"
                                  .format(str(e), get_exception_string()))

    def _handle_wmi_execution_failure(self, device, exc):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
        self.logger.info("Failed running wmi query on device {0}! error: {1}"
                         .format(device["internal_axon_id"], str(exc)))
