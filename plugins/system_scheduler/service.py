import logging
import threading
import time
from concurrent.futures import ALL_COMPLETED, wait, as_completed, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime

from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.interval import IntervalTrigger
from axonius.adapter_base import AdapterBase

from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME, CONFIGURABLE_CONFIGS_COLLECTION, \
    STATIC_CORRELATOR_PLUGIN_NAME, CORE_UNIQUE_NAME
from axonius.consts.scheduler_consts import SchedulerState

from axonius.plugin_exceptions import PhaseExecutionException
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts import plugin_consts, scheduler_consts, adapter_consts
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.thread_stopper import StopThreadException
from axonius.utils.files import get_local_config_file
from flask import jsonify

logger = logging.getLogger(f'axonius.{__name__}')

# Plugins that should always run async
ALWAYS_ASYNC_PLUGINS = ['static_analysis', 'general_info', 'pm_status']


class SystemSchedulerService(Triggerable, PluginBase, Configurable):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=plugin_consts.SYSTEM_SCHEDULER_PLUGIN_NAME, *args, **kwargs)
        self.current_phase = scheduler_consts.Phases.Stable

        # whether or not stopping sequence has initiated
        self.__stopping_initiated = False

        self.state = SchedulerState()

        # this lock is held while the system performs a rt process or a process that musn't run in parallel
        # to fetching or correlation
        self.__realtime_lock = threading.Lock()

        # This lock is held while the system is trying to stop
        self.__stopping_lock = threading.Lock()
        executors = {'default': ThreadPoolExecutorApscheduler(1)}
        self._research_phase_scheduler = LoggedBackgroundScheduler(executors=executors)
        self._research_phase_scheduler.add_job(func=self._trigger,
                                               trigger=IntervalTrigger(hours=self.__system_research_rate),
                                               name=scheduler_consts.RESEARCH_THREAD_ID,
                                               id=scheduler_consts.RESEARCH_THREAD_ID,
                                               max_instances=1)
        self._research_phase_scheduler.start()

        self.__realtime_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutorApscheduler(1)})
        self.__realtime_scheduler.add_job(func=self.__run_realtime_adapters,
                                          trigger=IntervalTrigger(seconds=30),
                                          next_run_time=datetime.now(),
                                          max_instances=1)
        self.__realtime_scheduler.start()

    @add_rule('state', should_authenticate=False)
    def get_state(self):
        """
        Get plugin state.
        """
        next_run_time = self._research_phase_scheduler.get_job(
            scheduler_consts.RESEARCH_THREAD_ID).next_run_time
        return jsonify({
            'state': self.state._asdict(),
            'stopping': self.__stopping_initiated,
            'next_run_time': time.mktime(next_run_time.timetuple())
        })

    def _on_config_update(self, config):
        logger.info(f'Loading SystemScheduler config: {config}')

        self.__constant_alerts = config['discovery_settings']['constant_alerts']
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
                        {
                            'name': 'constant_alerts',
                            'title': 'Always run Alerts',
                            'type': 'bool',
                            'required': True
                        }
                    ],
                    'name': 'discovery_settings',
                    'title': 'Discovery Settings',
                    'type': 'array'
                }
            ],
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'discovery_settings': {
                'system_research_rate': 12,
                'save_history': True,
                'constant_alerts': False
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
        with self.__realtime_lock:
            self.state.SubPhaseStatus = received_update['portion_of_adapters_left']
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

        logger.info(f'Started system scheduler')
        self.__start_research()

    @contextmanager
    def _start_research(self):
        """
        A context manager that enters research phase if it's not already under way.
        :return:
        """
        if self.state.Phase is scheduler_consts.Phases.Research:
            raise PhaseExecutionException(
                f'{scheduler_consts.Phases.Research.name} is already executing.')
        if self.__stopping_initiated:
            logger.info("Stopping initiated, not running")
            return
        else:
            # Change current phase
            self.current_phase = scheduler_consts.Phases.Research
            if self._notify_on_adapters is True:
                self.create_notification(f'Entered {scheduler_consts.Phases.Research.name} Phase.')
            self.send_external_info_log(f'Entered {scheduler_consts.Phases.Research.name} Phase.')
            logger.info(f'Entered {scheduler_consts.Phases.Research.name} Phase.')
            try:
                yield
            except StopThreadException:
                logger.info('Stopped execution')
                raise
            except BaseException:
                logger.exception(f'Failed {scheduler_consts.Phases.Research.name} Phase.')
                raise
            finally:
                logger.info(f'Back to {scheduler_consts.Phases.Stable} Phase.')
                self.current_phase = scheduler_consts.Phases.Stable
                self.state = SchedulerState()

    def __start_research(self):
        """
        Manages a research phase and it's sub phases.
        :return:
        """

        def _change_subphase(subphase: scheduler_consts.ResearchPhases):
            with self.__realtime_lock:
                self.state.SubPhase = subphase

            logger.info(f'Started Subphase {subphase}')
            if self._notify_on_adapters is True:
                self.create_notification(f'Started Subphase {subphase}')
            self.send_external_info_log(f'Started Subphase {subphase}')

        with self._start_research():
            self.state.Phase = scheduler_consts.Phases.Research
            _change_subphase(scheduler_consts.ResearchPhases.Fetch_Devices)

            try:
                # this is important and is described at https://axonius.atlassian.net/wiki/spaces/AX/pages/799211552/
                self.request_remote_plugin('wait/execute', 'reports')
            except Exception as e:
                logger.exception(f'Failed waiting for alerts before cycle {e}')

            # Fetch Devices Data.
            self._run_aggregator_phase(PluginSubtype.AdapterBase)
            self._request_gui_dashboard_cache_clear()

            # Fetch Scanners Data.
            _change_subphase(scheduler_consts.ResearchPhases.Fetch_Scanners)
            self._run_aggregator_phase(PluginSubtype.ScannerAdapter)

            # Clean old devices.
            _change_subphase(scheduler_consts.ResearchPhases.Clean_Devices)
            self._request_gui_dashboard_cache_clear()

            for adapter in self.__get__all_adapters():
                try:
                    # this is important and is described at
                    # https://axonius.atlassian.net/wiki/spaces/AX/pages/799211552/
                    self.request_remote_plugin('wait/insert_to_db', adapter[PLUGIN_UNIQUE_NAME])
                except Exception as e:
                    logger.exception(f'Failed waiting for adapter cycle {e}')

            self._run_cleaning_phase()

            # Run Pre Correlation plugins.
            _change_subphase(scheduler_consts.ResearchPhases.Pre_Correlation)
            self._run_plugins(PluginSubtype.PreCorrelation)

            # Run Correlations.
            _change_subphase(scheduler_consts.ResearchPhases.Run_Correlations)
            self._run_plugins(PluginSubtype.Correlator)

            self._request_db_rebuild(sync=True)
            self._request_gui_dashboard_cache_clear()

            _change_subphase(scheduler_consts.ResearchPhases.Post_Correlation)
            self._run_plugins(PluginSubtype.PostCorrelation)

            if self.__save_history:
                # Save history.
                _change_subphase(scheduler_consts.ResearchPhases.Save_Historical)
                self._run_historical_phase()

            self._request_db_rebuild(sync=True)
            self._request_gui_dashboard_cache_clear(clear_slow=True)

            logger.info(f'Finished {scheduler_consts.Phases.Research.name} Phase Successfully.')
            if self._notify_on_adapters is True:
                self.create_notification(f'Finished {scheduler_consts.Phases.Research.name} Phase Successfully.')
            self.send_external_info_log(f'Finished {scheduler_consts.Phases.Research.name} Phase Successfully.')

    def __get__all_adapters(self):
        with self._get_db_connection() as db_connection:
            return list(db_connection[CORE_UNIQUE_NAME]['configs'].find({
                'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE
            }
            ))

    def __get_all_realtime_adapters(self):
        with self._get_db_connection() as db_connection:
            for adapter in self.__get__all_adapters():
                config = db_connection[adapter[PLUGIN_UNIQUE_NAME]][CONFIGURABLE_CONFIGS_COLLECTION].find_one({
                    'config_name': AdapterBase.__name__
                })
                if config:
                    config = config.get('config')
                    if config:
                        if config.get('realtime_adapter'):
                            yield adapter

    def __run_realtime_adapters(self):
        """
        Triggers realtime adapters and correlations as long as a cycle hasn't taken place
        :return:
        """
        with self.__realtime_lock:
            try:
                if self.state.SubPhase is None:
                    # Not in cycle - can do all
                    should_trigger_plugins = True
                    should_fetch_rt_adapter = True

                elif self.state.SubPhase in [scheduler_consts.ResearchPhases.Fetch_Devices,
                                             scheduler_consts.ResearchPhases.Fetch_Scanners]:
                    # In cycle and fetching entities - no alerts for consistency
                    should_trigger_plugins = False
                    should_fetch_rt_adapter = True

                else:
                    # In cycle and after fetching entities - can't do anything for consistency
                    should_trigger_plugins = False
                    should_fetch_rt_adapter = False

                logger.info(f'RT Cycle, plugins - {should_trigger_plugins} and adapters - {should_fetch_rt_adapter} '
                            f'state - {self.state}')
                if should_fetch_rt_adapter:
                    adapters_to_call = list(self.__get_all_realtime_adapters())
                    if not adapters_to_call:
                        logger.info('No adapters to call, not doing anything at all')
                        return

                    for adapter_to_call in adapters_to_call:
                        logger.info(f'Fetching from rt adapter {adapter_to_call[PLUGIN_UNIQUE_NAME]}')
                        try:
                            self.request_remote_plugin(
                                'trigger/insert_to_db?blocking=False',
                                adapter_to_call[PLUGIN_UNIQUE_NAME],
                                'post')
                        except Exception as e:
                            logger.exception(f'Failed triggering {plugin_unique_name} as part of realtime - {e}')

                if should_trigger_plugins:
                    plugins_to_call = [STATIC_CORRELATOR_PLUGIN_NAME]

                    if self.__constant_alerts:
                        plugins_to_call.append('reports')

                    for plugin_unique_name in plugins_to_call:
                        logger.info(f'Executing plugin {plugin_unique_name}')
                        try:
                            self.request_remote_plugin(
                                'trigger/execute?blocking=False',
                                plugin_unique_name,
                                'post')
                        except Exception as e:
                            logger.exception(f'Failed triggering {plugin_unique_name} as part of realtime - {e}')
            finally:
                logger.info('Finished RT cycle')

    def _get_plugins(self, plugin_subtype: PluginSubtype):
        """
        Get registered plugins from core, filtered by plugin_subtype.
        :param plugin_subtype: A plugin_subtype to filter.
        :return:
        """
        registered_plugins = self.get_available_plugins_from_core()
        return [plugin for plugin in registered_plugins.values() if
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
            blocking = plugin[PLUGIN_NAME] not in ALWAYS_ASYNC_PLUGINS
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
                f'{self.state.SubPhase} subphase failed.')
            raise PhaseExecutionException(
                f'Executing {args[1]} failed as part of '
                f'{self.state.SubPhase} subphase failed.')

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.Core

    def _stopped(self, job_name: str):
        logger.info(f'Got a stop request: Back to {scheduler_consts.Phases.Stable} Phase.')
        try:
            self.__stopping_initiated = True
            # Let's rebuild once at the end for precaution
            self._request_db_rebuild(sync=False)
            self._stop_plugins()
        finally:
            self.current_phase = scheduler_consts.Phases.Stable
            self.state = SchedulerState()
            self.__stopping_initiated = False

    def get_all_plugins(self):
        """
        :return: all the currently registered plugins except Scheduler
        """
        plugins_available = self.get_available_plugins_from_core()
        for plugin_unique_name in plugins_available:
            if plugin_unique_name != self.plugin_unique_name:
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
                response = self.request_remote_plugin('stop_all', plugin, method='post', timeout=20)
                if response.status_code != 200:
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
            except Exception:
                logger.exception('An exception was raised while stopping all plugins.')

        logger.info('Finished stopping all plugins.')
