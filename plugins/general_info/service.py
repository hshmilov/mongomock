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
from axonius.utils.parsing import get_exception_string
from axonius.utils.files import get_local_config_file
from general_info.subplugins.basic_computer_info import GetBasicComputerInfo
from general_info.subplugins.installed_softwares import GetInstalledSoftwares
from general_info.subplugins.user_logons import GetUserLogons
from axonius.fields import Field, ListField
from datetime import datetime


MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS = 100
SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS = 5

# The maximum time we wait for new execution answers. If no sent execution request comes back we bail out.
# note that this timeout shouldn't be met since the execution request will be rejected before (plugin base execution
# monitor will reject the promise if an update wasn't done)
MAX_TIME_TO_WAIT_FOR_EXECUTION_REQUESTS_TO_FINISH_IN_SECONDS = 180

# The maximum time we wait until all active execution threads
MAX_TIME_TO_WAIT_FOR_EXECUTION_THREADS_TO_FINISH_IN_SECONDS = 180

subplugins_objects = [GetUserLogons, GetInstalledSoftwares, GetBasicComputerInfo]


class GeneralInfoService(PluginBase, Triggerable):
    class MyDeviceAdapter(DeviceAdapter):
        general_info_last_success_execution = Field(datetime, "Last General Info Success")

        ad_bad_config_no_lm_hash = Field(int, "Bad Config - No LMHash")
        ad_bad_config_force_guest = Field(int, "Bad Config - Force Guest")
        ad_bad_config_authentication_packages = ListField(str, "Bad Config - Authentication Packages")
        ad_bad_config_lm_compatibility_level = Field(int, "Bad Config - Compatibility Level")
        ad_bad_config_disabled_domain_creds = Field(int, "Bad Config - Disabled Domain Creds")
        ad_bad_config_secure_boot = Field(int, "Bad Config - Secure Boot")

    class MyUserAdapter(UserAdapter):
        pass

    def __init__(self, *args, **kargs):
        super().__init__(get_local_config_file(__file__), *args, **kargs)

        self.work_lock = threading.RLock()
        self.is_enabled = False  # Are we enabled?
        self._execution_manager_lock = threading.Lock()  # This is not an RLock. it can be acquired only once.
        self._number_of_active_execution_requests_var = 0  # Number of active execution requests
        self._number_of_triggers = 0

        general_info_sync_enabled = self.config['DEFAULT']['general_info_sync_enabled'].lower()
        assert general_info_sync_enabled in ['true', 'false']
        self._general_info_sync_enabled = bool(general_info_sync_enabled)

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
        if self._number_of_triggers == 1 and self._general_info_sync_enabled is True:
            # first trigger is blocking.
            logger.info(f"Running gather_general_info sync (number of triggers: {self._number_of_triggers})")
            self._gather_general_info()
        else:
            # Run it in a different thread
            logger.info(f"Running gather_general_info async (number of triggers: {self._number_of_triggers})")
            threading.Thread(target=self._run_gather_general_info_async).start()

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

    def _run_gather_general_info_async(self):
        """
        Simply runs _gather_general_info but also try/excepts it to log everything.
        :return:
        """

        try:
            self._gather_general_info()
        except Exception:
            logger.exception("Run gather_general_info asynchronously: Got an exception.")

    @stoppable
    def _gather_general_info(self):
        """
        Runs wmi queries on windows devices to understand important stuff.
        Afterwards, adds more information to users.
        """

        logger.info("Gathering General info started.")
        acquired = False
        try:
            acquired = self.work_lock.acquire(False)
            if acquired:
                logger.debug("acquired work lock")

                # First, gather general info about devices
                self._gather_windows_devices_general_info()

                # Second, go over all devices we have, and try to associate them with users.
                self._associate_users_with_devices()

            else:
                raise RuntimeError("General info gathering is already taking place, try again later")
        finally:
            if acquired:
                self.work_lock.release()

    def _gather_windows_devices_general_info(self):
        """
        Runs wmi queries on windows devices to understand important stuff.
        :returns: true if successful, false otherwise.
        """

        logger.info("Gathering General info about windows devices - started.")
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
                        'adapters.data.hostname': True,
                        'adapters.data.name': True,
                        'tags': True})

        windows_devices = list(windows_devices)  # no cursors needed.
        logger.info(f"Found {len(windows_devices)} windows devices to run queries on.")

        # We don't wanna burst thousands of queries here, so we are going to have a thread that always
        # keeps count of the number of requests, and shoot new ones in case needed.
        self.number_of_active_execution_requests = 0

        for device_i, device in enumerate(windows_devices):
            # a number that increases if we don't shoot any new requests. If we are stuck too much time,
            # we might have an error in the execution. in such a case we bail out.
            self.seconds_stuck = 0

            while self.number_of_active_execution_requests >= MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS:
                # Wait a few sec to re-check again.
                time.sleep(SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS)
                self.seconds_stuck = self.seconds_stuck + SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS

                if self.seconds_stuck % 60 == 0:
                    logger.info(f"Execution progress: {device_i} out of {len(windows_devices)} devices executed")

                if self.seconds_stuck > MAX_TIME_TO_WAIT_FOR_EXECUTION_REQUESTS_TO_FINISH_IN_SECONDS:
                    # The current execution requests sent will still be handled, everything in general will
                    # still continue to work, but this thread will finish. It is important because if the system
                    # waits for us to finish we wanna avoid getting stuck forever.
                    logger.error(f"Waited {self.seconds_stuck} seconds to continue sending more execution "
                                 f"requests but we still have {self.number_of_active_execution_requests} "
                                 f"threads active")
                    return False

            # shoot another one!
            self.number_of_active_execution_requests = self.number_of_active_execution_requests + 1
            internal_axon_id = device["internal_axon_id"]

            logger.debug(f"Going to request action on {internal_axon_id}")

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

        # execution answer threads should finish immediately because they don't do anything
        # that takes time excpet tagging that should be extra fast. but in the future we might
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

    def _associate_users_with_devices(self):
        """
        Assuming devices were assocaited with users, now we associate users with devices.
        :return:
        """
        logger.info("Associating users with devices")

        # 1. Get all devices which have users associations, and map all these devices to one global users object.
        devices_with_users_association = self.devices.get(data={"users": {"$exists": True}})
        users = {}
        for device in devices_with_users_association:
            # Get a list of all users associated for this device.
            for sd_users in [d['data']['users'] for d in device.specific_data if d['data'].get('users') is not None]:
                # for each user associated, add a (device, user) tuple.
                for user in sd_users:
                    if users.get(user['username']) is None:
                        users[user['username']] = []

                    # users, is a dict of all users, ordered by the key string 'username'.
                    # the dict is a mapping of the username to a list of tuples (user, device).
                    # (user, device) is a specific user + last_use_time + more info of that specific device.
                    # so we might have user1 and user2 objects which have the same username, but have other data
                    # different.
                    users[user['username']].append((user, device))

        # 2. Go over all users. for each user, associate all known devices.
        for username, linked_devices_and_users_list in users.items():
            # Create the new adapterdata for that user
            adapterdata_user = self._new_user_adapter()

            # Find that user
            user = list(self.users.get(data={"id": username}))

            # Do we have it? or do we need to create it?
            if len(user) > 1:
                # Can't be! how can we have a user with the same id? should have been correlated.
                logger.error(f"Found a couple of users (expected one) with same id: {username} -> {user}")
                continue
            elif len(user) == 0:
                # user does not exists, create it.
                logger.debug(f"username {username} needs to be created, this is a todo task. continuing")
                user_dict = self._new_user_adapter()
                user_dict.id = username  # Should be the unique identifier of that user.
                user_dict.username, user_dict.domain = username.split("@")  # expecting username to be user@domain.
                user_dict.is_local = True
                self._save_data_from_plugin(
                    self.plugin_unique_name,
                    {"raw": [], "parsed": [user_dict.to_dict()]},
                    EntityType.Users, False)
                # At this point we must have it.
                user = list(self.users.get(data={"id": username}))
                assert len(user) == 1, f"We just created the user {username} but the length is reported as {len(user)}."

            # at this point the user exists, go over all associated devices and add them.
            user = user[0]
            for linked_user, linked_device in linked_devices_and_users_list:
                device_caption = linked_device.get_first_data("hostname") or \
                    linked_device.get_first_data("name") or \
                    linked_device.get_first_data("id")

                logger.debug(f"Associating {device_caption} with user {username}")
                try:
                    adapterdata_user.last_seen_in_devices = \
                        max(linked_user['last_use_date'], adapterdata_user.last_seen_in_devices)
                except Exception:
                    # Last seen does not exist
                    adapterdata_user.last_seen_in_devices = linked_user['last_use_date']

                adapterdata_user.add_associated_device(
                    device_caption=device_caption,
                    last_use_date=linked_user['last_use_date'],
                    adapter_unique_name=linked_user['origin_unique_adapter_name'],
                    adapter_data_id=linked_user['origin_unique_adapter_data_id']
                )

            # we have a new adapterdata_user, lets add it. we do not give any specific identity
            # since this tag isn't associated to a specific adapter.
            adapterdata_user.id = username
            user.add_adapterdata(adapterdata_user.to_dict())

        self._save_field_names_to_db(EntityType.Users)

    def _handle_wmi_execution_success(self, device, data):
        try:
            self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
            is_execution_exception = False
            last_execution_debug = None

            # Initialize all subplugins. We do that in each run, to refresh cached data.
            subplugins_list = [con(self, logger) for con in subplugins_objects]

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
            adapterdata_device = self._new_device_adapter()
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
                    logger.exception(f"Subplugin {subplugin.__class__.__name__} exception."
                                     f"Internal axon id is {device['internal_axon_id']}. "
                                     f"Moving on to next plugin.")
                    all_error_logs.append(f"Subplugin {subplugin.__class__.__name__} exception: "
                                          f"{get_exception_string()}")

                # Update the response index.
                queries_response_index = queries_response_index + subplugin_num_queries

            # All of these plugins might have inserted new devices, lets get it.
            adapterdata_device.general_info_last_success_execution = datetime.now()
            new_data = adapterdata_device.to_dict()
            new_data['id'] = executer_info["adapter_unique_id"]

            # Add the final one
            self.devices.add_adapterdata(
                [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])], new_data,
                action_if_exists="update")  # If the tag exists, we update it using deep merge (and not replace it).

            # Fixme: That is super inefficient, we save the fields upon each wmi success instead when we finish
            # Fixme: running all queries.
            self._save_field_names_to_db(EntityType.Devices)

            if len(all_error_logs) > 0:
                is_execution_exception = True
                last_execution_debug = "All errors logs: {0}".format("\n".join(all_error_logs))

        except Exception as e:
            logger.exception("An error occured while processing wmi result: {0}, {1}"
                             .format(str(e), get_exception_string()))
            is_execution_exception = True
            last_execution_debug = f"An exception occured while processing wmi results: {get_exception_string()}"

        finally:
            # Disable execution failure tag if exists.
            self.devices.add_label(
                [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                "Execution Failure", False
            )

            # Enable or disable execution exception
            self.devices.add_label(
                [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                "Execution Exception", is_execution_exception
            )

            # If there is debug data to add, add it.
            if last_execution_debug is not None:
                last_execution_debug = last_execution_debug.replace("\\n", "\n")
                self.devices.add_data(
                    [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                    "Last Execution Debug", last_execution_debug
                )

            logger.info(f"Finished with device {device['internal_axon_id']}.")

    def _handle_wmi_execution_failure(self, device, exc):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1

        try:
            # Avidor: Someone decided that on failure we get an exception object, and not a real object.
            # God damn. Until i fix that, we do this very ugly thing...
            # TODO: Fix the whole god damn execution system

            if "{'status': 'failed', 'output': ''}" == str(exc):
                logger.debug(f"No executing adapters for device {device['internal_axon_id']}, continuing")
                return

            logger.info("Failed running wmi query on device {0}! error: {1}"
                        .format(device["internal_axon_id"], str(exc)))

            # We need to tag that device, but we have no associated adapter devices. we must use the first one.
            if len(device["adapters"]) > 0:
                executer_info = dict()
                executer_info["adapter_unique_name"] = device["adapters"][0]["plugin_unique_name"]
                executer_info["adapter_unique_id"] = device["adapters"][0]["data"]["id"]

                self.devices.add_label(
                    [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                    "Execution Failure", True
                )

                ex_str = str(exc).replace("\\n", "\n")

                self.devices.add_data(
                    [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                    "Last Execution Debug", f"Execution failed: {ex_str}"
                )
        except Exception:
            logger.exception("Exception in failure.")

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
