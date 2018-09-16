import logging

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME

logger = logging.getLogger(f'axonius.{__name__}')

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
from axonius.utils.db import find_and_sort_by_first_element_of_list
from axonius.profiling.memory import asizeof
from general_info.subplugins.basic_computer_info import GetBasicComputerInfo
from general_info.subplugins.installed_softwares import GetInstalledSoftwares
from general_info.subplugins.user_logons import GetUserLogons
from general_info.subplugins.connected_hardware import GetConnectedHardware
from general_info.subplugins.pm import GetAvailableSecurityPatches
from axonius.fields import Field, ListField
from datetime import datetime


MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS = 4
SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS = 5

# The maximum time we wait for new execution answers. If no sent execution request comes back we bail out.
# note that this timeout shouldn't be met since the execution request will be rejected before (plugin base execution
# monitor will reject the promise if an update wasn't done)
MAX_TIME_TO_WAIT_FOR_EXECUTION_REQUESTS_TO_FINISH_IN_SECONDS = 60 * 10

# The maximum time we wait until all active execution threads
# If this time is met we will still have all devices data inserted, we just will have less users data (association
# will begin before all devices have finished)
MAX_TIME_TO_WAIT_FOR_EXECUTION_THREADS_TO_FINISH_IN_SECONDS = 60 * 10


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
        self.subplugins_list = []

        general_info_sync_enabled = self.config['DEFAULT']['general_info_sync_enabled'].lower()
        assert general_info_sync_enabled in ['true', 'false']
        self._general_info_sync_enabled = general_info_sync_enabled.strip().lower() == 'true'

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
        Simply runs _get_pm_status but also try/excepts it to log everything.
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
        if not self._execution_enabled:
            logger.info(f"Execution is disabled, not continuing")
            return []
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

                logger.info("Finished gathering info & associating users for all devices")

            else:
                msg = "General info was called and is already taking place, try again later"
                logger.error(msg)
                raise RuntimeError(msg)
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
        # Initialize all of our subplugins
        subplugins_objects = [GetUserLogons, GetInstalledSoftwares, GetBasicComputerInfo, GetConnectedHardware]
        if self._should_use_axr is True and (self._pm_smb_enabled or self._pm_rpc_enabled):
            logger.info("Using AXR to query patch management info")
            subplugins_objects.append(GetAvailableSecurityPatches)
        else:
            logger.info("Not querying patch management info using general info")

        self.subplugins_list = [con(self, logger) for con in subplugins_objects]
        logger.info("Done initializing subplugins")

        # The following query should run on all windows devices but since Axonius does not support
        # any type of execution other than AD this is an AD-HOC solution we put here to be faster.
        # It should be {"adapters.data.os.type": "Windows"}
        # We also make sure that we query only for active directory devices which are Windows and that have any sort
        # of ip address.
        windows_devices, windows_devices_count = find_and_sort_by_first_element_of_list(
            self.devices_db,
            {
                "adapters":
                    {
                        "$elemMatch":
                            {
                                "plugin_name": "active_directory_adapter",
                                "data.os.type": "Windows",
                                "data.network_interfaces.ips": {"$exists": True}
                            }
                    }
            },
            {
                '_id': False,
                'internal_axon_id': True,
                "tags.data.general_info_last_success_execution": True
            },
            "tags.data.general_info_last_success_execution"
        )
        logger.info(f"Found {windows_devices_count} Windows devices to run queries on.")

        # Performance issue (AX-1592):
        # We are querying for all devices of a certain type. This could result in a huge amount of memory if we
        # have too much results.
        #
        # Using the generator of mongodb, on the other side, is bad as well. Since we are not sending
        # execution requests to all devices immediately, but send them in chunks, it takes a while
        # until we reach the end of the generator.
        # But, Mongodb works in the following way in default: for every generator, it fetches the first 100
        # results. when we reach the 101'st object, it connects to the db again and fetches it.
        # If we don't do that within 10 minutes, MongoDB assumes the cursor was deleted.
        #
        # So the following code wouldn't work on the 101'st device since it takes more than 10 minutes for us
        # to finish code execution.
        #
        # We decided to query only the internal_axon_ids and store all of them in memory.
        # Regarding memory consumption: Profiling shows that a list of 100,000 axon id's takes about 10 mb.
        # This can be shown by seeing
        # axonius.profiling.memory.asizeof([d['internal_axon_id'] for d in self.devices_db.find({})])/(1024**2)
        #
        # Cons:
        # internal_axon_id's are not consistent. If we have correlation, it will be incorrect.
        # Currently execution occurs only after correlation, and it takes less than a cycle (execution over 1 cycle
        # is not supported) so that's ok.

        windows_devices = [d['internal_axon_id'] for d in windows_devices]
        logger.info(f"Approximate devices internal_axon_ids size in memory: {asizeof(windows_devices)/(1024**2)} mb")

        # Lets make some better logging
        if windows_devices_count > 10000:
            log_message_device_count_threshold = 1000
        elif windows_devices_count > 1000:
            log_message_device_count_threshold = 100
        else:
            log_message_device_count_threshold = 50

        # We don't wanna burst thousands of queries here, so we are going to have a thread that always
        # keeps count of the number of requests, and shoot new ones in case needed.
        self.number_of_active_execution_requests = 0

        # Determine max number of execution requests. If we use the new execution method then pm_status isn't working,
        # we should raise our bar by 2.
        if self._should_use_axr:
            max_number_of_execution_requests = MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS * 2
        else:
            max_number_of_execution_requests = MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS

        device_i = 0
        for internal_axon_id in windows_devices:
            # a number that increases if we don't shoot any new requests. If we are stuck too much time,
            # we might have an error in the execution. in such a case we bail out.
            device_i += 1
            self.seconds_stuck = 0

            while self.number_of_active_execution_requests >= max_number_of_execution_requests:
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
            # Caution! If we had correlation up to this point, we will have serious problems.

            logger.debug(f"Going to request action on {internal_axon_id}")

            # Get all wmi queries from all subadapters.
            wmi_smb_commands = []
            for subplugin in subplugins_objects:
                wmi_smb_commands.extend(subplugin.get_wmi_smb_commands())

            # Now run all queries you have got on that device.
            if self._should_use_axr:
                p = self.request_action(
                    "execute_axr",
                    internal_axon_id,
                    {
                        "axr_commands": wmi_smb_commands
                    }
                )
            else:
                # fallback to old execution setting
                p = self.request_action(
                    "execute_wmi_smb",
                    internal_axon_id,
                    {
                        "wmi_smb_commands": wmi_smb_commands
                    }
                )

            p.then(did_fulfill=functools.partial(self._handle_wmi_execution_success, internal_axon_id),
                   did_reject=functools.partial(self._handle_wmi_execution_failure, internal_axon_id))

        # At this moment we have some execution threads which are running (should finish almost immediately since
        # they aren't doing any complex logic) and threads that haven't come back already. we wait for them.
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
        Assuming devices were associated with users, now we associate users with devices.
        :return:
        """
        logger.info("Associating users with devices")

        # 1. Get all devices which have users associations, and map all these devices to one global users object.
        devices_with_users_association = self.devices_db.find({
            "$or": [
                {"adapters.data.users": {"$exists": True}},
                {"tags.data.users": {"$exists": True}}
            ]
        })
        users = {}
        for device in devices_with_users_association:
            # Get a list of all users associated for this device.
            all_device_data = device.get('adapters', []) + device.get('tags', [])
            for sd_users in [d['data']['users'] for d in all_device_data if isinstance(d['data'], dict) and d['data'].get('users') is not None]:
                # for each user associated, add a (device, user) tuple.
                for user in sd_users:
                    if 'username' not in user:
                        logger.warning(f'Bad user {user}')
                        continue
                    if users.get(user['username']) is None:
                        users[user['username']] = []

                    # users, is a dict of all users, ordered by the key string 'username'.
                    # the dict is a mapping of the username to a list of tuples (user, device).
                    # (user, device) is a specific user + last_use_time + more info of that specific device.
                    # so we might have user1 and user2 objects which have the same username, but have other data
                    # different.
                    users[user['username']].append((user, device))

        # 2. Go over all users. whatever we don't have, we must create first.
        for username in users.keys():
            user = list(self.users.get(data={"id": username}))
            if len(user) == 0:
                # user does not exists, create it.
                user_dict = self._new_user_adapter()
                user_dict.id = username  # Should be the unique identifier of that user.
                try:
                    user_dict.username, user_dict.domain = username.split("@")  # expecting username to be user@domain.
                except ValueError:
                    logger.exception(f"Bad user format! expected 'username@domain' format, got {username}. bypassing")
                    continue
                user_dict.is_local = True
                self._save_data_from_plugin(
                    self.plugin_unique_name,
                    {"raw": [], "parsed": [user_dict.to_dict()]},
                    EntityType.Users, False)

        # 3. We have to rebuild the views db. But we don't have the internal axon id's.
        # We need to refactor self._save_data_from_plugin to return the internal_axon_id's. Until we do that,
        # We collect their internal axon id's .
        # list(users.keys()) is not redundant, we need convert dict_keys to list or else pymongo will throw a
        # can not decode object error
        new_users = self.users_db.find({"adapters.data.id": {"$in": list(users.keys())}},
                                       projection={"_id": False, "internal_axon_id": True})
        new_internal_axon_ids = [nu['internal_axon_id'] for nu in new_users]

        try:
            self._request_db_rebuild(sync=True, internal_axon_ids=new_internal_axon_ids).raise_for_status()
        except Exception:
            logger.exception(f"Error in rebuilding, continuing without it. This means we won't have some of the local"
                             f"users until the next rebuild occurs, and these won't have associated devices until"
                             f"next cycle of general_info occurs")

        # 4. Now go over all users again. for each user, associate all known devices.
        for username, linked_devices_and_users_list in users.items():
            # Create the new adapterdata for that user
            adapterdata_user = self._new_user_adapter()

            # Find that user. It should be in the view new.
            user = list(self.users.get(data={"id": username}))

            # Do we have it? or do we need to create it?
            if len(user) > 1:
                # Can't be! how can we have a user with the same id? should have been correlated.
                logger.critical(f"Found a couple of users (expected one) with same id: {username} -> {user}")
                continue
            elif len(user) == 0:
                logger.error(f"User {username} should have been created in the view but is not there! Continuing")
                continue

            # at this point the user exists, go over all associated devices and add them.
            user = user[0]
            client_used = None
            for linked_user, linked_device in linked_devices_and_users_list:
                try:
                    def get_first_data(fd_d, fd_attr):
                        # Gets the first "hostname", for example, from a device object.
                        for sd in fd_d.get('adapters', []) + fd_d.get('tags', []):
                            if isinstance(sd.get('data'), dict):
                                value = sd['data'].get(fd_attr)
                                if value is not None:
                                    return value
                        return None

                    device_caption = get_first_data(linked_device, "hostname") or \
                        get_first_data(linked_device, "name") or get_first_data(linked_device, "id")

                    logger.debug(f"Associating {device_caption} with user {username}")
                    try:
                        adapterdata_user.last_seen_in_devices = \
                            max(linked_user['last_use_date'], adapterdata_user.last_seen_in_devices)
                    except Exception:
                        if linked_user.get('last_use_date') is not None:
                            adapterdata_user.last_seen_in_devices = linked_user.get('last_use_date')

                    if linked_user.get('user_sid') is not None:
                        adapterdata_user.user_sid = linked_user.get('user_sid')

                    if linked_user.get('is_disabled') is not None:
                        adapterdata_user.account_disabled = linked_user.get('is_disabled')

                    is_admin_status = linked_user.get("is_admin")
                    if isinstance(is_admin_status, bool):
                        adapterdata_user.is_admin = is_admin_status

                    client_used = linked_user.get('origin_unique_adapter_client')

                    adapterdata_user.add_associated_device(
                        device_caption=device_caption,
                        last_use_date=linked_user.get('last_use_date'),
                        adapter_unique_name=linked_user.get('origin_unique_adapter_name'),
                        adapter_data_id=linked_user.get('origin_unique_adapter_data_id'),
                        adapter_client_used=client_used
                    )
                except Exception:
                    logger.exception(f"Cant associate user {linked_user}")

            # we have a new adapterdata_user, lets add it. we do not give any specific identity
            # since this tag isn't associated to a specific adapter.
            adapterdata_user.id = username
            user.add_adapterdata(adapterdata_user.to_dict(), client_used=client_used or "")

        self._save_field_names_to_db(EntityType.Users)
        logger.info("Finished associating users with devices")

    def _handle_wmi_execution_success(self, internal_axon_id, data):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1

        # This has to be outside of the try, since the except and finally assume we have a device.
        # We need to get the device first.
        device = self.devices_db.find_one({"internal_axon_id": internal_axon_id})
        if device is None:
            logger.critical(f"Did not find document containing internal_axon_id {internal_axon_id}. "
                            f"Did we have correlation in place?")
            return

        try:
            is_execution_exception = False
            last_execution_debug = None

            # Now get some info depending on the adapter that ran the execution
            executer_info = dict()
            executer_info["adapter_unique_name"] = data["responder"]
            adapter_used = [adap for adap in device["adapters"] if adap[PLUGIN_UNIQUE_NAME]
                            == executer_info["adapter_unique_name"]][0]
            executer_info["adapter_client_used"] = adapter_used['client_used']
            executer_info["adapter_unique_id"] = adapter_used["data"]["id"]

            # We have got many requests. Lets call the handler of each of our subplugins.
            # We go through the amount of queries each subplugin requested, linearly.
            queries_response = data["output"]["product"]
            queries_response_index = 0

            # Create a new device, since these subplugins will have some generic info enrichments.
            adapterdata_device = self._new_device_adapter()
            adapterdata_device.id = f"{adapter_used[PLUGIN_UNIQUE_NAME]},{adapter_used['data']['id']}"

            all_error_logs = []

            for subplugin in self.subplugins_list:
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

            # Disable execution failure tag if exists.
            self.devices.add_label(
                [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                "Connection Error", False
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

    def _handle_wmi_execution_failure(self, internal_axon_id, exc):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
        device = self.devices_db.find_one({"internal_axon_id": internal_axon_id})
        if device is None:
            logger.critical(f"Did not find document containing internal_axon_id {internal_axon_id}. "
                            f"Did we have correlation in place?")
            return

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

            logger.info("Failed running wmi query on device {0}! error: {1}"
                        .format(device["internal_axon_id"], str(exc)))

            # We need to tag that device, but we have no associated adapter devices. we must use the first one.
            if len(device["adapters"]) > 0:
                executer_info = dict()
                executer_info["adapter_unique_name"] = device["adapters"][0][PLUGIN_UNIQUE_NAME]
                executer_info["adapter_unique_id"] = device["adapters"][0]["data"]["id"]

                if "connection refused" in str(exc).lower():
                    self.devices.add_label(
                        [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                        "Connection Error", True
                    )

                else:
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

    @property
    def plugin_subtype(self):
        return "Post-Correlation"
