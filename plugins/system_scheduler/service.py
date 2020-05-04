import logging
import threading
import time
from concurrent.futures import (ALL_COMPLETED, ThreadPoolExecutor,
                                as_completed, wait)
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Set, Dict
import requests

import pytz
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dateutil import tz
from flask import jsonify

from axonius.adapter_base import AdapterBase
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts import adapter_consts, plugin_consts, scheduler_consts
from axonius.consts.gui_consts import RootMasterNames
from axonius.consts.metric_consts import SystemMetric
from axonius.consts.plugin_consts import (CONFIGURABLE_CONFIGS_COLLECTION,
                                          CORE_UNIQUE_NAME,
                                          GENERAL_INFO_PLUGIN_NAME,
                                          PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          REIMAGE_TAGS_ANALYSIS_PLUGIN_NAME,
                                          REPORTS_PLUGIN_NAME,
                                          STATIC_ANALYSIS_PLUGIN_NAME,
                                          STATIC_CORRELATOR_PLUGIN_NAME)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.consts.scheduler_consts import SchedulerState
from axonius.logging.audit_helper import (AuditCategory, AuditAction)
from axonius.logging.metric_helper import log_metric
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import StoredJobStateCompletion, Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.plugin_exceptions import PhaseExecutionException
from axonius.thread_stopper import StopThreadException
from axonius.utils.backup import backup_to_s3
from axonius.utils.files import get_local_config_file
from axonius.utils.host_utils import get_free_disk_space
from axonius.utils.root_master.root_master import root_master_restore_from_s3

logger = logging.getLogger(f'axonius.{__name__}')

# Plugins that should always run async
ALWAYS_ASYNC_PLUGINS = [STATIC_ANALYSIS_PLUGIN_NAME, GENERAL_INFO_PLUGIN_NAME, REIMAGE_TAGS_ANALYSIS_PLUGIN_NAME]
MIN_GB_TO_SAVE_HISTORY = 15


class SystemSchedulerResearchMode(Enum):
    """
    Rate : is the legacy mode which start discovery per hour interval .
    Date : a cron base , currently ony supporting time of day and Recurrence.
    """
    rate = 'system_research_rate'
    date = 'system_research_date'


