import logging

from axonius.entities import EntityType
from axonius.mixins.configurable import Configurable
from axonius.utils.parsing import parse_filter

logger = logging.getLogger(f"axonius.{__name__}")
import concurrent.futures
from retrying import retry
from concurrent.futures import ALL_COMPLETED, wait
import threading
import dateutil.parser
from datetime import datetime, timezone
import time
import requests
from contextlib import contextmanager
from flask import jsonify
from apscheduler.executors.pool import ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.interval import IntervalTrigger

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts import adapter_consts
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.thread_stopper import stoppable
from axonius.mixins.triggerable import Triggerable
import axonius.plugin_exceptions
from axonius.consts import plugin_consts
from axonius.utils.files import get_local_config_file
from axonius.consts import scheduler_consts


class SystemSchedulerService(PluginBase, Triggerable, Configurable):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, *args, **kwargs)
        self.current_phase = scheduler_consts.Phases.Stable.name

        self.state = dict(scheduler_consts.SCHEDULER_INIT_STATE)
        self.research_phase_lock = threading.RLock()
        executors = {'default': ThreadPoolExecutorApscheduler(1)}
        self._research_phase_scheduler = LoggedBackgroundScheduler(executors=executors)
        self._research_phase_scheduler.add_job(func=self._restart_research,
                                               trigger=IntervalTrigger(hours=self.__system_research_rate),
                                               next_run_time=datetime.now(),
                                               name=scheduler_consts.RESEARCH_THREAD_ID,
                                               id=scheduler_consts.RESEARCH_THREAD_ID,
                                               max_instances=1)
        self._research_phase_scheduler.start()
        self._activate('execute')

    @add_rule('state', should_authenticate=False)
    def get_state(self):
        """
        Get plugin state.
        """
        return jsonify(self.state)

    @add_rule('next_run_time', should_authenticate=False)
    def get_next_run_time(self):
        """
        Calculates next run time by adding research rate seconds to the time last run time
        :return: The time next research is supposed to start running
        """
        next_run_time = self._research_phase_scheduler.get_job(
            scheduler_consts.RESEARCH_THREAD_ID).next_run_time
        return str(int(time.mktime(next_run_time.timetuple())))

    def _on_config_update(self, config):
        logger.info(f"Loading SystemScheduler config: {config}")
        self.__system_research_rate = float(config['system_research_rate'])
        logger.info(f"Setting research rate to: {self.__system_research_rate}")
        scheduler = getattr(self, '_research_phase_scheduler', None)

        # first config load, no reschedule
        if not scheduler:
            return

        # reschedule
        scheduler.reschedule_job(
            scheduler_consts.RESEARCH_THREAD_ID, trigger=IntervalTrigger(hours=self.__system_research_rate))

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    "name": "system_research_rate",
                    "title": "Schedule Rate (hours)",
                    "type": "number"
                },
                {
                    "name": "generate_report",
                    "title": "Automatically Generate Report after Discovery Phase - Warning: turning off this feature can result in very long download times for executive reports.",
                    "type": "bool",
                    "required": True
                }
            ],
            "pretty_name": "Scheduler Configuration",
            "title": "Discovery Settings",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            "system_research_rate": 12,
            "generate_report": True
        }

    @add_rule('sub_phase_update', ['POST'])
    def set_sub_phase_state(self):
        """
        Sets the sub_phase state (should be used by aggregator).
        :return:
        """
        received_update = self.get_request_data_as_object()
        logger.info(
            f"{self.get_caller_plugin_name()} notified that {received_update['adapter_name']} finished fetching data. {received_update['portion_of_adapters_left']} left.")
        self.state[scheduler_consts.StateLevels.SubPhaseStatus.name] = received_update['portion_of_adapters_left']
        return ''

    def _triggered(self, job_name: str, post_json: dict, *args):
        """
        The function that runs jobs as part of the triggerable mixin,
        Currently supports only "execute" which triggers a research right away.
        :param job_name: The job to execute.
        :param post_json: data for the job.
        :param args:
        :return:
        """
        if job_name != 'execute':
            logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)

        time_to_research = datetime.now()

        if post_json and "timestamp" in post_json:
            try:
                time_to_research = dateutil.parser.parse(post_json["timestamp"])
                if time_to_research < datetime.now():
                    logger.info("Received an  earlier date to schedule a research phase.")
                    return return_error("The specified time as already occurred", 400)
            except Exception as err:
                logger.exception("Received a bad timestamp for scheduling a research phase.")
                return return_error("Failed to parse timestamp", 400)

        return self._schedule_research_phase(time_to_research)

    @contextmanager
    def _start_research(self):
        """
        A context manager that enters research phase if it's not already under way.
        :return:
        """
        if self.state[scheduler_consts.StateLevels.Phase.name] is scheduler_consts.Phases.Research.name:
            raise axonius.plugin_exceptions.PhaseExecutionException(
                f"{scheduler_consts.Phases.Research.name} is already executing.")
        else:
            with self.research_phase_lock:
                # Change current phase
                logger.info(f"Entered {scheduler_consts.Phases.Research.name} Phase.")
                self.current_phase = scheduler_consts.Phases.Research.name
                try:
                    yield
                except Exception:
                    logger.exception(f"Failed {scheduler_consts.Phases.Research.name} Phase.")
                finally:
                    self.current_phase = scheduler_consts.Phases.Stable.name
                    logger.info(f"Back to {scheduler_consts.Phases.Stable.name} Phase.")
                    self.state = dict(scheduler_consts.SCHEDULER_INIT_STATE)

    def _schedule_research_phase(self, time_to_run):
        """
        Makes the apscheduler schedule a research phase right now.
        :return:
        """
        research_job = self._research_phase_scheduler.get_job(scheduler_consts.RESEARCH_THREAD_ID)
        research_job.modify(next_run_time=time_to_run)
        self._research_phase_scheduler.wakeup()
        logger.info(f"Scheduling a {scheduler_consts.Phases.Research.name} Phase for {time_to_run}.")
        return ""

    def _restart_research(self):
        self.stop_research_phase()
        self._research_phase_thread()

    @stoppable
    def _research_phase_thread(self):
        """
        Manages a research phase and it's sub phases.
        :return:
        """

        def _change_subphase(subphase: scheduler_consts.ResearchPhases):
            self.state[scheduler_consts.StateLevels.SubPhase.name] = subphase.name
            logger.info(f'Started Subphase {subphase}')

        with self._start_research():
            self.state[scheduler_consts.StateLevels.Phase.name] = scheduler_consts.Phases.Research.name

            # Fetch Devices Data.
            _change_subphase(scheduler_consts.ResearchPhases.Fetch_Devices)
            self._run_aggregator_phase(adapter_consts.DEVICE_ADAPTER_PLUGIN_SUBTYPE)

            # Fetch Scanners Data.
            _change_subphase(scheduler_consts.ResearchPhases.Fetch_Scanners)
            self._run_aggregator_phase(adapter_consts.SCANNER_ADAPTER_PLUGIN_SUBTYPE)

            # Clean old devices.
            _change_subphase(scheduler_consts.ResearchPhases.Clean_Devices)
            self._run_cleaning_phase()

            # Run Pre Correlation plugins.
            _change_subphase(scheduler_consts.ResearchPhases.Pre_Correlation)
            self._run_plugins('Pre-Correlation')

            # Run Correlations.
            _change_subphase(scheduler_consts.ResearchPhases.Run_Correlations)
            self._run_plugins('Correlator')

            _change_subphase(scheduler_consts.ResearchPhases.Post_Correlation)
            self._run_plugins('Post-Correlation')

            logger.info(f"Finished {scheduler_consts.Phases.Research.name} Phase Successfuly.")

    def _get_plugins(self, plugin_subtype):
        """
        Get registered plugins from core, filtered by plugin_subtype.
        :param plugin_subtype: A plugin_subtype to filter.
        :return:
        """
        registered_plugins = requests.get(self.core_address + '/register')
        registered_plugins.raise_for_status()
        return [plugin for plugin in registered_plugins.json().values() if
                plugin['plugin_subtype'] == plugin_subtype]

    def _run_plugins(self, plugin_subtype):
        """
        Trigger execute asynchronously in filtered plugins.
        :param plugin_subtype: A plugin_subtype to filter.
        :return:
        """
        plugins_to_run = self._get_plugins(plugin_subtype)
        with concurrent.futures.ThreadPoolExecutor() as executor:

            future_for_pre_correlation_plugin = {executor.submit(
                self._run_blocking_request, 'trigger/execute', plugin[plugin_consts.PLUGIN_UNIQUE_NAME], 'post'): plugin[plugin_consts.PLUGIN_NAME] for plugin in plugins_to_run}

            for future in concurrent.futures.as_completed(future_for_pre_correlation_plugin):
                try:
                    future.result()
                    logger.info(f'{future_for_pre_correlation_plugin[future]} Finished Execution.')
                except Exception:
                    logger.exception(f'Executing {future_for_pre_correlation_plugin[future]} Plugin Failed.')

    def _run_cleaning_phase(self):
        """
        Trigger cleaning all devices from all adapters
        :return:
        """
        self._run_blocking_request('trigger/clean_db', plugin_consts.AGGREGATOR_PLUGIN_NAME, 'post')

    def _run_aggregator_phase(self, plugin_subtype):
        """
        Trigger "fetch_filtered_adapters" job in aggregator with plugin_subtype filter.
        :param plugin_subtype: A plugin_subtype to filter as a white list.
        :return:
        """
        self._run_blocking_request('trigger/fetch_filtered_adapters', plugin_consts.AGGREGATOR_PLUGIN_NAME, 'post',
                                   json={'plugin_subtype': plugin_subtype})

    def _run_blocking_request(self, *args, **kwargs):
        """
        Runs a blocking http request and examines it's status_code response for failures.
        :param args:
        :param kwargs:
        :return:
        """
        response = self.request_remote_plugin(*args, **kwargs)
        # 403 is a disabled plugin.
        if response.status_code not in (200, 403):
            logger.exception(
                f"Executing {args[1]} failed as part of {self.state[scheduler_consts.StateLevels.SubPhase.name]} subphase failed.")
            raise axonius.plugin_exceptions.PhaseExecutionException(
                f"Executing {args[1]} failed as part of {self.state[scheduler_consts.StateLevels.SubPhase.name]} subphase failed.")

    @property
    def plugin_subtype(self):
        return "Core"

    def stop_research_phase(self):
        @retry(stop_max_attempt_number=100, wait_fixed=1000, retry_on_result=lambda result: result is False)
        def _wait_for_stable():
            return self.current_phase == scheduler_consts.Phases.Stable.name
        logger.info(f"received stop request for plugin: {self.plugin_unique_name}")
        try:
            self._stop_plugins()
        except Exception:
            logger.exception('An exception was raised while stopping all plugins')
        try:
            _wait_for_stable()
        except Exception:
            logger.exception("Couldn't stop plugins for more than a 100 seconds")
            raise axonius.plugin_exceptions.PluginException("Couldn't stop plugins for more than a 100 seconds")

    @add_rule('stop_all', should_authenticate=False, methods=['POST'])
    def stop_all(self):
        self.stop_research_phase()
        return '', 204

    def get_all_plugins(self):
        """
        :return: all the currently registered plugins - used when we want to stop everything in the system towards a
                 clean discovery phase
        """
        plugins_available = requests.get(self.core_address + '/register').json()
        for plugin_unique_name in plugins_available:
            yield plugin_unique_name

    def _stop_plugins(self):
        """
        For each plugin in the system create a stop_plugin request.
        It does so asynchronously and waits for every plugin to return ensuring the system is always displaying its
        correct state - not in stable state until it really is.
        """
        def _stop_plugin(plugin):
            try:
                logger.debug(f'stopping {plugin}')
                response = self.request_remote_plugin('stop_plugin', plugin)
                if response.status_code != 204:
                    logger.error(f"{plugin} didn't stop properly, returned: {response.content}")
            except Exception:
                logger.exception(f'error stopping {plugin}')
                pass

        plugins_to_stop = frozenset(self.get_all_plugins())
        if len(plugins_to_stop) == 0:
            return
        logger.info("Starting {0} worker threads.".format(len(plugins_to_stop)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(plugins_to_stop)) as executor:
            try:
                futures = []
                # Creating a future for all the device summaries to be executed by the executors.
                for plugin in plugins_to_stop:
                    futures.append(executor.submit(
                        _stop_plugin, plugin))

                wait(futures, timeout=None, return_when=ALL_COMPLETED)
            except Exception as err:
                logger.exception("An exception was raised while stopping all plugins.")

        logger.info("Finished stopping all plugins.")
