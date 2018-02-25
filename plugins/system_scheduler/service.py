import concurrent.futures
import threading
import dateutil.parser
from datetime import datetime
import requests
from enum import Enum, auto
from contextlib import contextmanager
from flask import jsonify
from apscheduler.executors.pool import ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.interval import IntervalTrigger

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts import adapter_consts
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.mixins.triggerable import Triggerable
import axonius.plugin_exceptions
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, SYSTEM_SCHEDULER_PLUGIN_NAME, AGGREGATOR_PLUGIN_NAME, PLUGIN_NAME
from axonius.utils.files import get_local_config_file


class Phases(Enum):
    Research = auto()
    Stable = auto()


class ResearchPhases(Enum):
    Fetch_Devices = auto()
    Fetch_Scanners = auto()
    RunPreCorrelationplugins = auto()
    RunCorrelations = auto()
    RunPostCorrelationplugins = auto()


class StateLevels(Enum):
    Phase = auto()
    SubPhase = auto()
    SubPhaseStatus = auto()


RESEARCH_THREAD_ID = 'phase_thread'


class SystemSchedulerService(PluginBase, Triggerable):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=SYSTEM_SCHEDULER_PLUGIN_NAME, *args, **kwargs)

        self.state = {
            StateLevels.Phase.name: Phases.Stable.name,
            StateLevels.SubPhase.name: None,
            StateLevels.SubPhaseStatus.name: None
        }
        self.system_research_rate = int(self.config['DEFAULT']['system_research_rate'])
        self.research_phase_lock = threading.RLock()
        self._research_phase_scheduler = None

        executors = {'default': ThreadPoolExecutorApscheduler(1)}
        self._research_phase_scheduler = LoggedBackgroundScheduler(self.logger, executors=executors)
        self._research_phase_scheduler.add_job(func=self._research_phase_thread,
                                               trigger=IntervalTrigger(minutes=self.system_research_rate),
                                               next_run_time=datetime.now(),
                                               name=RESEARCH_THREAD_ID,
                                               id=RESEARCH_THREAD_ID,
                                               max_instances=1)
        self._research_phase_scheduler.start()
        self._activate('execute')

    @add_rule('state', should_authenticate=False)
    def get_state(self):
        """
        Get plugin state.
        """
        return jsonify(self.state)

    @add_rule('research_rate', ['POST'])
    def set_system_research_rate(self):
        """
        Set the systems research rate (Originally taken from config).
        """
        data = self.get_request_data_as_object()
        if 'system_research_rate' not in data or not isinstance(data['system_research_rate'], int):
            return return_error('A new system_research_rate was not present in the request as a number', 400)

        self.system_research_rate = data['system_research_rate']

        self._research_phase_scheduler.reschedule_job(
            'phase_thread', trigger=IntervalTrigger(minutes=self.system_research_rate))

    @add_rule('sub_phase_update', ['POST'])
    def set_sub_phase_state(self):
        """
        Sets the sub_phase state (should be used by aggregator).
        :return:
        """
        received_update = self.get_request_data_as_object()
        self.logger.info(
            f"{self.get_caller_plugin_name()} notified that {received_update['adapter_name']} finished fetching data. f{received_update['num_of_adapters_left']} left.")
        self.state[StateLevels.SubPhaseStatus.name] = received_update['num_of_adapters_left']
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
            self.logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)

        time_to_research = datetime.now()

        if "timestamp" in post_json:
            try:
                time_to_research = dateutil.parser.parse(post_json["timestamp"])
                if time_to_research < datetime.now():
                    self.logger.info("Received an  earlier date to schedule a research phase.")
                    return return_error("The specified time as already occurred", 400)
            except Exception as err:
                self.logger.exception("Received a bad timestamp for scheduling a research phase.")
                return return_error("Failed to parse timestamp", 400)

        return self._schedule_research_phase(time_to_research)

    @contextmanager
    def _start_research(self):
        """
        A context manager that enters research phase if it's not already under way.
        :return:
        """
        if self.state[StateLevels.Phase.name] is Phases.Research.name:
            raise axonius.plugin_exceptions.PhaseExecutionException(f"{Phases.Research.name} is already executing.")
        else:
            with self.research_phase_lock:
                # Change current phase
                self.logger.info(f"Entered {Phases.Research.name} Phase.")
                self.current_phase = Phases.Research.name
                try:
                    yield
                except Exception:
                    self.logger.exception(f"Failed {Phases.Research.name} Phase.")
                finally:
                    self.current_phase = Phases.Stable.name
                    self.logger.info(f"Back to {Phases.Stable.name} Phase.")

    def _schedule_research_phase(self, time_to_run):
        """
        Makes the apscheduler schedule a research phase right now.
        :return:
        """
        research_job = self._research_phase_scheduler.get_job(RESEARCH_THREAD_ID)
        research_job.modify(next_run_time=time_to_run)
        self._research_phase_scheduler.wakeup()
        self.logger.info(f"Scheduling a  {Phases.Research.name} Phase.")
        return ""

    def _research_phase_thread(self):
        """
        Manages a research phase and it's sub phases.
        :return:
        """
        def _change_subphase(subphase_name):
            self.state[StateLevels.SubPhaseStatus.name] = subphase_name
            self.logger.info(f'Started Subphase {subphase_name}')

        with self._start_research():
            # Fetch Devices Data.
            _change_subphase(ResearchPhases.Fetch_Devices.name)
            self._run_aggregator_phase(adapter_consts.DEVICE_ADAPTER_PLUGIN_SUBTYPE)

            # Fetch Scanners Data.
            _change_subphase(ResearchPhases.Fetch_Scanners.name)
            self._run_aggregator_phase(adapter_consts.SCANNER_ADAPTER_PLUGIN_SUBTYPE)

            # Run Pre Correlation plugins.
            _change_subphase(ResearchPhases.RunPreCorrelationplugins.name)
            self._run_plugins('Pre-Correlation')

            # Run Correlations.
            _change_subphase(ResearchPhases.RunCorrelations.name)
            self._run_plugins('Correlator')

            _change_subphase(ResearchPhases.RunPostCorrelationplugins.name)
            self._run_plugins('Post-Correlation')

            self.logger.info(f"Finished {Phases.Research.name} Phase Successfuly.")

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
                self._run_blocking_request, 'trigger/execute', plugin[PLUGIN_UNIQUE_NAME], 'post'): plugin[PLUGIN_NAME] for plugin in plugins_to_run}

            for future in concurrent.futures.as_completed(future_for_pre_correlation_plugin):
                try:
                    future.result()
                    self.logger.info(f'{future_for_pre_correlation_plugin[future]} Finished Execution.')
                except Exception:
                    self.logger.error(f'Executing {future_for_pre_correlation_plugin[future]} Plugin Failed.')

    def _run_aggregator_phase(self, plugin_subtype):
        """
        Trigger "fetch_filtered_adapters" job in aggregator with plugin_subtype filter.
        :param plugin_subtype: A plugin_subtype to filter as a white list.
        :return:
        """
        self._run_blocking_request('trigger/fetch_filtered_adapters', AGGREGATOR_PLUGIN_NAME, 'post',
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
            self.logger.exception(
                f"Executing {args[1]} failed as part of {self.state[StateLevels.SubPhaseStatus.name]} subphase failed.")
            raise axonius.plugin_exceptions.PhaseExecutionException(
                f"Executing {args[1]} failed as part of {self.state[StateLevels.SubPhaseStatus.name]} subphase failed.")

    @property
    def plugin_subtype(self):
        return "Core"
