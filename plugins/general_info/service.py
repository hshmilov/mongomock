import functools
import logging
import traceback


import threading
import time
from datetime import datetime, timedelta
from typing import Tuple, Iterable

from promise import Promise

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.mixins.triggerable import Triggerable, RunIdentifier
from axonius.plugin_base import EntityType, PluginBase
from axonius.profiling.memory import asizeof
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from general_info.subplugins.basic_computer_info import GetBasicComputerInfo
from general_info.subplugins.connected_hardware import GetConnectedHardware
from general_info.subplugins.installed_softwares import GetInstalledSoftwares
from general_info.subplugins.pm import GetAvailableSecurityPatches
from general_info.subplugins.reg_file_subplugin import CheckReg
from general_info.subplugins.user_logons import GetUserLogons

logger = logging.getLogger(f'axonius.{__name__}')


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

# RPC Errors
DCOM_ERROR_PROBABLY_RPC_ACCESS_DENIED = "0x800706ba"
DCOM_ERROR_INTERNET_PROBLEMS = "0x80072EE2"

SHOULD_USE_AXR = False  # Old things we might use in the future. do not change as this doesn't work and is risky.


class GeneralInfoService(Triggerable, PluginBase):

    class MyDeviceAdapter(DeviceAdapter):

        general_info_last_success_execution = Field(datetime, 'Last WMI Success')
        pm_last_execution_success = Field(datetime, 'Last PM Info Success')

        ad_bad_config_no_lm_hash = Field(int, 'Bad Config - No LMHash')
        ad_bad_config_force_guest = Field(int, 'Bad Config - Force Guest')
        ad_bad_config_authentication_packages = ListField(str, 'Bad Config - Authentication Packages')
        ad_bad_config_lm_compatibility_level = Field(int, 'Bad Config - Compatibility Level')
        ad_bad_config_disabled_domain_creds = Field(int, 'Bad Config - Disabled Domain Creds')
        ad_bad_config_secure_boot = Field(int, 'Bad Config - Secure Boot')
        reg_key_not_exists = ListField(str, 'Validated Registry Keys - Not Existing')
        reg_key_exists = ListField(str, 'Validated Registry Keys - Existing')

    class MyUserAdapter(UserAdapter):
        pass

    def __init__(self, *args, **kargs):
        super().__init__(get_local_config_file(__file__), *args, **kargs)

        self._execution_manager_lock = threading.Lock()  # This is not an RLock. it can be acquired only once.
        self._number_of_active_execution_requests_var = 0  # Number of active execution requests
        self.subplugins_list = []

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name != 'execute':
            raise RuntimeError('Job name is wrong')

        logger.info("Gathering General info started.")
        promises = list(self._gather_windows_devices_general_info(post_json))
        promises_results = {}
        for p, internal_axon_id in promises:
            try:
                Promise.wait(p, timedelta(minutes=30).total_seconds())
                is_success = any(val is True for val in p.value)
                errors = ','.join([val for val in p.value if isinstance(val, str)])

                if p.is_fulfilled and is_success:
                    promises_results[internal_axon_id] = {
                        'success': True,
                        'value': 'WMI execution success'
                    }
                else:
                    promises_results[internal_axon_id] = {
                        'success': False,
                        'value': errors if errors else 'WMI execution failure, check extended data for reason'
                    }
            except Exception as e:
                promises_results[internal_axon_id] = {
                    'success': False,
                    'value': f'An unknown error occurred: {str(e)}'
                }

        logger.info('Finished gathering info & associating users for all devices')
        return promises_results

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

    @staticmethod
    def get_first_data(fd_d, fd_attr):
        # Gets the first 'hostname', for example, from a device object.
        for sd in fd_d.get('adapters', []):
            if isinstance(sd.get('data'), dict):
                value = sd['data'].get(fd_attr)
                if value:
                    return value
        return None

    def _gather_windows_devices_general_info(self, request_content) -> Iterable[Tuple[Promise, str]]:
        """
        Runs wmi queries on windows devices to understand important stuff.
        :returns: true if successful, false otherwise.
        """

        logger.info('Gathering General info about windows devices - started.')
        '''
        1. Get a list of windows devices
        2. Get wmi queries to run from all subplugins
        2. Execute a wmi queries on them
        3. Pass the result to the subplugins
        '''
        # Initialize all of our subplugins
        subplugins_objects = [GetUserLogons, GetInstalledSoftwares,
                              GetBasicComputerInfo, GetConnectedHardware]
        if SHOULD_USE_AXR:
            logger.info('Using AXR to query patch management info')
            subplugins_objects.append(GetAvailableSecurityPatches)
        else:
            logger.info('Not querying patch management info using general info')

        self.subplugins_list = [con(self, logger) for con in subplugins_objects]
        self.subplugins_list.append(CheckReg(
            self, logger, reg_check_exists=request_content['command'].get('reg_check_exists') or [])
        )
        subplugins_objects.append(CheckReg)
        logger.info('Done initializing subplugins')

        internal_axon_ids = request_content['internal_axon_ids']  # a list of internal axon id's
        logger.info(f'Got {len(internal_axon_ids)} Windows devices to run queries on.')

        # Notice
        # internal_axon_id's are not consistent. If we have correlation, it will be incorrect.
        # Currently execution occurs only after correlation, and it takes less than a cycle (execution over 1 cycle
        # is not supported) so that's ok.
        logger.info(f'Approximate devices internal_axon_ids size in memory: {asizeof(internal_axon_ids)/(1024**2)} mb')

        # Lets make some better logging
        if len(internal_axon_ids) > 10000:
            log_message_device_count_threshold = 1000
        elif len(internal_axon_ids) > 1000:
            log_message_device_count_threshold = 100
        else:
            log_message_device_count_threshold = 50

        # We don't wanna burst thousands of queries here, so we are going to have a thread that always
        # keeps count of the number of requests, and shoot new ones in case needed.
        self.number_of_active_execution_requests = 0

        # Determine max number of execution requests. If we use the new execution method then pm_status isn't working,
        # we should raise our bar by 2.
        if SHOULD_USE_AXR:
            max_number_of_execution_requests = MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS * 2
        else:
            max_number_of_execution_requests = MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS

        device_i = 0
        for internal_axon_id in internal_axon_ids:
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
                    logger.error(f'Waited {self.seconds_stuck} seconds to continue sending more execution '
                                 f'requests but we still have {self.number_of_active_execution_requests} '
                                 f'threads active')
                    return False

            if device_i % log_message_device_count_threshold == 0:
                logger.info(f'Execution progress: {device_i} out of {len(internal_axon_ids)} devices executed')

            # shoot another one!
            self.number_of_active_execution_requests = self.number_of_active_execution_requests + 1
            # Caution! If we had correlation up to this point, we will have serious problems.

            logger.debug(f'Going to request action on {internal_axon_id}')

            custom_credentials = request_content.get('custom_credentials') or {}

            # Get all wmi queries from all subadapters.
            wmi_smb_commands = []
            for subplugin in subplugins_objects:
                wmi_smb_commands.extend(subplugin.get_wmi_smb_commands())

            # Now run all queries you have got on that device.
            if SHOULD_USE_AXR:
                p = self.request_action(
                    'execute_axr',
                    internal_axon_id,
                    {
                        'axr_commands': wmi_smb_commands,
                        'custom_credentials': custom_credentials
                    }
                )
            else:
                # fallback to old execution setting
                p = self.request_action(
                    'execute_wmi_smb',
                    internal_axon_id,
                    {
                        'wmi_smb_commands': wmi_smb_commands,
                        'custom_credentials': custom_credentials
                    }
                )

            wmi_state_promise = Promise()
            p.then(
                did_fulfill=functools.partial(self._handle_wmi_execution_success, internal_axon_id, wmi_state_promise),
                did_reject=functools.partial(self._handle_wmi_execution_failure, internal_axon_id, wmi_state_promise)
            )

            # Now run all queries you have got on that device.
            q = self.request_action(
                "execute_wmi_smb",
                internal_axon_id,
                {
                    "wmi_smb_commands": [{"type": "pmonline", "args": ["rpc_and_fallback_smb"]}],
                    'custom_credentials': custom_credentials
                }
            )
            pm_state_promise = Promise()
            q.then(
                did_fulfill=functools.partial(self._handle_pm_success, internal_axon_id, pm_state_promise),
                did_reject=functools.partial(self._handle_pm_failure, internal_axon_id, pm_state_promise)
            )

            yield Promise.all([wmi_state_promise, pm_state_promise]), internal_axon_id

    def _handle_wmi_execution_success(self, internal_axon_id, state_promise: Promise, data):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1

        # This has to be outside of the try, since the except and finally assume we have a device.
        # We need to get the device first.
        device = self.devices_db.find_one({'internal_axon_id': internal_axon_id})
        if device is None:
            logger.critical(f'Did not find document containing internal_axon_id {internal_axon_id}. '
                            f'Did we have correlation in place?')
            state_promise.do_resolve(False)
            return

        try:
            is_execution_exception = False
            last_execution_debug = None

            # Now get some info depending on the adapter that ran the execution
            executer_info = dict()
            executer_info['adapter_unique_name'] = data['responder']
            adapter_used = [adap for adap in device['adapters'] if adap[PLUGIN_UNIQUE_NAME]
                            == executer_info['adapter_unique_name']][0]
            executer_info['adapter_client_used'] = adapter_used['client_used']
            executer_info['adapter_unique_id'] = adapter_used['data']['id']

            # We have got many requests. Lets call the handler of each of our subplugins.
            # We go through the amount of queries each subplugin requested, linearly.
            queries_response = data['output']['product']
            queries_response_index = 0

            # Create a new device, since these subplugins will have some generic info enrichments.
            adapterdata_device = self._new_device_adapter()
            adapter_used_device_id = adapter_used['data']['id']
            adapterdata_device.id = f'{adapter_used[PLUGIN_UNIQUE_NAME]},{adapter_used_device_id}'

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
                        raise ValueError('return value is not True')
                except Exception:
                    try:
                        device_hostname = self.get_first_data(device, 'hostname')
                    except Exception:
                        device_hostname = device['internal_axon_id']
                    logger.exception(f'Subplugin {subplugin.__class__.__name__} exception.'
                                     f'Internal axon id is {device_hostname}. '
                                     f'Moving on to next plugin.')
                    all_error_logs.append(f'Subplugin {subplugin.__class__.__name__} exception: '
                                          f'{get_exception_string()}')

                # Update the response index.
                queries_response_index = queries_response_index + subplugin_num_queries

            # All of these plugins might have inserted new devices, lets get it.
            adapterdata_device.general_info_last_success_execution = datetime.now()
            new_data = adapterdata_device.to_dict()

            # Add the final one
            self.devices.add_adapterdata(
                [(executer_info['adapter_unique_name'], executer_info['adapter_unique_id'])], new_data,
                action_if_exists='update',  # If the tag exists, we update it using deep merge (and not replace it).
                client_used=executer_info['adapter_client_used']
            )
            self._save_field_names_to_db(EntityType.Devices)

            if len(all_error_logs) > 0:
                last_execution_debug = 'All errors logs: {0}'.format('\n'.join(all_error_logs))

        except Exception as e:
            logger.exception('An error occured while processing wmi result: {0}, {1}'
                             .format(str(e), get_exception_string()))
            last_execution_debug = f'An exception occured while processing wmi results: {get_exception_string()}'

        finally:
            state_promise.do_resolve(True)

            # If there is debug data to add, add it.
            if last_execution_debug is not None:
                last_execution_debug = last_execution_debug.replace('\\n', '\n')
                self.devices.add_data(
                    [(executer_info['adapter_unique_name'], executer_info['adapter_unique_id'])],
                    'Last Execution Debug', last_execution_debug
                )
            try:
                device_hostname = self.get_first_data(device, 'hostname')
                logger.info(f'WMI: Finished with device {device_hostname}.')
            except Exception:
                logger.exception(f'WMI: Finished with device {device["internal_axon_id"]}, can not understand hostname')

        if state_promise.is_pending:
            state_promise.do_resolve(False)

    def _handle_wmi_execution_failure(self, internal_axon_id, state_promise: Promise, exc):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
        device = self.devices_db.find_one({'internal_axon_id': internal_axon_id})
        if device is None:
            logger.critical(f'Did not find document containing internal_axon_id {internal_axon_id}. '
                            f'Did we have correlation in place?')
            state_promise.do_resolve("Device Error")
            return

        try:
            # Avidor: Someone decided that on failure we get an exception object, and not a real object.
            # God damn. Until i fix that, we do this very ugly thing...
            # TODO: Fix the whole god damn execution system

            try:
                device_hostname = self.get_first_data(device, 'hostname')
            except Exception:
                logger.exception(f'can not get device hostname {device}')
                device_hostname = device['internal_axon_id']

            if str(exc) == '{\'status\': \'failed\', \'output\': \'\'}':
                logger.debug(f'No executing adapters for device {device_hostname}, continuing')
                state_promise.do_resolve('Can not find adapter to execute with (wmi)')
                return

            logger.info('Failed running wmi query on device {0}! error: {1}'
                        .format(device_hostname, str(exc)))

            # We need to tag that device, but we have no associated adapter devices. we must use the first one.
            if len(device['adapters']) > 0:
                executer_info = dict()
                executer_info['adapter_unique_name'] = device['adapters'][0][PLUGIN_UNIQUE_NAME]
                executer_info['adapter_unique_id'] = device['adapters'][0]['data']['id']

                if 'connection refused' in str(exc).lower():
                    state_promise.do_resolve("Connection Error")

                else:
                    state_promise.do_resolve("Connection Exception")

                ex_str = str(exc).replace('\\n', '\n')

                self.devices.add_data(
                    [(executer_info['adapter_unique_name'], executer_info['adapter_unique_id'])],
                    'Last Execution Debug', f'Execution failed: {ex_str}'
                )
            else:
                state_promise.do_resolve(False)
        except Exception:
            logger.exception('Exception in failure.')
            state_promise.do_resolve("Exception")

        if state_promise.is_pending:
            state_promise.do_resolve(False)

    def _handle_pm_success(self, internal_axon_id, state_promise: Promise, data):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
        # This has to be outside of the try, since the except and finally assume we have a device.
        # We need to get the device first.
        device = self.devices_db.find_one({"internal_axon_id": internal_axon_id})
        if device is None:
            logger.critical(f"Did not find document containing internal_axon_id {internal_axon_id}. "
                            f"Did we have correlation in place?")
            state_promise.do_resolve(False)
            return

        try:
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
            self._save_field_names_to_db(EntityType.Devices)

            if len(all_error_logs) > 0:
                is_execution_exception = True
                last_pm_status_debug = "All errors logs: {0}".format("\n".join(all_error_logs))

        except Exception as e:
            logger.exception("An error occurred while processing pm result: {0}, {1}"
                             .format(str(e), get_exception_string()))
            is_execution_exception = True
            last_pm_status_debug = f"An exception occured while processing pm results: {get_exception_string()}"

        finally:
            state_promise.do_resolve(not is_execution_exception)
            # If there is debug data to add, add it.
            if last_pm_status_debug is not None:
                last_pm_status_debug = last_pm_status_debug.replace("\\n", "\n")
                self.devices.add_data(
                    [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                    "Last PM Status Debug", last_pm_status_debug
                )

            device_hostname = self.get_first_data(device, 'hostname')
            logger.info(f"PM: Finished with device {device_hostname}.")

        if state_promise.is_pending:
            state_promise.do_resolve(False)

    def _handle_pm_failure(self, internal_axon_id, state_promise: Promise, exc):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
        device = self.devices_db.find_one({"internal_axon_id": internal_axon_id})
        if device is None:
            logger.critical(f"Did not find document containing internal_axon_id {internal_axon_id}. "
                            f"Did we have correlation in place?")
            state_promise.do_resolve(False)
            return
        device_hostname = self.get_first_data(device, 'hostname')

        try:
            # Avidor: Someone decided that on failure we get an exception object, and not a real object.
            # God damn. Until i fix that, we do this very ugly thing...
            # TODO: Fix the whole god damn execution system

            if "{'status': 'failed', 'output': ''}" == str(exc):
                logger.debug(f"No executing adapters for device {device['internal_axon_id']}, continuing")
                state_promise.do_resolve('Can not find adapter to execute with (pm)')
                return

            logger.info("Failed running pm status on device {0}! error: {1}"
                        .format(device_hostname, str(exc)))

            # We need to tag that device, but we have no associated adapter devices. we must use the first one.
            if len(device["adapters"]) > 0:
                executer_info = dict()
                executer_info["adapter_unique_name"] = device["adapters"][0]["plugin_unique_name"]
                executer_info["adapter_unique_id"] = device["adapters"][0]["data"]["id"]

                ex_str = str(exc).replace("\\n", "\n")

                self.devices.add_data(
                    [(executer_info["adapter_unique_name"], executer_info["adapter_unique_id"])],
                    "Last PM Status Debug", f"Execution failed: {ex_str}"
                )

            state_promise.do_resolve(False)
        except Exception:
            logger.exception("Exception in failure.")
            state_promise.do_resolve(False)

        if state_promise.is_pending:
            state_promise.do_resolve(False)