# pylint: disable=invalid-name, too-many-instance-attributes, too-many-branches, too-many-statements, no-member
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

        executors = {'default': ThreadPoolExecutorApscheduler(1)}

        self._research_phase_scheduler = LoggedBackgroundScheduler(executors=executors)
        self._research_phase_scheduler.add_job(func=self._trigger,
                                               trigger=self.get_research_trigger_by_mode(),
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

        self.__correlation_lock = threading.Lock()
        self._correlation_scheduler = LoggedBackgroundScheduler(
            executors={'default': ThreadPoolExecutorApscheduler(1)}
        )
        self._correlation_scheduler.start()
        self.configure_correlation_scheduler()

        self.plugin_settings = self._get_collection('plugin_settings')

    def run_correlations(self):
        if self.__correlation_lock.acquire(False):
            try:
                logger.info(f'Running correlation')
                self._run_plugins(self._get_plugins(PluginSubtype.Correlator))
                logger.info(f'Done running correlation')
                return True
            finally:
                self.__correlation_lock.release()
        else:
            logger.info(f'Other correlation is in place. Skipping')
            return False

    def detect_correlation_errors(self):
        """
        Once a week, run 'detect correlation errors'
        :return:
        """
        res = self.plugin_settings.find_one({'name': 'last_detect_correlation_errors_date'})
        if res and (res['date'] + timedelta(days=7) > datetime.now()):
            # We need to run once a week only.
            logger.info(f'Not running detect correlation errors: last time it ran was {res["date"]}')
            return
        self.plugin_settings.update_one(
            {'name': 'last_detect_correlation_errors_date'},
            {
                '$set': {
                    'date': datetime.now()
                }
            },
            upsert=True
        )
        logger.info(f'Running detect correlation errors')

        # Run detect errors
        self._trigger_remote_plugin(
            STATIC_CORRELATOR_PLUGIN_NAME,
            job_name='detect_errors',
            data={'should_fix_errors': True},
            timeout=3600 * 6,
            stop_on_timeout=True
        )

        # Run static correlator
        self._trigger_remote_plugin(
            STATIC_CORRELATOR_PLUGIN_NAME,
            timeout=3600 * 8,
            stop_on_timeout=True
        )

    @add_rule('trigger_s3_backup')
    def trigger_s3_backup_external(self):
        return jsonify({'result': str(self.trigger_s3_backup())})

    @staticmethod
    def trigger_s3_backup():
        return str(backup_to_s3())

    @add_rule('trigger_root_master_s3_restore')
    def trigger_root_master_s3_restore_external(self):
        return jsonify({'result': str(self.trigger_root_master_s3_restore())})

    @staticmethod
    def trigger_root_master_s3_restore():
        return str(root_master_restore_from_s3())

    @add_rule('state', should_authenticate=False)
    def get_state(self):
        """
        Get plugin state.
        """
        next_run_time = self._research_phase_scheduler.get_job(
            scheduler_consts.RESEARCH_THREAD_ID).next_run_time
        last_triggered_job = self.get_last_job(
            {
                'job_name': 'execute',
                'job_completed_state': {'$ne': StoredJobStateCompletion.Scheduled.name}
            },
            'started_at'
        )
        last_finished_job = self.get_last_job({'job_name': 'execute',
                                               'job_completed_state': StoredJobStateCompletion.Successful.name},
                                              'finished_at')
        last_start_time = None
        last_finished_at = None
        if last_triggered_job:
            last_start_time = last_triggered_job.get('started_at')
        if last_finished_job:
            last_finished_at = last_finished_job.get('finished_at')
        return jsonify({
            'state': self.state._asdict(),
            'stopping': self.__stopping_initiated,
            'next_run_time': (next_run_time - datetime.now(tz.tzlocal())).total_seconds(),
            'last_start_time': last_start_time,
            'last_finished_time': last_finished_at
        })

    def _on_config_update(self, config):
        logger.info(f'Loading SystemScheduler config: {config}')

        self.__constant_alerts = config['discovery_settings']['constant_alerts']
        self.__analyse_reimage = config['discovery_settings']['analyse_reimage']
        self.__system_research_rate = float(config['discovery_settings']['system_research_rate'])
        system_research_date = config['discovery_settings']['system_research_date']
        self.__system_research_date_time = system_research_date['system_research_date_time']
        self.__system_research_date_recurrence = system_research_date['system_research_date_recurrence']
        self.__system_research_mode = config['discovery_settings']['conditional']

        history_settings = config['discovery_settings']['history_settings']
        if history_settings['enabled'] and history_settings['max_days_to_save'] > 0:
            self.__max_days_to_save = history_settings['max_days_to_save']
        else:
            self.__max_days_to_save = False

        logger.info(f'Setting research mode to: {self.__system_research_mode}')
        logger.info(f'Setting research rate to: {self.__system_research_rate}')
        logger.info(f'Setting research date to: {self.__system_research_date_time}')
        logger.info(f'Setting research recurrence to: {self.__system_research_date_recurrence}')

        scheduler = getattr(self, '_research_phase_scheduler', None)
        self.__save_history = bool(config['discovery_settings']['save_history'])

        # first config load, no reschedule
        if not scheduler:
            return

        # reschedule
        # Saving next_run in order to restore it after 'reschedule_job' overrides this value. We want to restore
        # this value because updating schedule rate should't change the next scheduled time
        scheduler.reschedule_job(
            scheduler_consts.RESEARCH_THREAD_ID, trigger=self.get_research_trigger_by_mode())

    def get_research_trigger_by_mode(self) -> BaseTrigger:
        if self.__system_research_mode == SystemSchedulerResearchMode.rate.value:
            return IntervalTrigger(hours=self.__system_research_rate, timezone=pytz.utc)
        if self.__system_research_mode == SystemSchedulerResearchMode.date.value:
            hour, minute = self.__system_research_date_time.split(':')
            recurrence = self.__system_research_date_recurrence
            return CronTrigger(hour=hour,
                               minute=minute,
                               second='0',
                               day=f'*/{recurrence}')
        raise Exception(f' {self.__system_research_mode } is invalid research mode ')

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'items': [
                        {
                            'name': 'conditional',
                            'title': 'Discovery schedule',
                            'enum': [
                                {
                                    'name': 'system_research_rate',
                                    'title': 'Interval'
                                },
                                {
                                    'name': 'system_research_date',
                                    'title': 'Scheduled'
                                }
                            ],
                            'type': 'string'
                        },
                        {
                            'name': 'system_research_rate',
                            'title': 'Hours between discovery cycles',
                            'type': 'number',
                            'max': 24 * 365  # Up to a year
                        },
                        {
                            'name': 'system_research_date',
                            'type': 'array',
                            'items': [
                                {
                                    'name': 'system_research_date_time',
                                    'title': 'Scheduled discovery time',
                                    'type': 'string',
                                    'format': 'time'
                                },
                                {
                                    'name': 'system_research_date_recurrence',
                                    'title': 'Repeat scheduled discovery every (days)',
                                    'type': 'number'
                                }
                            ],
                            'required': ['system_research_date_time', 'system_research_date_recurrence']
                        },
                        {
                            'name': 'constant_alerts',
                            'title': 'Constantly run Enforcement Sets',
                            'type': 'bool',
                            'required': True
                        },
                        {
                            'name': 'analyse_reimage',
                            'title': 'Tag reimaged devices',
                            'type': 'bool',
                            'required': True
                        },
                        {
                            'name': 'save_history',
                            'title': 'Enable daily historical snapshot',
                            'type': 'bool',
                            'required': True
                        },
                        {
                            'name': 'history_settings',
                            'title': 'Historical Data Settings',
                            'type': 'array',
                            'items': [
                                {
                                    'name': 'enabled',
                                    'title': 'Enable historical data retention',
                                    'type': 'bool'
                                },
                                {
                                    'name': 'max_days_to_save',
                                    'title': 'Historical data retention period (days)',
                                    'type': 'integer'
                                }
                            ],
                            'required': ['enabled', 'days']
                        }
                    ],
                    'name': 'discovery_settings',
                    'title': 'Discovery Settings',
                    'type': 'array',
                    'required': ['conditional', 'system_research_rate',
                                 'save_history', 'constant_alerts', 'analyse_reimage']
                }
            ],
            'type': 'array',
            'pretty_name': 'Lifecycle Settings'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'discovery_settings': {
                'system_research_rate': 12,
                'system_research_date': {
                    'system_research_date_time': '13:00',
                    'system_research_date_recurrence': 1
                },
                'history_settings': {
                    'enabled': True,
                    'max_days_to_save': 180
                },
                'save_history': True,
                'constant_alerts': False,
                'analyse_reimage': False,
                'conditional': 'system_research_rate'
            }
        }

    def configure_correlation_scheduler(self):
        scheduler = getattr(self, '_correlation_scheduler', None)
        if scheduler:
            job = scheduler.get_job(scheduler_consts.CORRELATION_SCHEDULER_THREAD_ID)
            if not self._correlation_schedule_settings.get('enabled'):
                if job:
                    logger.info(f'Removing correlation scheduler')
                    job.remove()
            else:
                hours = self._correlation_schedule_settings.get('correlation_hours_interval')
                if not hours or hours < 1:
                    raise ValueError(f'Error: invalid correlation scheduler hours interval: {hours}')

                new_interval = IntervalTrigger(hours=hours)
                if job:
                    current_trigger = job.trigger
                    if isinstance(current_trigger, IntervalTrigger)\
                            and current_trigger.interval_length == new_interval.interval_length:
                        # Interval not changed, go on with your life
                        logger.debug('Correlation trigger hours stayed the same, not changing')
                    else:
                        job.reschedule(new_interval)
                        logger.info(f'Rescheduling job to {hours} hours. Next run: {job.next_run_time}')
                else:
                    job = scheduler.add_job(
                        func=self.run_correlations,
                        trigger=new_interval,
                        next_run_time=datetime.now() + timedelta(hours=hours),
                        name=scheduler_consts.CORRELATION_SCHEDULER_THREAD_ID,
                        id=scheduler_consts.CORRELATION_SCHEDULER_THREAD_ID,
                        max_instances=1,
                        coalesce=True
                    )
                    logger.info(f'Adding initial job. Next run: {job.next_run_time}')

    def _global_config_updated(self):
        try:
            self.configure_correlation_scheduler()
        except Exception:
            logger.exception(f'Failed updating correlation scheduler settings')

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        """
        The function that runs jobs as part of the triggerable mixin,
        Currently supports only 'execute' which triggers a research right away.
        :param job_name: The job to execute.
        :param post_json: data for the job.
        :param args:
        :return:
        """

        log_metric(logger,
                   metric_name=SystemMetric.TRIAL_EXPIRED_STATE,
                   metric_value=self.trial_expired())

        log_metric(logger,
                   metric_name=SystemMetric.CONTRACT_EXPIRED_STATE,
                   metric_value=self.contract_expired())

        if job_name != 'execute':
            logger.error(f'Got bad trigger request for non-existent job: {job_name}')
            return return_error('Got bad trigger request for non-existent job', 400)

        if self.trial_expired():
            logger.error('Job not ran - system trial has expired')
            return return_error('Job not ran - system trial has expired', 400)

        if self.contract_expired():
            logger.error('Job not ran - system contract has expired')
            return return_error('Job not ran - system contract has expired', 400)

        logger.info(f'Started system scheduler')
        try:
            now = time.time()
            self.__start_research()
            log_metric(logger, metric_name=SystemMetric.CYCLE_FINISHED,
                       metric_value=round(time.time() - now, 1))
        except Exception:
            logger.critical(f'Error - Did not finish a cycle due to an exception!', exc_info=True)
            raise

        return None

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
            logger.info('Stopping initiated, not running')
            return

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

        return

    def __start_research(self):
        """
        Manages a research phase and it's sub phases.
        :return:
        """
        def _log_activity_research(action: AuditAction, params: Dict[str, str] = None):
            self.log_activity(AuditCategory.Discovery, action, params)

        def _log_activity_phase(action: AuditAction):
            _log_activity_research(action, {
                'phase': self.state.SubPhase.value
            })

        def _start_subphase(subphase: scheduler_consts.ResearchPhases):
            with self.__realtime_lock:
                self.state.SubPhase = subphase
            logger.info(f'Started Subphase {subphase}')
            _log_activity_phase(AuditAction.StartPhase)
            if self._notify_on_adapters is True:
                logger.debug(f'Creating notification for subphase {subphase}')
                self.create_notification(f'Started Subphase {subphase}')
            logger.debug(f'Trying to send syslog for subphase {subphase}')
            self.send_external_info_log(f'Started Subphase {subphase}')

        def _complete_subphase():
            _log_activity_phase(AuditAction.CompletePhase)

        def _change_subphase(subphase: scheduler_consts.ResearchPhases):
            _complete_subphase()
            _start_subphase(subphase)

        with self._start_research():
            self.state.Phase = scheduler_consts.Phases.Research
            _log_activity_research(AuditAction.Start)
            _start_subphase(scheduler_consts.ResearchPhases.Fetch_Devices)
            time.sleep(5)  # for too-quick-cycles

            if (self.feature_flags_config().get(RootMasterNames.root_key) or {}).get(RootMasterNames.enabled):
                try:
                    logger.info(f'Root Master mode enabled - Restoring from s3 instead of fetch')
                    # 1. Restore from s3
                    root_master_restore_from_s3()
                    self._request_gui_dashboard_cache_clear()
                    # 2. Run enforcement center
                    _change_subphase(scheduler_consts.ResearchPhases.Post_Correlation)
                    post_correlation_plugins = [plugin for plugin in self._get_plugins(PluginSubtype.PostCorrelation)
                                                if plugin[PLUGIN_NAME] == REPORTS_PLUGIN_NAME]
                    if post_correlation_plugins:
                        self._run_plugins(post_correlation_plugins)
                        self._request_gui_dashboard_cache_clear()

                except Exception:
                    logger.critical(f'Warning - could not complete root-master cycle')

                return  # do not continue the rest of the cycle

            try:
                # this is important and is described at https://axonius.atlassian.net/wiki/spaces/AX/pages/799211552/
                self.request_remote_plugin('wait/execute', REPORTS_PLUGIN_NAME)
            except Exception as e:
                logger.exception(f'Failed waiting for alerts before cycle {e}')

            # Fetch Devices Data.
            try:
                self._run_aggregator_phase(PluginSubtype.AdapterBase)
                self._request_gui_dashboard_cache_clear()
            except Exception:
                logger.error('Failed running fetch_devices phase', exc_info=True)

            try:
                self.detect_correlation_errors()
            except Exception:
                logger.error(f'Failed running detect correlation errors', exc_info=True)

            # Fetch Scanners Data.
            try:
                _change_subphase(scheduler_consts.ResearchPhases.Fetch_Scanners)
                self._run_aggregator_phase(PluginSubtype.ScannerAdapter)
            except Exception:
                logger.error('Failed running fetch_scanners phase', exc_info=True)

            # Clean old devices.
            try:
                _change_subphase(scheduler_consts.ResearchPhases.Clean_Devices)
                self._request_gui_dashboard_cache_clear()

                for adapter in list(
                        self.core_configs_collection.find(
                            {
                                'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE,
                                'status': 'up'
                            }
                        )
                ):
                    try:
                        # this is important and is described at
                        # https://axonius.atlassian.net/wiki/spaces/AX/pages/799211552/
                        logger.debug(f'Requesting wait/insert_to_db for {adapter[PLUGIN_UNIQUE_NAME]}')
                        self.request_remote_plugin('wait/insert_to_db', adapter[PLUGIN_UNIQUE_NAME])
                    except Exception as e:
                        logger.exception(f'Failed waiting for adapter cycle {e}')

                self._run_cleaning_phase()
            except Exception:
                logger.error(f'Failed running clean devices phase', exc_info=True)

            # Run Pre Correlation plugins.
            try:
                _change_subphase(scheduler_consts.ResearchPhases.Pre_Correlation)
                self._run_plugins(self._get_plugins(PluginSubtype.PreCorrelation))
            except Exception:
                logger.error(f'Failed running pre-correlation phase', exc_info=True)

            # Run Correlations.
            try:
                _change_subphase(scheduler_consts.ResearchPhases.Run_Correlations)
                if not self.run_correlations():
                    #  If the correlation was not run because there is an existing one already running, then wait
                    # for it to finish, only then transition to next phase.
                    logger.info(f'Other correlation is in place. Blocking until it is finished..')
                    with self.__correlation_lock:
                        logger.info(f'Other correlation has finished')
                self._request_gui_dashboard_cache_clear()
            except Exception:
                logger.error(f'Failed running correlation phase', exc_info=True)

            try:
                _change_subphase(scheduler_consts.ResearchPhases.Post_Correlation)
                post_correlations_plugins = self._get_plugins(PluginSubtype.PostCorrelation)

                if not self.__analyse_reimage:
                    post_correlations_plugins = [x
                                                 for x
                                                 in post_correlations_plugins
                                                 if x[PLUGIN_NAME] != REIMAGE_TAGS_ANALYSIS_PLUGIN_NAME]

                self._run_plugins(post_correlations_plugins)
            except Exception:
                logger.error(f'Failed running post-correlation phase', exc_info=True)

            try:
                if self.__save_history:
                    # Save history.
                    _change_subphase(scheduler_consts.ResearchPhases.Save_Historical)
                    free_disk_space_in_gb = get_free_disk_space() / (1024 ** 3)
                    if free_disk_space_in_gb < MIN_GB_TO_SAVE_HISTORY:
                        logger.error(f'Can not save history - less than 15 GB on disk!')
                    else:
                        self._run_historical_phase(self.__max_days_to_save)

                self._request_gui_dashboard_cache_clear(clear_slow=True)
            except Exception:
                logger.error(f'Failed running save historical phase', exc_info=True)

            try:
                r = requests.post('https://bandicoot.axonius.local:9090/transfer',
                                  params={'fetchTime': round(time.time() * 1000)})
                if r.status_code != 200:
                    logger.warning(f'Failed to initiate bandicoot transfer got error code: {r.status_code}')
                else:
                    logger.info(f'Bandicoot transfer request was successfully sent')
            except Exception:
                logger.warning(f'Failed to initiate bandicoot transfer')
            try:
                # logger.info(f'Restarting Heavy Lifting...')
                # self._ask_core_to_raise_adapter(HEAVY_LIFTING_PLUGIN_NAME)    # disabled for now
                # logger.info(f'Restart complete')
                pass
            except Exception:
                logger.exception(f'Could not restart heavy-lifting')

            logger.info(f'Finished {scheduler_consts.Phases.Research.name} Phase Successfully.')
            _complete_subphase()
            _log_activity_research(AuditAction.Complete)
            if self._notify_on_adapters is True:
                self.create_notification(f'Finished {scheduler_consts.Phases.Research.name} Phase Successfully.')
            self.send_external_info_log(f'Finished {scheduler_consts.Phases.Research.name} Phase Successfully.')

            try:
                if (self.feature_flags_config().get(RootMasterNames.root_key) or {}).get(RootMasterNames.enabled):
                    logger.info(f'Root Master mode enabled - not backing up')
                elif self._aws_s3_settings.get('enabled') and self._aws_s3_settings.get('enable_backups'):
                    threading.Thread(target=backup_to_s3).start()
            except Exception:
                logger.exception(f'Could not run s3-backup phase')

    def __get_all_realtime_adapters(self):
        db_connection = self._get_db_connection()
        for adapter in self.core_configs_collection.find(
                {
                    'plugin_type': adapter_consts.ADAPTER_PLUGIN_TYPE
                }
        ):
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

                logger.debug(f'RT Cycle, plugins - {should_trigger_plugins} and adapters - {should_fetch_rt_adapter} '
                             f'state - {self.state}')
                if should_fetch_rt_adapter:
                    adapters_to_call = list(self.__get_all_realtime_adapters())
                    if not adapters_to_call:
                        logger.debug('No adapters to call, not doing anything at all')
                        return

                    for adapter_to_call in adapters_to_call:
                        logger.debug(f'Fetching from rt adapter {adapter_to_call[PLUGIN_UNIQUE_NAME]}')
                        self._trigger_remote_plugin(adapter_to_call[PLUGIN_UNIQUE_NAME],
                                                    'insert_to_db',
                                                    blocking=False)

                if should_trigger_plugins:
                    plugins_to_call = [STATIC_CORRELATOR_PLUGIN_NAME]

                    if self.__constant_alerts:
                        plugins_to_call.append(REPORTS_PLUGIN_NAME)

                    for plugin_unique_name in plugins_to_call:
                        logger.debug(f'Executing plugin {plugin_unique_name}')
                        self._trigger_remote_plugin(plugin_unique_name, blocking=False)
            finally:
                logger.debug('Finished RT cycle')

    def _get_plugins(self, plugin_subtype: PluginSubtype) -> list:
        """
        Get registered plugins from core, filtered by plugin_subtype.
        :param plugin_subtype: A plugin_subtype to filter.
        :return:
        """
        registered_plugins = self.get_available_plugins_from_core()
        return [plugin
                for plugin
                in registered_plugins.values()
                if plugin['plugin_subtype'] == plugin_subtype.value]

    def _run_plugins(self, plugins_to_run: list):
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
            self._trigger_remote_plugin(plugin[plugin_consts.PLUGIN_UNIQUE_NAME],
                                        blocking=blocking,
                                        timeout=24 * 3600, stop_on_timeout=True)

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
        self._run_blocking_request(plugin_consts.AGGREGATOR_PLUGIN_NAME, 'clean_db', timeout=3600 * 6)

    def _run_historical_phase(self, max_days_to_save):
        """
        Trigger saving history
        :return:
        """
        self._run_blocking_request(
            plugin_consts.AGGREGATOR_PLUGIN_NAME,
            'save_history',
            data={'max_days_to_save': max_days_to_save},
            timeout=3600 * 6,
        )

    def _run_aggregator_phase(self, plugin_subtype: PluginSubtype):
        """
        Trigger 'fetch_filtered_adapters' job in aggregator with plugin_subtype filter.
        :param plugin_subtype: A plugin_subtype to filter as a white list.
        :return: none
        """
        aggregator_job_id = self._run_non_blocking_request(plugin_consts.AGGREGATOR_PLUGIN_NAME,
                                                           'fetch_filtered_adapters',
                                                           data={'plugin_subtype': plugin_subtype.value})
        self.state.AssociatePluginId = aggregator_job_id
        self._wait_for_aggregator_phase(plugin_subtype)
        self.state.AssociatePluginId = None

    def _wait_for_aggregator_phase(self, plugin_subtype: PluginSubtype):
        """
        Wait for 'fetch_filtered_adapters' job in aggregator with plugin_subtype filter.
        :param plugin_subtype: A plugin_subtype to filter as a white list.
        :return: None
        """
        self._wait_for_request(plugin_consts.AGGREGATOR_PLUGIN_NAME, 'fetch_filtered_adapters',
                               data={'plugin_subtype': plugin_subtype.value}, timeout=48 * 3600)

    def _run_blocking_request(self, plugin_name: str, job_name: str, data: dict = None, timeout: int = None):
        """
        Runs a blocking trigger
        """
        logger.debug(f'Running request {job_name} on {plugin_name}')
        response = self._trigger_remote_plugin(plugin_name, job_name, data=data,
                                               timeout=timeout, stop_on_timeout=True)
        if response.status_code == 408:
            logger.exception(f'Timeout out on {plugin_name}')
            raise PhaseExecutionException(f'Timeout out on {plugin_name}')

        # 403 is a disabled plugin.
        if response.status_code not in (200, 403):
            logger.exception(
                f'Executing {plugin_name} failed as part of '
                f'{self.state.SubPhase} subphase failed.')
            raise PhaseExecutionException(
                f'Executing {plugin_name} failed as part of '
                f'{self.state.SubPhase} subphase failed.')

    def _run_non_blocking_request(self, plugin_name: str, job_name: str,
                                  data: dict = None) -> str:
        """
        Runs a non blocking trigger, and get the id of the jod that started
        :param plugin_name: the plugin name to reach
        :param job_name: the job name to trigger
        :param data: the payload data for the plugin job
        :return: the id of the requested job
        """
        response = self._trigger_remote_plugin_no_blocking(plugin_name, job_name, data=data)

        # 403 is a disabled plugin.
        if response.status_code not in (200, 403):
            logger.exception(
                f'Executing {plugin_name} failed as part of '
                f'{self.state.SubPhase} subphase failed.')
            raise PhaseExecutionException(
                f'Executing {plugin_name} failed as part of '
                f'{self.state.SubPhase} subphase failed.')

        return response.text

    def _wait_for_request(self, plugin_name: str, job_name: str,
                          data: dict = None,
                          timeout: int = None) -> str:
        """
        Runs a non blocking trigger, and get the id of the jod that started
        :param plugin_name: the plugin name to reach
        :param job_name: the job name to trigger
        :param data: the payload data for the plugin job
        :return: the id of the requested job
        """
        response = self._wait_for_remote_plugin(plugin_name, job_name, data=data, timeout=timeout, stop_on_timeout=True)

        if response is None:
            raise PhaseExecutionException(f'Couldn\'t call remote plugin on {plugin_name}')

        if response.status_code == 408:
            logger.exception(f'Timeout out on {plugin_name}')
            raise PhaseExecutionException(f'Timeout out on {plugin_name}')

        # 403 is a disabled plugin.
        if response.status_code not in (200, 403):
            logger.exception(
                f'Executing {plugin_name} failed as part of '
                f'{self.state.SubPhase} subphase failed.')
            raise PhaseExecutionException(
                f'Executing {plugin_name} failed as part of '
                f'{self.state.SubPhase} subphase failed.')

        return response.text

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.Core

    def _stopped(self, job_name: str):
        logger.info(f'Got a stop request: Back to {scheduler_consts.Phases.Stable} Phase.')
        try:
            self.__stopping_initiated = True
            self._stop_plugins()
        finally:
            self.current_phase = scheduler_consts.Phases.Stable
            self.state = SchedulerState()
            self.__stopping_initiated = False

    def get_all_plugins(self) -> Set[str]:
        """
        :return: all the currently registered plugin unique names except Scheduler, Core and Instance Control
        """
        return {x
                for x
                in self.get_available_plugins_from_core().keys()
                if not x.startswith('instance_control') and
                x not in {self.plugin_unique_name, CORE_UNIQUE_NAME}
                }

    def _stop_plugins(self):
        """
        For each plugin in the system create a stop_plugin request.
        It does so asynchronously and waits for every plugin to return ensuring the system is always displaying its
        correct state - not in stable state until it really is.
        """

        def _stop_plugin(plugin):
            try:
                logger.debug(f'stopping {plugin}')
                response = self.request_remote_plugin('stop_all', plugin, method='post', timeout=20,
                                                      fail_on_plugin_down=True)
                if response.status_code != 200:
                    logger.info(f'{plugin} didn\'t stop properly, returned: {response.content}')
            except Exception:
                logger.debug(f'error stopping {plugin}, perhaps the plugin is down', exc_info=True)

        plugins_to_stop = self.get_all_plugins()
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
