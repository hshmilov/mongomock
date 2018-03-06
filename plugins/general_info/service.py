import time
import threading
import functools

from axonius.devices import deep_merge_only_dict
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.devices.device import Device
from axonius.mixins.triggerable import Triggerable
from axonius.parsing_utils import get_exception_string
from axonius.utils.files import get_local_config_file
from general_info.subplugins.basic_computer_info import GetBasicComputerInfo
from general_info.subplugins.installed_softwares import GetInstalledSoftwares
from general_info.subplugins.user_logons import GetUserLogons
from axonius.fields import Field
from datetime import datetime


MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS = 50
SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS = 5

subplugins_objects = [GetUserLogons, GetInstalledSoftwares, GetBasicComputerInfo]


class GeneralInfoService(PluginBase, Triggerable):
    class MyDevice(Device):
        general_info_last_success_execution = Field(datetime, "Last General Info Success")

    def __init__(self, *args, **kargs):
        super().__init__(get_local_config_file(__file__), *args, **kargs)

        self.work_lock = threading.RLock()
        self.is_enabled = False  # Are we enabled?
        self._execution_manager_lock = threading.Lock()  # This is not an RLock. it can be acquired only once.
        self._number_of_active_execution_requests_var = 0  # Number of active execution requests

        self._activate('execute')

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
                            'adapters.client_used': True,
                            'tags': True})

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
                    wmi_smb_commands = []
                    for subplugin in subplugins_objects:
                        wmi_smb_commands.extend(subplugin.get_wmi_smb_commands())

                    # Now run all queries you have got on that device.
                    p = self.request_action(
                        "execute_wmi_smb",
                        internal_axon_id,
                        {
                            "wmi_smb_commands": wmi_smb_commands
                        }
                    )

                    p.then(did_fulfill=functools.partial(self._handle_wmi_execution_success, device),
                           did_reject=functools.partial(self._handle_wmi_execution_failure, device))

        return True

    def _handle_wmi_execution_success(self, device, data):
        try:
            self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
            is_execution_exception = False
            last_execution_debug = None

            # Initialize all subplugins. We do that in each run, to refresh cached data.
            subplugins_list = [con(self) for con in subplugins_objects]

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
            all_error_logs = []

            for subplugin in subplugins_list:
                subplugin_num_queries = len(subplugin.get_wmi_smb_commands())
                subplugin_result = queries_response[queries_response_index:
                                                    queries_response_index + subplugin_num_queries]
                try:
                    did_subplugin_succeed = \
                        subplugin.handle_result(device,
                                                executer_info,
                                                subplugin_result,
                                                adapterdata_device)

                    all_error_logs.extend(subplugin.get_error_logs())

                    if did_subplugin_succeed is not True:
                        raise ValueError("return value is not True")
                except Exception:
                    self.logger.exception(f"Subplugin {subplugin.__class__.__name__} exception."
                                          f"Internal axon id is {device['internal_axon_id']}. "
                                          f"Moving on to next plugin.")
                    all_error_logs.append(f"Subplugin {subplugin.__class__.__name__} exception: "
                                          f"{get_exception_string()}")

                # Update the response index.
                queries_response_index = queries_response_index + subplugin_num_queries

            # All of these plugins might have inserted new devices, lets get it.
            adapterdata_device.general_info_last_success_execution = datetime.now()
            new_data = adapterdata_device.to_dict()

            # But! It might be that this time we brought less info than before. So we should merge the data, instead
            # of replacing it.
            final_data = [tag["data"] for tag in device["tags"]
                          if tag["plugin_unique_name"] == self.plugin_unique_name and tag["type"] == "adapterdata"]
            if len(final_data) > 0:
                final_data = final_data[0]
            else:
                final_data = {}

            # Merge. Note that we deep merge dicts but not lists, since lists are like fields
            # for us (for example ip). Usually when we get some list variable we get all of it so we don't need
            # any update things
            final_data = deep_merge_only_dict(new_data, final_data)

            # Add the final one
            self.add_adapterdata_to_device(
                (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]), final_data)

            # Fixme: That is super inefficient, we save the fields upon each wmi success instead when we finish
            # Fixme: running all queries.
            self._save_field_names_to_db()

            if len(all_error_logs) > 0:
                is_execution_exception = True
                last_execution_debug = "All errors logs: {0}".format("\n".join(all_error_logs))

        except Exception as e:
            self.logger.exception("An error occured while processing wmi result: {0}, {1}"
                                  .format(str(e), get_exception_string()))
            is_execution_exception = True
            last_execution_debug = f"An exception occured while processing wmi results: {get_exception_string()}"

        finally:
            # Disable execution failure tag if exists.
            self.add_label_to_device(
                (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]),
                "Execution Failure", False
            )

            # Enable or disable execution exception
            self.add_label_to_device(
                (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]),
                "Execution Exception", is_execution_exception
            )

            # If there is debug data to add, add it.
            if last_execution_debug is not None:
                last_execution_debug = last_execution_debug.replace("\\n", "\n")
                self.add_data_to_device(
                    (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]),
                    "Last Execution Debug", last_execution_debug
                )

    def _handle_wmi_execution_failure(self, device, exc):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1

        try:
            # Avidor: Someone decided that on failure we get an exception object, and not a real object.
            # God damn. Until i fix that, we do this very ugly thing...
            # TODO: Fix the whole god damn execution system

            if "{'status': 'failed', 'output': ''}" == str(exc):
                self.logger.info(f"No executing adpaters for device {device['internal_axon_id']}, continuing")
                return

            self.logger.info("Failed running wmi query on device {0}! error: {1}"
                             .format(device["internal_axon_id"], str(exc)))

            # We need to tag that device, but we have no associated adapter devices. we must use the first one.
            if len(device["adapters"]) > 0:
                executer_info = dict()
                executer_info["adapter_unique_name"] = device["adapters"][0]["plugin_unique_name"]
                executer_info["adapter_unique_id"] = device["adapters"][0]["data"]["id"]

                self.add_label_to_device(
                    (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]),
                    "Execution Failure", True
                )

                ex_str = str(exc).replace("\\n", "\n")

                self.add_data_to_device(
                    (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]),
                    "Last Execution Debug", f"Execution failed: {ex_str}"
                )
        except Exception:
            self.logger.exception("Exception in failure.")

    @add_rule('run', methods=['POST'], should_authenticate=False)
    def run_now(self):
        if self.scheduler is None:
            self.start_activatable()

        else:
            jobs = self.scheduler.get_jobs()
            reset_job = next(job for job in jobs if job.name == 'general_info')
            reset_job.modify(next_run_time=datetime.now())
            self.scheduler.wakeup()

        return ""
