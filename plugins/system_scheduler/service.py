import logging
import threading
import time
from concurrent.futures import ALL_COMPLETED, wait, as_completed, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime

import requests
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.interval import IntervalTrigger
from axonius.consts.plugin_consts import PLUGIN_NAME

from axonius.plugin_exceptions import PhaseExecutionException
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts import plugin_consts, scheduler_consts
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.thread_stopper import StopThreadException, stoppable
from axonius.utils.files import get_local_config_file
from flask import jsonify
from retrying import retry

logger = logging.getLogger(f'axonius.{__name__}')

# Dict between plugin names that could run async and their respectful "pretty" names
ASYNCABLE_PLUGINS = {
    'general_info': 'General Info',
    'pm_status': 'PM Status'
}

# Plugins that should always run async
ALWAYS_ASYNC_PLUGINS = ['static_analysis']


class SystemSchedulerService(PluginBase, Triggerable, Configurable):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, *args, **kwargs)
        self.current_phase = scheduler_consts.Phases.Stable

        # whether or not stopping sequence has initiated
        self.__stopping_initiated = False

        self.state = dict(scheduler_consts.SCHEDULER_INIT_STATE)

        # This lock is held while the system is trying to stop
        self.__stopping_lock = threading.Lock()
        executors = {'default': ThreadPoolExecutorApscheduler(1)}
        self._research_phase_scheduler = LoggedBackgroundScheduler(executors=executors)
        self._research_phase_scheduler.add_job(func=self._trigger,
                                               trigger=IntervalTrigger(hours=self.__system_research_rate),
                                               next_run_time=datetime.now(),
                                               name=scheduler_consts.RESEARCH_THREAD_ID,
                                               id=scheduler_consts.RESEARCH_THREAD_ID,
                                               max_instances=1)
        self._research_phase_scheduler.start()

    @add_rule('state', should_authenticate=False)
    def get_state(self):
        """
        Get plugin state.
        """
        return jsonify({
            'state': self.state,
            'stopping': self.__stopping_initiated
        })

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
        logger.info(f'Loading SystemScheduler config: {config}')

        self.__plugin_settings = config['plugin_settings']

        for plugin_name in ALWAYS_ASYNC_PLUGINS:
            self.__plugin_settings[plugin_name] = {
                'enabled': True,
                'sync': False
            }

        self.__system_research_rate = float(config['discovery_settings']['system_research_rate'])
        logger.info(f'Setting research rate to: {self.__system_research_rate}')
        scheduler = getattr(self, '_research_phase_scheduler', None)
        self.__save_history = bool(config['discovery_settings']['save_history'])

        # first config load, no reschedule
        if not scheduler:
            return

        # reschedule
        # Saving next_run in order to restore it after 'reschedule_job' overrides this value. We want to restore
        # this value because updating schedule rate should't change the next scheduled time
        scheduler.reschedule_job(
            scheduler_consts.RESEARCH_THREAD_ID, trigger=IntervalTrigger(hours=self.__system_research_rate))

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'items': [
                        {
                            'name': 'system_research_rate',
                            'title': 'Schedule Rate (hours)',
                            'type': 'number'
                        },
                        {
                            'name': 'save_history',
                            'title': 'Should history be gathered',
                            'type': 'bool',
                            'required': True
                        },
                    ],
                    'name': 'discovery_settings',
                    'title': 'Discovery Settings',
                    'type': 'array'
                },
                {
                    'items': [
                        {
                            'items': [
                                {
                                    'name': 'enabled',
                                    'title': f'Use {pretty_name} plugin',
                                    'type': 'bool'
                                },
                                {
                                    'name': 'sync',
                                    'title': 'Wait until the plugin finished before continuing',
                                    'type': 'bool'
                                }
                            ],
                            'required': ['enabled', 'sync'],
                            'name': f'{name}',
                            'title': f'{pretty_name} Plugin Settings',
                            'type': 'array'
                        } for name, pretty_name in ASYNCABLE_PLUGINS.items()
                    ],
                    'type': 'array',
                    'name': 'plugin_settings',
                    'title': 'Specific Plugin Settings'
                }
            ],
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'discovery_settings': {
                'system_research_rate': 12,
                'save_history': True
            },
            'plugin_settings': {
                name: {
                    'enabled': True,
                    'sync': False
                }
                for name
                in ASYNCABLE_PLUGINS
            }
        }

    @add_rule('sub_phase_update', ['POST'])
    def set_sub_phase_state(self):
        """
        Sets the sub_phase state (should be used by aggregator).
        :return:
        """
        received_update = self.get_request_data_as_object()
        logger.info(
            f'{self.get_caller_plugin_name()} notified that {received_update["adapter_name"]} finished fetching data.'
            f' {received_update["portion_of_adapters_left"]} left.')
        self.state[scheduler_consts.StateLevels.SubPhaseStatus.name] = received_update['portion_of_adapters_left']
        return ''

    def _triggered(self, job_name: str, post_json: dict, *args):
        """
        The function that runs jobs as part of the triggerable mixin,
        Currently supports only 'execute' which triggers a research right away.
        :param job_name: The job to execute.
        :param post_json: data for the job.
        :param args:
        :return:
        """
        if job_name != 'execute':
            logger.error(f'Got bad trigger request for non-existent job: {job_name}')
            return return_error('Got bad trigger request for non-existent job', 400)

        self.__start_research()

    @contextmanager
    def _start_research(self):
        """
        A context manager that enters research phase if it's not already under way.
        :return:
        """
        if self.state[scheduler_consts.StateLevels.Phase.name] is scheduler_consts.Phases.Research.name:
            raise PhaseExecutionException(
                f'{scheduler_consts.Phases.Research.name} is already executing.')
        if self.__stopping_initiated:
            logger.info("Stopping initiated, not running")
            return
        else:
            # Change current phase
            logger.info(f'Entered {scheduler_consts.Phases.Research.name} Phase.')
            self.current_phase = scheduler_consts.Phases.Research
            try:
                yield
            except StopThreadException:
                logger.info('Stopped execution')
            except BaseException:
                logger.exception(f'Failed {scheduler_consts.Phases.Research.name} Phase.')
            finally:
                self.current_phase = scheduler_consts.Phases.Stable
                logger.info(f'Back to {scheduler_consts.Phases.Stable} Phase.')
                self.state = dict(scheduler_consts.SCHEDULER_INIT_STATE)

    @stoppable
    def __start_research(self):
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
            self._run_aggregator_phase(PluginSubtype.AdapterBase)

            # Fetch Scanners Data.
            _change_subphase(scheduler_consts.ResearchPhases.Fetch_Scanners)
            self._run_aggregator_phase(PluginSubtype.ScannerAdapter)

            # Clean old devices.
            _change_subphase(scheduler_consts.ResearchPhases.Clean_Devices)
            self._run_cleaning_phase()

            # Run Pre Correlation plugins.
            _change_subphase(scheduler_consts.ResearchPhases.Pre_Correlation)
            self._run_plugins(PluginSubtype.PreCorrelation)

            # Run Correlations.
            _change_subphase(scheduler_consts.ResearchPhases.Run_Correlations)
            self._run_plugins(PluginSubtype.Correlator)

            self._request_db_rebuild(sync=True)

            _change_subphase(scheduler_consts.ResearchPhases.Post_Correlation)
            self._run_plugins(PluginSubtype.PostCorrelation)

            if self.__save_history:
                # Save history.
                _change_subphase(scheduler_consts.ResearchPhases.Save_Historical)
                self._run_historical_phase()

            self._request_db_rebuild(sync=True)
            logger.info(f'Finished {scheduler_consts.Phases.Research.name} Phase Successfully.')

    def _get_plugins(self, plugin_subtype: PluginSubtype):
        """
        Get registered plugins from core, filtered by plugin_subtype.
        :param plugin_subtype: A plugin_subtype to filter.
        :return:
        """
        registered_plugins = requests.get(self.core_address + '/register')
        registered_plugins.raise_for_status()
        return [plugin for plugin in registered_plugins.json().values() if
                plugin['plugin_subtype'] == plugin_subtype.value]

    def _run_plugins(self, plugin_subtype: PluginSubtype):
        """
        Trigger execute asynchronously in filtered plugins.
        :param plugin_subtype: A plugin_subtype to filter.
        :return:
        """
        def run_trigger_on_plugin(plugin: dict):
            """
            Performs trigger/execute according to what we want
            :param plugin: the plugin dict as returned from /register
            """
            blocking = True
            plugin_settings = self.__plugin_settings.get(plugin[PLUGIN_NAME])
            if plugin_settings:
                if not plugin_settings['enabled']:
                    return
                if not plugin_settings['sync']:
                    blocking = False

            self._run_blocking_request(
                f'trigger/execute?blocking={blocking}',
                plugin[plugin_consts.PLUGIN_UNIQUE_NAME],
                'post')

        plugins_to_run = self._get_plugins(plugin_subtype)
        with ThreadPoolExecutor() as executor:

            future_for_pre_correlation_plugin = {
                executor.submit(run_trigger_on_plugin, plugin):
                    plugin[plugin_consts.PLUGIN_NAME] for plugin in plugins_to_run
            }

            for future in as_completed(future_for_pre_correlation_plugin):
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

    def _run_historical_phase(self):
        """
        Trigger saving history
        :return:
        """
        self._run_blocking_request('trigger/save_history', plugin_consts.AGGREGATOR_PLUGIN_NAME, 'post')

    def _run_aggregator_phase(self, plugin_subtype: PluginSubtype):
        """
        Trigger 'fetch_filtered_adapters' job in aggregator with plugin_subtype filter.
        :param plugin_subtype: A plugin_subtype to filter as a white list.
        :return:
        """
        self._run_blocking_request('trigger/fetch_filtered_adapters', plugin_consts.AGGREGATOR_PLUGIN_NAME, 'post',
                                   json={'plugin_subtype': plugin_subtype.value})

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
                f'Executing {args[1]} failed as part of '
                f'{self.state[scheduler_consts.StateLevels.SubPhase.name]} subphase failed.')
            raise PhaseExecutionException(
                f'Executing {args[1]} failed as part of '
                f'{self.state[scheduler_consts.StateLevels.SubPhase.name]} subphase failed.')

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.Core

    def stop_research_phase(self):
        with self.__stopping_lock:
            try:
                self.__stopping_initiated = True

                @retry(stop_max_attempt_number=50, wait_fixed=300, retry_on_result=lambda result: result is False)
                def _wait_for_stable():
                    return self.current_phase == scheduler_consts.Phases.Stable

                logger.info(f'received stop request for plugin: {self.plugin_unique_name}')
                try:
                    self._stop_plugins()
                except Exception:
                    logger.exception('An exception was raised while stopping all plugins')
                try:
                    _wait_for_stable()
                except Exception:
                    logger.exception('Couldn\'t stop plugins for more than a while - forcing stop')
                    self.current_phase = scheduler_consts.Phases.Stable
                    self.state = dict(scheduler_consts.SCHEDULER_INIT_STATE)
                    logger.info(f'{self.current_phase} and {self.state}')
                    self._restore_to_running_state()
                else:
                    logger.info("Finished waiting for stable")

            finally:
                self.__stopping_initiated = False

    @add_rule('stop_all', should_authenticate=False, methods=['POST'])
    def stop_all(self):
        if self.__stopping_initiated:
            logger.info("Already stopping")
            return '', 204

        logger.info(f'Received stop_all - starting to stop - {self.__stopping_lock}')
        try:
            self._unschedule()
            self.stop_research_phase()
        except Exception:
            logger.exception('Exception while stopping')
        finally:
            logger.info('Finished stopping all')
            # Let's rebuild once at the end for precaution
            self._request_db_rebuild(sync=False)
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
                response = self.request_remote_plugin('stop_plugin', plugin, timeout=20)
                if response.status_code != 204:
                    logger.error(f'{plugin} didn\'t stop properly, returned: {response.content}')
            except Exception:
                logger.exception(f'error stopping {plugin}')

        plugins_to_stop = frozenset(self.get_all_plugins())
        if len(plugins_to_stop) == 0:
            return
        logger.info(f'Starting {len(plugins_to_stop)} worker threads.')
        with ThreadPoolExecutor(max_workers=len(plugins_to_stop)) as executor:
            try:
                futures = []
                # Creating a future for all the device summaries to be executed by the executors.
                for plugin in plugins_to_stop:
                    futures.append(executor.submit(
                        _stop_plugin, plugin))

                wait(futures, timeout=None, return_when=ALL_COMPLETED)
            except Exception as err:
                logger.exception('An exception was raised while stopping all plugins.')

        logger.info('Finished stopping all plugins.')
