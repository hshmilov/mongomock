import time
import threading
import functools
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from axonius.plugin_base import PluginBase, add_rule
from axonius.mixins.activatable import Activatable
from axonius.mixins.triggerable import Triggerable
from axonius.parsing_utils import get_exception_string
from subplugins.last_user_logon import GetLastUserLogon
from subplugins.installed_softwares import GetInstalledSoftwares
from subplugins.basic_computer_info import GetBasicComputerInfo
from datetime import datetime


MAX_NUMBER_OF_CONCURRENT_EXECUTION_REQUESTS = 20
SECONDS_TO_SLEEP_IF_TOO_MUCH_EXECUTION_REQUESTS = 5


class GeneralInfoPlugin(PluginBase, Activatable, Triggerable):
    def _is_work_in_progress(self) -> bool:

        if self.work_lock.acquire(False):
            self.work_lock.release()
            return False
        return True

    def _stop_activatable(self):
        assert self.scheduler is not None, "general_info_plugin is not running"

        self.is_enabled = False
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=True)
        self.scheduler = None

    def _start_activatable(self):
        """
        Start the scheduler
        :return:
        """
        assert self.scheduler is None, "general_info_plugin is already running"

        self.is_enabled = True
        executors = {'default': ThreadPoolExecutor(1)}
        self.scheduler = BackgroundScheduler(executors=executors)
        self.scheduler.add_job(func=self._general_info_thread,
                               trigger=IntervalTrigger(hours=1),
                               next_run_time=datetime.now(),
                               name='general_info',
                               id='general_info',
                               max_instances=1)
        self.scheduler.start()

    def _triggered(self, job_name, post_json):
        """
        Returns any errors as-is.
        :return:
        """

        acquired = False
        try:
            if self.work_lock.acquire(False):
                acquired = True
                self._general_info_thread()
            else:
                raise RuntimeError("General info gathering is already taking place, try again later")
        finally:
            if acquired:
                self.work_lock.release()

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self.work_lock = threading.RLock()
        self.is_enabled = False  # Are we enabled?
        self.scheduler = None
        self._execution_manager_lock = threading.Lock()  # This is not an RLock. it can be acquired only once.
        self._number_of_active_execution_requests_var = 0  # Number of active execution requests
        self.subplugins = []  # All of our subplugins.

        self.activatable_start_if_needed()

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

    def _general_info_thread(self):
        """
        Runs wmi queries on windows devices to understand important stuff.
        """

        self.logger.info("General info thread started.")
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
                # Go through all devices, and when the time is right, shoot a request.
                if self.is_enabled is False:
                    # A shutdown request (through the Activatable interface)
                    # has been sent, we must exit gracefully. So do not continue.
                    return

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

            for subplugin in self.subplugins:
                subplugin_num_queries = len(subplugin.get_wmi_commands())
                subplugin_result = queries_response[queries_response_index:
                                                    queries_response_index + subplugin_num_queries]
                subplugin.handle_result(device, executer_info, subplugin_result)

                # Update the response index.
                queries_response_index = queries_response_index + subplugin_num_queries

        except Exception as e:
            self.logger.exception("An error occured while processing wmi result: {0}, {1}"
                                  .format(str(e), get_exception_string()))

    def _handle_wmi_execution_failure(self, device, exc):
        self.number_of_active_execution_requests = self.number_of_active_execution_requests - 1
        self.logger.info("Failed running wmi query on device {0}! error: {1}"
                         .format(device["internal_axon_id"], str(exc)))

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
