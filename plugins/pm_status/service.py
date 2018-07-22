import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.thread_stopper import stoppable

import time
import threading
import functools

from axonius.plugin_base import PluginBase, add_rule, return_error, EntityType
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.mixins.triggerable import Triggerable
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import get_exception_string
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from datetime import datetime


MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS = 4
SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS = 5

# The maximum time we wait for new execution answers. If no sent execution request comes back we bail out.
# note that this timeout shouldn't be met since the execution request will be rejected before (plugin base execution
# monitor will reject the promise if an update wasn't done)
MAX_TIME_TO_WAIT_FOR_EXECUTION_REQUESTS_TO_FINISH_IN_SECONDS = 60 * 10

# The maximum time we wait until all active execution threads
MAX_TIME_TO_WAIT_FOR_EXECUTION_THREADS_TO_FINISH_IN_SECONDS = 180


# RPC Errors
DCOM_ERROR_PROBABLY_RPC_ACCESS_DENIED = "0x800706ba"
DCOM_ERROR_INTERNET_PROBLEMS = "0x80072EE2"


class PmStatusService(PluginBase, Triggerable):
    class MyDeviceAdapter(DeviceAdapter):
        pm_last_execution_success = Field(datetime, "Last PM Success")

    class MyUserAdapter(UserAdapter):
        pass

    def __init__(self, *args, **kargs):
        super().__init__(get_local_config_file(__file__), *args, **kargs)

        self.work_lock = threading.RLock()
        self.is_enabled = False  # Are we enabled?
        self._execution_manager_lock = threading.Lock()  # This is not an RLock. it can be acquired only once.
        self._number_of_active_execution_requests_var = 0  # Number of active execution requests
        self._number_of_triggers = 0

        sync_enabled = self.config['DEFAULT']['sync_enabled'].lower()
        assert sync_enabled in ['true', 'false']
        self._sync_enabled = sync_enabled.strip().lower() == 'true'

        self._activate('execute')

    def _triggered(self, job_name: str, post_json: dict, *args):
        """
        Returns any errors as-is.
        :return:
        """
        if job_name != 'execute':
            logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)

        self._number_of_triggers = self._number_of_triggers + 1
        if self._number_of_triggers == 1 and self._sync_enabled is True:
            # first trigger is blocking.
            logger.info(f"Running get_pm_status sync (number of triggers: {self._number_of_triggers})")
            self._get_pm_status()
        else:
            # Run it in a different thread
            logger.info(f"Running get_pm_status async (number of triggers: {self._number_of_triggers})")
            threading.Thread(target=self._get_pm_status_async).start()

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

    def _get_pm_status_async(self):
        """
        Simply runs _get_pm_status but also try/excepts it to log everything.
        :return:
        """

        try:
            self._get_pm_status()
        except Exception:
            logger.exception("Run get_pm_status asynchronously: Got an exception.")

    @stoppable
    def _get_pm_status(self):
        """
        Runs rpc queries on windows devices to understand the patch management status.
        """
        if not self._execution_enabled:
            logger.error("Execution is not enabled, going on")
            return []

        if not self._pm_rpc_enabled and not self._pm_smb_enabled:
            logger.error("PM Status Failure: rpc and smb settings are false (Global Settings)")
            return []

        logger.info("Get PM Status started (before lock).")
        acquired = False
        try:
            acquired = self.work_lock.acquire(False)
            if acquired:
                logger.debug("acquired work lock")

                self._get_pm_status_internal()

                logger.info("Finished gathering pm status")

            else:
                msg = "Get PM Status was called and is already taking place, try again later"
                logger.error(msg)
                raise RuntimeError(msg)
        finally:
            if acquired:
                self.work_lock.release()

    def _get_pm_status_internal(self):
        """
        Runs wmi queries on windows devices to understand important stuff.
        :returns: true if successful, false otherwise.
        """

        logger.info("Get PM Status about windows devices - started.")
        """
        1. Get a list of windows devices
        2. Execute PM status with rpc
        3. Parse results
        """

        # The following query should run on all windows devices but since Axonius does not support
        # any type of execution other than AD this is an AD-HOC solution we put here to be faster.
        # It should be {"adapters.data.os.type": "Windows"}
        # Also, we query for devices that have SOME network interfaces somehow (not necessarily from active directory)
        # If it doesn't have then clearly we would not have any way of interacting with it.
        windows_devices = self.devices_db.find(
            {"adapters.plugin_name": "active_directory_adapter", "adapters.data.network_interfaces": {"$exists": True}},
            projection={'internal_axon_id': True,
                        'adapters.data.id': True,
                        'adapters.plugin_unique_name': True,
                        'adapters.client_used': True,
                        'adapters.data.hostname': True,
                        'adapters.data.name': True,
                        'tags': True})

        windows_devices_count = windows_devices.count()
        logger.info(f"Found {windows_devices_count} Windows devices to run queries on.")

        # Lets make some better logging
        if windows_devices_count > 10000:
            log_message_device_count_threshold = 1000
        elif windows_devices_count > 1000:
            log_message_device_count_threshold = 100
        else:
            log_message_device_count_threshold = 50

        # Determine pm type
        if self._pm_rpc_enabled is True and self._pm_smb_enabled is True:
            pm_online_type = "rpc_and_fallback_smb"
            logger.info("Using RPC and fallback SMB for PM")
        elif self._pm_rpc_enabled is True:
            pm_online_type = "rpc"
            logger.info("Using RPC for PM")
        elif self._pm_smb_enabled is True:
            pm_online_type = "smb"
            logger.info("Using SMB for PM")
        else:
            raise ValueError("Can not choose PM Online type")

        # We don't wanna burst thousands of queries here, so we are going to have a thread that always
        # keeps count of the number of requests, and shoot new ones in case needed.
        self.number_of_active_execution_requests = 0

        device_i = 0
        for device in windows_devices:
            # a number that increases if we don't shoot any new requests. If we are stuck too much time,
            # we might have an error in the execution. in such a case we bail out.
            device_i += 1
            self.seconds_stuck = 0

            while self.number_of_active_execution_requests >= MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS:
                # Wait a few sec to re-check again.
                time.sleep(SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS)
                self.seconds_stuck = self.seconds_stuck + SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS

                if self.seconds_stuck > MAX_TIME_TO_WAIT_FOR_EXECUTION_REQUESTS_TO_FINISH_IN_SECONDS:
                    # The current execution requests sent will still be handled, everything in general will
                    # still continue to work, but this thread will finish. It is important because if the system
                    # waits for us to finish we wanna avoid getting stuck forever.
                    logger.error(f"Waited {self.seconds_stuck} seconds to continue sending more execution "
                                 f"requests but we still have {self.number_of_active_execution_requests} "
                                 f"threads active")
                    return False

            if device_i % log_message_device_count_threshold == 0:
                logger.info(f"Execution progress: {device_i} out of {windows_devices_count} devices executed")

            # shoot another one!
            self.number_of_active_execution_requests = self.number_of_active_execution_requests + 1
            internal_axon_id = device["internal_axon_id"]

            logger.debug(f"Going to request action on {internal_axon_id}")
            wmi_smb_commands = [{"type": "pmonline", "args": [pm_online_type]}]

            # Now run all queries you have got on that device.
            p = self.request_action(
                "execute_wmi_smb",
                internal_axon_id,
                {
                    "wmi_smb_commands": wmi_smb_commands
                }
            )

            p.then(did_fulfill=functools.partial(self._handle_pm_success, device),
                   did_reject=functools.partial(self._handle_pm_failure, device))

        # execution answer threads should finish immediately because they don't do anything
        # that takes time except tagging that should be extra fast. but in the future we might
        # have some more complex things there, so we wait here until everything is finished.
        self.seconds_stuck = 0
        while self.number_of_active_execution_requests > 0:
            time.sleep(1)
            self.seconds_stuck = self.seconds_stuck + 1
            if self.seconds_stuck > MAX_TIME_TO_WAIT_FOR_EXECUTION_THREADS_TO_FINISH_IN_SECONDS:
                logger.error(f"Waited {self.seconds_stuck} seconds for all execution threads to "
                             f"finish, bailing out with {self.number_of_active_execution_requests} threads still"
                             f"active.")
                return False

        return True

    def _handle_pm_success(self, device, data):
        try:
            self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
            is_execution_exception = False
            last_pm_status_debug = None

            # Now get some info depending on the adapter that ran the execution
            executer_info = dict()
            executer_info["adapter_unique_name"] = data["responder"]
            adapter_used = [adap for adap in device["adapters"] if adap["plugin_unique_name"]
                            == executer_info["adapter_unique_name"]][0]
            executer_info["adapter_client_used"] = adapter_used['client_used']
            executer_info["adapter_unique_id"] = adapter_used["data"]["id"]

            response = data["output"]["product"][0]

            # Create a new device
            adapterdata_device = self._new_device_adapter()
            all_error_logs = []

            try:
                # Check that the response status is ok
                if response['status'] != 'ok':
                    if DCOM_ERROR_PROBABLY_RPC_ACCESS_DENIED in response['data']:
                        # This happens quite often.
                        raise ValueError("DCOM returned 0x800706ba. This probably means RPC Access Denied")
                    elif DCOM_ERROR_INTERNET_PROBLEMS in response['data']:
                        # This can happen on computers with no internet or with internet problems
                        raise ValueError("Error code 0x80072EE2. This probably means internet access error")
                    else:
                        raise ValueError(f"PM Response is not ok: {response}")

                # Parse the data. add data to all_error_logs
                for patch in response['data']:
                    try:
                        pm_publish_date = patch.get("LastDeploymentChangeTime")
                        if pm_publish_date is not None:
                            pm_publish_date = datetime.fromtimestamp(pm_publish_date)
                    except Exception:
                        logger.exception(f"Error parsing publish date of patch {patch}")
                        pass

                    pm_title = patch.get("Title")
                    pm_msrc_severity = patch.get("MsrcSeverity")
                    pm_type = patch.get("Type")
                    if pm_type != "Software" and pm_type != "Driver":
                        logger.error(f"Expected pm type to be Software/Driver but its {pm_type}")
                        pm_type = None

                    pm_categories = patch.get("Categories")
                    pm_security_bulletin_ids = patch.get("SecurityBulletinIDs")
                    pm_kb_article_ids = patch.get("KBArticleIDs")

                    # Validate Its all strings
                    if pm_categories is not None:
                        pm_categories = [str(x) for x in pm_categories]

                    if pm_security_bulletin_ids is not None:
                        pm_security_bulletin_ids = [str(x) for x in pm_security_bulletin_ids]

                    if pm_kb_article_ids is not None:
                        pm_kb_article_ids = [str(x) for x in pm_kb_article_ids]

                    adapterdata_device.add_available_security_patch(
                        title=pm_title,
                        security_bulletin_ids=pm_security_bulletin_ids,
                        kb_article_ids=pm_kb_article_ids,
                        msrc_severity=pm_msrc_severity,
                        patch_type=pm_type,
                        categories=pm_categories,
                        publish_date=pm_publish_date
                    )
            except Exception:
                logger.exception(f"Exception while parsing data on internal axon id is {device['internal_axon_id']}. ")
                all_error_logs.append(f"exception: {get_exception_string()}")

            # All of these plugins might have inserted new devices, lets get it.
            adapterdata_device.pm_last_execution_success = datetime.now()
            new_data = adapterdata_device.to_dict()
            new_data['id'] = executer_info["adapter_unique_id"]

            # Add the final one
            self.devices.add_adapterdata(
                [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])], new_data,
                action_if_exists="update",  # If the tag exists, we update it using deep merge (and not replace it).
                client_used=executer_info["adapter_client_used"]
            )

            # Fixme: That is super inefficient, we save the fields upon each wmi success instead when we finish
            # Fixme: running all queries.
            self._save_field_names_to_db(EntityType.Devices)

            if len(all_error_logs) > 0:
                is_execution_exception = True
                last_pm_status_debug = "All errors logs: {0}".format("\n".join(all_error_logs))

        except Exception as e:
            logger.exception("An error occured while processing pm result: {0}, {1}"
                             .format(str(e), get_exception_string()))
            is_execution_exception = True
            last_pm_status_debug = f"An exception occured while processing pm results: {get_exception_string()}"

        finally:
            # Disable execution failure tag if exists.
            self.devices.add_label(
                [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                "PM Status Failure", False
            )

            # Enable or disable execution exception
            self.devices.add_label(
                [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                "PM Status Exception", is_execution_exception
            )

            # If there is debug data to add, add it.
            if last_pm_status_debug is not None:
                last_pm_status_debug = last_pm_status_debug.replace("\\n", "\n")
                self.devices.add_data(
                    [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                    "Last PM Status Debug", last_pm_status_debug
                )

            logger.info(f"Finished with device {device['internal_axon_id']}.")

    def _handle_pm_failure(self, device, exc):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1

        try:
            # Avidor: Someone decided that on failure we get an exception object, and not a real object.
            # God damn. Until i fix that, we do this very ugly thing...
            # TODO: Fix the whole god damn execution system

            if "{'status': 'failed', 'output': ''}" == str(exc):
                logger.debug(f"No executing adapters for device {device['internal_axon_id']}, continuing")
                return

            if "[BLACKLIST]" in str(exc):
                logger.info(f"Failure because of blacklist in device {device['internal_axon_id']}")
                return

            logger.info("Failed running pm status on device {0}! error: {1}"
                        .format(device["internal_axon_id"], str(exc)))

            # We need to tag that device, but we have no associated adapter devices. we must use the first one.
            if len(device["adapters"]) > 0:
                executer_info = dict()
                executer_info["adapter_unique_name"] = device["adapters"][0]["plugin_unique_name"]
                executer_info["adapter_unique_id"] = device["adapters"][0]["data"]["id"]

                self.devices.add_label(
                    [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                    "PM Status Failure", True
                )

                ex_str = str(exc).replace("\\n", "\n")

                self.devices.add_data(
                    [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                    "Last PM Status Debug", f"Execution failed: {ex_str}"
                )
        except Exception:
            logger.exception("Exception in failure.")

    @add_rule('run', methods=['POST'], should_authenticate=False)
    def run_now(self):
        self._get_pm_status_async()
