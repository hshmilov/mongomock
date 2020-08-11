# pylint: disable=too-many-lines
import logging
import threading
import time
from concurrent.futures import (ALL_COMPLETED, ThreadPoolExecutor,
                                as_completed, wait)
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Set, Dict, Iterator, List, Tuple
from dateutil import tz
import requests

import pytz
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import jsonify
from promise import Promise

from axonius.adapter_base import AdapterBase
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.adapter_consts import LAST_FETCH_TIME, ADAPTER_PLUGIN_TYPE, CLIENT_ID
from axonius.consts.gui_consts import RootMasterNames
from axonius.consts.metric_consts import SystemMetric
from axonius.consts.plugin_consts import (CORE_UNIQUE_NAME,
                                          PLUGIN_NAME, PLUGIN_UNIQUE_NAME,
                                          REIMAGE_TAGS_ANALYSIS_PLUGIN_NAME,
                                          REPORTS_PLUGIN_NAME,
                                          STATIC_ANALYSIS_PLUGIN_NAME,
                                          STATIC_CORRELATOR_PLUGIN_NAME, CLIENTS_COLLECTION,
                                          GUI_PLUGIN_NAME, DISCOVERY_CONFIG_NAME,
                                          ENABLE_CUSTOM_DISCOVERY, DISCOVERY_REPEAT_TYPE, DISCOVERY_REPEAT_ON,
                                          DISCOVERY_RESEARCH_DATE_TIME, DISCOVERY_REPEAT_EVERY,
                                          STATIC_USERS_CORRELATOR_PLUGIN_NAME,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          AGGREGATOR_PLUGIN_NAME, DISCOVERY_REPEAT_RATE, CONNECTION_DISCOVERY,
                                          ADAPTER_DISCOVERY, DISCOVERY_REPEAT_ON_WEEKDAYS,
                                          DISCOVERY_REPEAT_EVERY_DAY, HISTORY_REPEAT_ON, HISTORY_REPEAT_TYPE,
                                          HISTORY_REPEAT_EVERY, HISTORY_REPEAT_WEEKDAYS, HISTORY_REPEAT_RECURRENCE,
                                          HISTORY_REPEAT_EVERY_LIFECYCLE, WEEKDAYS)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.consts.scheduler_consts import (SchedulerState, Phases, ResearchPhases,
                                             CHECK_ADAPTER_CLIENTS_STATUS_INTERVAL, TUNNEL_STATUS_CHECK_INTERVAL,
                                             CUSTOM_DISCOVERY_CHECK_INTERVAL, CUSTOM_DISCOVERY_THRESHOLD,
                                             RUN_ENFORCEMENT_CHECK_INTERVAL,
                                             RESEARCH_THREAD_ID, CORRELATION_SCHEDULER_THREAD_ID,
                                             SCHEDULER_CONFIG_NAME, SCHEDULER_SAVE_HISTORY_CONFIG_NAME)
from axonius.consts.report_consts import TRIGGERS_FIELD
from axonius.logging.audit_helper import (AuditCategory, AuditAction)
from axonius.logging.metric_helper import log_metric
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import StoredJobStateCompletion, Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.plugin_exceptions import PhaseExecutionException
from axonius.saas.input_params import read_saas_input_params
from axonius.thread_stopper import StopThreadException
from axonius.types.enforcement_classes import TriggerPeriod, Trigger
from axonius.utils.backup import backup_to_s3, backup_to_external
from axonius.utils.datetime import time_diff, days_diff
from axonius.utils.files import get_local_config_file
from axonius.utils.root_master.root_master import root_master_restore_from_s3, root_master_restore_from_smb
from axonius.utils.host_utils import get_free_disk_space, check_installer_locks

logger = logging.getLogger(f'axonius.{__name__}')

# Plugins that should always run async
ALWAYS_ASYNC_PLUGINS = [STATIC_ANALYSIS_PLUGIN_NAME, REIMAGE_TAGS_ANALYSIS_PLUGIN_NAME]
MIN_GB_TO_SAVE_HISTORY = 15


class SystemSchedulerResearchMode(Enum):
    """
    Rate : is the legacy mode which start discovery per hour interval .
    Date : a cron base , currently ony supporting time of day and Recurrence.
    """
    rate = 'system_research_rate'
    date = 'system_research_date'
    weekdays = 'system_research_weekdays'


# pylint: disable=invalid-name, too-many-instance-attributes, too-many-branches, too-many-statements, no-member, too-many-lines
class SystemSchedulerService(Triggerable, PluginBase, Configurable):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=SYSTEM_SCHEDULER_PLUGIN_NAME, *args, **kwargs)
        self.current_phase = Phases.Stable

        # whether or not stopping sequence has initiated
        self.__stopping_initiated = False

        self.state = SchedulerState()

        executors = {'default': ThreadPoolExecutorApscheduler(1)}

        self._research_phase_scheduler = LoggedBackgroundScheduler(executors=executors)
        self._research_phase_scheduler.add_job(func=self._trigger,
                                               trigger=self.get_research_trigger_by_mode(),
                                               name=RESEARCH_THREAD_ID,
                                               id=RESEARCH_THREAD_ID,
                                               max_instances=1)
        self._research_phase_scheduler.start()

        self.__realtime_scheduler = LoggedBackgroundScheduler(executors={'default': ThreadPoolExecutorApscheduler(1)})
        self.__realtime_scheduler.add_job(func=self.__run_realtime_adapters,
                                          trigger=IntervalTrigger(seconds=30),
                                          next_run_time=datetime.now(),
                                          max_instances=1)
        self.__realtime_scheduler.start()

        if read_saas_input_params():
            self.__tunnel_status_scheduler = LoggedBackgroundScheduler(
                executors={'default': ThreadPoolExecutorApscheduler(1)})
            self.__tunnel_status_scheduler.add_job(func=self.__run_tunnel_check,
                                                   trigger=IntervalTrigger(minutes=TUNNEL_STATUS_CHECK_INTERVAL),
                                                   next_run_time=datetime.now(),
                                                   max_instances=1)
            self.__tunnel_status_scheduler.start()

        self.__custom_discovery_scheduler = LoggedBackgroundScheduler(executors={
            'default': ThreadPoolExecutorApscheduler(1)
        })
        self.__custom_discovery_scheduler.add_job(func=self.__run_custom_discovery_adapters,
                                                  trigger=IntervalTrigger(seconds=CUSTOM_DISCOVERY_CHECK_INTERVAL),
                                                  next_run_time=datetime.now(),
                                                  max_instances=1)
        self.__custom_discovery_scheduler.start()

        self.__run_enforcements_scheduler = LoggedBackgroundScheduler(executors={
            'default': ThreadPoolExecutorApscheduler(1)
        })
        self.__run_enforcements_scheduler.add_job(func=self.__run_triggered_enforcements,
                                                  trigger=IntervalTrigger(seconds=RUN_ENFORCEMENT_CHECK_INTERVAL),
                                                  next_run_time=datetime.now(),
                                                  max_instances=1)
        self.__run_enforcements_scheduler.start()

        self.__adapter_clients_status = LoggedBackgroundScheduler(executors={
            'default': ThreadPoolExecutorApscheduler(1)
        })

        if self._update_adapters_clients_periodically:
            self.__adapter_clients_status.add_job(func=self.__check_adapter_clients_status,
                                                  trigger=IntervalTrigger(
                                                      minutes=CHECK_ADAPTER_CLIENTS_STATUS_INTERVAL),
                                                  next_run_time=datetime.now(),
                                                  max_instances=1)
            self.__adapter_clients_status.start()

        self.__correlation_lock = threading.Lock()
        self._correlation_scheduler = LoggedBackgroundScheduler(
            executors={'default': ThreadPoolExecutorApscheduler(1)}
        )
        self._correlation_scheduler.start()
        self.configure_correlation_scheduler()
        self.system_scheduler_plugin_settings = self._get_collection('plugin_settings')

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
        res = self.system_scheduler_plugin_settings.find_one({'name': 'last_detect_correlation_errors_date'})
        if res and (res['date'] + timedelta(days=7) > datetime.now()):
            # We need to run once a week only.
            logger.info(f'Not running detect correlation errors: last time it ran was {res["date"]}')
            return
        self.system_scheduler_plugin_settings.update_one(
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
        return str(backup_to_external(services=['s3']))

    @add_rule('trigger_root_master_s3_restore')
    def trigger_root_master_s3_restore_external(self):
        return jsonify({'result': str(self.trigger_root_master_s3_restore())})

    @staticmethod
    def trigger_root_master_s3_restore():
        return str(root_master_restore_from_s3())

    @add_rule('trigger_smb_backup')
    def trigger_smb_backup_external(self):
        return jsonify({'result': str(self.trigger_smb_backup())})

    @staticmethod
    def trigger_smb_backup():
        return str(backup_to_external(services=['smb']))

    @add_rule('trigger_root_master_smb_restore')
    def trigger_root_master_smb_restore_external(self):
        return jsonify({'result': str(self.trigger_root_master_smb_restore())})

    @staticmethod
    def trigger_root_master_smb_restore():
        return str(root_master_restore_from_smb())

    @add_rule('state', should_authenticate=False)
    def get_state(self):
        """
        Get plugin state.
        """
        next_run_time = self._research_phase_scheduler.get_job(RESEARCH_THREAD_ID).next_run_time
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
        self.__system_research_weekdays = config['discovery_settings']['system_research_weekdays']
        self.__system_research_mode = config['discovery_settings']['conditional']

        history_settings = config['history_retention_settings']
        if history_settings['enabled'] and history_settings['max_days_to_save'] > 0:
            self.__max_days_to_save = history_settings['max_days_to_save']
        else:
            self.__max_days_to_save = False

        logger.info(f'Setting research mode to: {self.__system_research_mode}')
        logger.info(f'Setting research rate to: {self.__system_research_rate}')
        logger.info(f'Setting research date to: {self.__system_research_date_time}')
        logger.info(f'Setting research recurrence to: {self.__system_research_date_recurrence}')

        scheduler = getattr(self, '_research_phase_scheduler', None)
        self.__save_history = bool(config['history_settings'][SCHEDULER_SAVE_HISTORY_CONFIG_NAME])

        # first config load, no reschedule
        if not scheduler:
            return

        # reschedule
        # Saving next_run in order to restore it after 'reschedule_job' overrides this value. We want to restore
        # this value because updating schedule rate should't change the next scheduled time
        scheduler.reschedule_job(RESEARCH_THREAD_ID, trigger=self.get_research_trigger_by_mode())

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
        if self.__system_research_mode == SystemSchedulerResearchMode.weekdays.value:
            hour, minute = self.__system_research_weekdays.get(DISCOVERY_RESEARCH_DATE_TIME).split(':')
            # Create a string of weekdays in cron syntax (sun,mon,tue,wed...)
            weekdays_for_cron = ','.join([day[:3].lower() for day in
                                          self.__system_research_weekdays.get(DISCOVERY_REPEAT_ON)])
            return CronTrigger(hour=hour,
                               minute=minute,
                               second='0',
                               day_of_week=weekdays_for_cron)

        raise Exception(f'{self.__system_research_mode} is invalid research mode ')

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
                                    'title': 'Every x hours'
                                },
                                {
                                    'name': 'system_research_date',
                                    'title': 'Every x days'
                                },
                                {
                                    'name': 'system_research_weekdays',
                                    'title': 'Days of week'
                                }
                            ],
                            'type': 'string'
                        },
                        {
                            'name': 'system_research_rate',
                            'title': 'Repeat scheduled discovery every (hours)',
                            'type': 'number',
                            'max': 24 * 365  # Up to a year
                        },
                        {
                            'name': 'system_research_date',
                            'type': 'array',
                            'items': [
                                {
                                    'name': 'system_research_date_recurrence',
                                    'title': 'Repeat scheduled discovery every (days)',
                                    'type': 'number'
                                },
                                {
                                    'name': 'system_research_date_time',
                                    'title': 'Scheduled discovery time',
                                    'type': 'string',
                                    'format': 'time'
                                }
                            ],
                            'required': ['system_research_date_time', 'system_research_date_recurrence']
                        },
                        {
                            'name': 'system_research_weekdays',
                            'type': 'array',
                            'required': [DISCOVERY_RESEARCH_DATE_TIME, DISCOVERY_REPEAT_ON],
                            'items': [
                                {
                                    'name': DISCOVERY_REPEAT_ON,
                                    'title': 'Repeat scheduled discovery on',
                                    'type': 'array',
                                    'items': {
                                        'enum': [{'name': day.lower(), 'title': day} for day in WEEKDAYS],
                                        'type': 'string'
                                    }
                                },
                                {
                                    'name': DISCOVERY_RESEARCH_DATE_TIME,
                                    'title': 'Scheduled discovery time',
                                    'type': 'string',
                                    'format': 'time'
                                }
                            ]
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
                        }
                    ],

                    'name': 'discovery_settings',
                    'title': 'Discovery Settings',
                    'type': 'array',
                    'required': ['conditional', 'system_research_rate',
                                 'constant_alerts', 'analyse_reimage']
                },
                {
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable scheduled historical snapshot',
                            'type': 'bool',
                            'required': True
                        },
                        {
                            'name': HISTORY_REPEAT_TYPE,
                            'title': 'Historical snapshot schedule '
                                     '(data will be saved for first discovery on each day)',
                            'enum': [
                                {
                                    'name': HISTORY_REPEAT_EVERY_LIFECYCLE,
                                    'title': 'Every discovery cycle'
                                },
                                {
                                    'name': HISTORY_REPEAT_EVERY,
                                    'title': 'Every x days'
                                },
                                {
                                    'name': HISTORY_REPEAT_WEEKDAYS,
                                    'title': 'Days of week'
                                }
                            ],
                            'type': 'string'
                        },
                        {
                            'name': HISTORY_REPEAT_EVERY,
                            'type': 'array',
                            'items': [
                                {
                                    'name': HISTORY_REPEAT_RECURRENCE,
                                    'title': 'Repeat scheduled historical snapshot every (days)',
                                    'type': 'number',
                                    'min': 1
                                }
                            ],
                            'required': ['historical_schedule_recurrence']
                        },
                        {
                            'name': HISTORY_REPEAT_WEEKDAYS,
                            'type': 'array',
                            'required': [HISTORY_REPEAT_ON],
                            'items': [
                                {
                                    'name': HISTORY_REPEAT_ON,
                                    'title': 'Repeat scheduled historical snapshot on',
                                    'type': 'array',
                                    'items': {
                                        'enum': [{'name': day.lower(), 'title': day} for day in WEEKDAYS],
                                        'type': 'string'
                                    }
                                }
                            ]
                        },
                    ],
                    'name': 'history_settings',
                    'title': 'Historical Snapshot Scheduling Settings',
                    'type': 'array',
                    'required': ['enabled', 'conditional']
                },
                {
                    'name': 'history_retention_settings',
                    'title': 'Historical Snapshot Retention Settings',
                    'type': 'array',
                    'items': [
                        {
                            'name': 'enabled',
                            'title': 'Enable historical snapshot retention',
                            'type': 'bool'
                        },
                        {
                            'name': 'max_days_to_save',
                            'title': 'Historical snapshot retention period (days)',
                            'type': 'integer'
                        }
                    ],
                    'required': ['enabled', 'max_days_to_save']
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
                'system_research_weekdays': {
                    DISCOVERY_RESEARCH_DATE_TIME: '13:00',
                    DISCOVERY_REPEAT_ON: [day.lower() for day in WEEKDAYS]
                },
                'constant_alerts': False,
                'analyse_reimage': False,
                'conditional': 'system_research_rate'
            },
            'history_settings': {
                'enabled': True,
                HISTORY_REPEAT_EVERY: {
                    HISTORY_REPEAT_RECURRENCE: 1
                },
                HISTORY_REPEAT_WEEKDAYS: {
                    HISTORY_REPEAT_ON: [day.lower() for day in WEEKDAYS]
                },
                HISTORY_REPEAT_TYPE: HISTORY_REPEAT_EVERY_LIFECYCLE,
            },
            'history_retention_settings': {
                'enabled': True,
                'max_days_to_save': 180
            },
        }

    def configure_correlation_scheduler(self):
        scheduler = getattr(self, '_correlation_scheduler', None)
        if scheduler:
            job = scheduler.get_job(CORRELATION_SCHEDULER_THREAD_ID)
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
                    if isinstance(current_trigger, IntervalTrigger) \
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
                        name=CORRELATION_SCHEDULER_THREAD_ID,
                        id=CORRELATION_SCHEDULER_THREAD_ID,
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
        if self.state.Phase is Phases.Research:
            raise PhaseExecutionException(f'{Phases.Research.name} is already executing.')
        if self.__stopping_initiated:
            logger.info('Stopping initiated, not running')
            return

        # Change current phase
        self.current_phase = Phases.Research
        logger.info(f'Entered {Phases.Research.name} Phase.')
        try:
            yield
        except StopThreadException:
            logger.info('Stopped execution')
            raise
        except BaseException:
            logger.exception(f'Failed {Phases.Research.name} Phase.')
            raise
        finally:
            logger.info(f'Back to {Phases.Stable} Phase.')
            self.current_phase = Phases.Stable
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
            if self.state and self.state.SubPhase:
                _log_activity_research(action, {
                    'phase': self.state.SubPhase.value
                })

        def _start_subphase(subphase: ResearchPhases):
            self.state.SubPhase = subphase
            logger.info(f'Started Subphase {subphase}')
            _log_activity_phase(AuditAction.StartPhase)
            if self._notify_on_adapters is True:
                logger.debug(f'Creating notification for subphase {subphase}')
                self.create_notification(f'Started Subphase {subphase}')
            logger.debug(f'Trying to send syslog for subphase {subphase}')

        def _complete_subphase():
            _log_activity_phase(AuditAction.CompletePhase)

        def _change_subphase(subphase: ResearchPhases):
            _complete_subphase()
            _start_subphase(subphase)

        # pylint: disable=no-else-return
        with self._start_research():
            self.state.Phase = Phases.Research
            _log_activity_research(AuditAction.Start)
            _start_subphase(ResearchPhases.Fetch_Devices)
            time.sleep(5)  # for too-quick-cycles

            if (self.feature_flags_config().get(RootMasterNames.root_key) or {}).get(RootMasterNames.enabled):
                try:
                    logger.info(f'Root Master mode enabled - Restoring from s3 instead of fetch')
                    # 1. Restore from s3
                    root_master_restore_from_s3()
                    self._request_gui_dashboard_cache_clear()
                    # 2. Run enforcement center
                    _change_subphase(ResearchPhases.Post_Correlation)
                    post_correlation_plugins = [plugin for plugin in self._get_plugins(PluginSubtype.PostCorrelation)
                                                if plugin[PLUGIN_NAME] == REPORTS_PLUGIN_NAME]
                    if post_correlation_plugins:
                        self._run_plugins(post_correlation_plugins)
                        self._request_gui_dashboard_cache_clear()

                except Exception:
                    logger.critical(f'Could not complete root-master cycle (S3)')

                return  # do not continue the rest of the cycle

            # pylint: disable=no-else-return
            elif (self.feature_flags_config().get(RootMasterNames.root_key)
                  or {}).get(RootMasterNames.SMB_enabled):
                try:
                    logger.info(f'Root Master Mode enabled - Restoring from '
                                f'SMB instead of fetch')
                    response = root_master_restore_from_smb()
                    self._request_gui_dashboard_cache_clear()

                    _change_subphase(ResearchPhases.Post_Correlation)
                    post_correlation_plugins = [plugin for plugin in
                                                self._get_plugins(PluginSubtype.PostCorrelation)
                                                if plugin[PLUGIN_NAME] == REPORTS_PLUGIN_NAME]
                    if post_correlation_plugins:
                        self._run_plugins(post_correlation_plugins)
                        self._request_gui_dashboard_cache_clear()

                except Exception:
                    logger.critical(f'Could not complete Root Master cycle (SMB)')
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
                _change_subphase(ResearchPhases.Fetch_Scanners)
                self._run_aggregator_phase(PluginSubtype.ScannerAdapter)
            except Exception:
                logger.error('Failed running fetch_scanners phase', exc_info=True)

            # Clean old devices.
            try:
                _change_subphase(ResearchPhases.Clean_Devices)
                self._request_gui_dashboard_cache_clear()

                self._run_cleaning_phase()
            except Exception:
                logger.error(f'Failed running clean devices phase', exc_info=True)

            # Run Pre Correlation plugins.
            try:
                _change_subphase(ResearchPhases.Pre_Correlation)
                self._run_plugins(self._get_plugins(PluginSubtype.PreCorrelation))
            except Exception:
                logger.error(f'Failed running pre-correlation phase', exc_info=True)

            # Run Correlations.
            try:
                _change_subphase(ResearchPhases.Run_Correlations)
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
                _change_subphase(ResearchPhases.Post_Correlation)
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
                history_config, last_history_date = self.get_history_config()
                if self.__save_history and self.should_save_history(history_config, last_history_date):
                    # Save history.
                    _change_subphase(ResearchPhases.Save_Historical)
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

            logger.info(f'Finished {Phases.Research.name} Phase Successfully.')
            _complete_subphase()
            _log_activity_research(AuditAction.Complete)

            try:
                if (self.feature_flags_config().get(RootMasterNames.root_key) or {}).get(RootMasterNames.enabled):
                    logger.info(f'Root Master mode enabled - not backing up')
                elif self._aws_s3_settings.get('enabled') and self._aws_s3_settings.get('enable_backups'):
                    threading.Thread(target=backup_to_s3).start()
                elif self._smb_settings.get('enabled') and self._smb_settings.get('enable_backups'):
                    threading.Thread(target=backup_to_external, args=(['smb'],)).start()
            except Exception:
                logger.exception(f'Could not run backup phase')

    def __get_all_realtime_adapters(self):
        names = self.plugins.get_plugin_names_with_config(AdapterBase.__name__, {'realtime_adapter': True})
        for adapter in self.core_configs_collection.find(
                {
                    'plugin_type': ADAPTER_PLUGIN_TYPE
                }
        ):

            if adapter[PLUGIN_NAME] in names:
                yield adapter

    @staticmethod
    def should_save_history(history_saving_config: dict, last_history: datetime) -> bool:
        """
        Check if we should save historical devices data
        :param history_saving_config: history saving config
        :param last_history: last history date
        :return: True if we should save history data
        """
        if not history_saving_config:
            return True

        if history_saving_config.get(HISTORY_REPEAT_TYPE) == HISTORY_REPEAT_EVERY_LIFECYCLE:
            return True

        if history_saving_config.get(HISTORY_REPEAT_TYPE) == HISTORY_REPEAT_WEEKDAYS:
            today = datetime.today().strftime('%A').lower()
            saved_weekdays = (history_saving_config.get(HISTORY_REPEAT_WEEKDAYS) or {}).get(HISTORY_REPEAT_ON) or []
            if today in saved_weekdays:
                return True
        elif history_saving_config.get(HISTORY_REPEAT_TYPE) == HISTORY_REPEAT_EVERY:
            if not last_history:
                return True
            saved_recurrence = (history_saving_config.get(HISTORY_REPEAT_EVERY) or {}).get(HISTORY_REPEAT_RECURRENCE, 1)
            if (datetime.now() - last_history).days >= saved_recurrence:
                return True
        return False

    # pylint: disable=too-many-return-statements
    @staticmethod
    def should_run_custom_discovery(discovery_config: dict, last_discovery: datetime) -> bool:
        """
        Check if the given adapter/client should be triggered by the given discovery config
        :param discovery_config: adapter custom discovery settings
        :param last_discovery: last time the adapter/client was triggered
        :return: True if we should trigger adapter/client fetch
        """
        current_time = datetime.now().time()
        if discovery_config.get(DISCOVERY_REPEAT_TYPE) == DISCOVERY_REPEAT_RATE:
            if not last_discovery:
                return True
            if int(((datetime.now() - last_discovery).seconds / 3600)) ==\
                    discovery_config.get(DISCOVERY_REPEAT_RATE, 12):
                return True
            return False

        discovery_type_config = None
        run_on_weekdays = False
        run_repeat_every_day = False
        if discovery_config.get(DISCOVERY_REPEAT_TYPE) == DISCOVERY_REPEAT_ON_WEEKDAYS:
            run_on_weekdays = True
            discovery_type_config = discovery_config.get(DISCOVERY_REPEAT_ON_WEEKDAYS)
        elif discovery_config.get(DISCOVERY_REPEAT_TYPE) == DISCOVERY_REPEAT_EVERY_DAY:
            run_repeat_every_day = True
            discovery_type_config = discovery_config.get(DISCOVERY_REPEAT_EVERY_DAY)

        # Check custom discovery time
        try:
            scheduled_custom_discovery_time = \
                datetime.strptime(discovery_type_config.get(DISCOVERY_RESEARCH_DATE_TIME), '%H:%M').time()
        except ValueError:
            logger.error(f'Error parsing discovery time: {discovery_type_config.get(DISCOVERY_RESEARCH_DATE_TIME)}')
            return False

        # its too early
        if current_time < scheduled_custom_discovery_time:
            return False

        # too late
        if time_diff(current_time, scheduled_custom_discovery_time).seconds > CUSTOM_DISCOVERY_THRESHOLD:
            return False

        # Check for weekday
        if run_on_weekdays:
            today = datetime.today().strftime('%A').lower()
            if today in discovery_type_config.get(DISCOVERY_REPEAT_ON_WEEKDAYS, []):
                if not last_discovery:
                    return True
                if (datetime.now() - last_discovery).days > 0:
                    return True

        # Check for day diff
        elif run_repeat_every_day:
            if not last_discovery:
                return True
            if (datetime.now() - last_discovery).days == discovery_type_config.get(DISCOVERY_REPEAT_EVERY, 1):
                return True
        return False

    def get_custom_discovery_adapters(self) -> Iterator[Tuple[dict, List[Tuple[Tuple[Dict, bool]]]]]:
        """
        Get adapters that has custom discovery settings and should be triggered right now
        :return: an iterator of Tuples, which contains the adapter, and it's clients that should be triggered
        at this time (with custom discovery). Each client in the List, is a tuple of (Client, custom_discovery_set)
        """
        all_plugins_with_custom_discovery_enabled = self.plugins.get_plugin_names_with_config(
            DISCOVERY_CONFIG_NAME,
            {
                f'{ADAPTER_DISCOVERY}.{ENABLE_CUSTOM_DISCOVERY}': True
            }
        )

        all_plugins_with_custom_connection_discovery_enabled = self.plugins.get_plugin_names_with_config(
            DISCOVERY_CONFIG_NAME,
            {
                CONNECTION_DISCOVERY: True
            }
        )

        def _handle_connection_discovery(_adapter: Dict, adapter_config: Dict, _plugin_settings: Dict,
                                         _should_trigger_adapter: bool) -> Tuple[Dict, List[Dict], List[Dict]]:
            """
            Function to filter which of the adapter's clients should be triggered.
            :param _adapter: the adapter object.
            :param adapter_config: The adapter's config from core db.
            :param _plugin_settings: the adapter's plugin_settings object. (self.plugin_settings)
            :param _should_trigger_adapter: is the adapter should be triggered now (with its custom discovery)
            :return: first element of the tuple is the adapter, second - a list of clients with custom discovery
            configured and last the clients which should be triggered along with the adapter discovery configurations.
            """
            # remove adapter that has clients with custom discovery, so we won't trigger twice.
            if _adapter[PLUGIN_NAME] in all_plugins_with_custom_discovery_enabled:
                all_plugins_with_custom_discovery_enabled.remove(_adapter[PLUGIN_NAME])
            _clients = self.get_adapter_clients(_adapter[PLUGIN_UNIQUE_NAME])

            adapter_discovery_enabled = adapter_config.get(ENABLE_CUSTOM_DISCOVERY, False)
            custom_discovery_clients_to_trigger = []
            adapter_discovery_clients_to_trigger = []

            for client in _clients:
                _config = client.get(CONNECTION_DISCOVERY, {})
                connection_discovery_enabled = _config.get(ENABLE_CUSTOM_DISCOVERY, False)

                if connection_discovery_enabled:
                    last_fetch_time = client.get(LAST_FETCH_TIME)
                    if self.should_run_custom_discovery(_config, last_fetch_time):
                        custom_discovery_clients_to_trigger.append((client, True))
                elif adapter_discovery_enabled and _should_trigger_adapter:
                    adapter_discovery_clients_to_trigger.append((client, False))

            # All the adapter's clients will be triggered one by one.
            # ￿So clients with custom discovery, won't be triggered twice.
            if custom_discovery_clients_to_trigger or adapter_discovery_clients_to_trigger:
                yield _adapter, custom_discovery_clients_to_trigger, adapter_discovery_clients_to_trigger

        def _get_adapter_discovery_config(_adapter: Dict) -> Tuple[Dict, Dict]:
            """
            :param _adapter: the adapter doc from db
            :return: Tuple of adapter's plugin_settings object and config from core db.
            """
            _plugin_settings = self.plugins.get_plugin_settings(_adapter[PLUGIN_NAME])
            return _plugin_settings, _plugin_settings.configurable_configs.discovery_configuration[ADAPTER_DISCOVERY]

        # pylint: disable=too-many-nested-blocks
        if all_plugins_with_custom_discovery_enabled or all_plugins_with_custom_connection_discovery_enabled:
            for adapter in self.core_configs_collection.find():
                if (adapter[PLUGIN_NAME] in all_plugins_with_custom_connection_discovery_enabled) or\
                        (adapter[PLUGIN_NAME] in all_plugins_with_custom_discovery_enabled):
                    should_trigger_adapter = False
                    plugin_settings, config = _get_adapter_discovery_config(adapter)
                    last_adapter_fetch_time = plugin_settings.plugin_settings_keyval[LAST_FETCH_TIME]
                    if self.should_run_custom_discovery(config, last_adapter_fetch_time):
                        should_trigger_adapter = True

                    num_of_clients_to_trigger = 0
                    if adapter[PLUGIN_NAME] in all_plugins_with_custom_connection_discovery_enabled:
                        try:
                            num_of_clients_to_trigger = self.get_adapter_clients_config_with_custom_discovery_count(
                                adapter[PLUGIN_UNIQUE_NAME])
                            if num_of_clients_to_trigger > 0:
                                yield from _handle_connection_discovery(adapter,
                                                                        config,
                                                                        plugin_settings,
                                                                        should_trigger_adapter)
                        except Exception:
                            logger.exception(
                                f'Error filtering adapter {adapter[PLUGIN_UNIQUE_NAME]} custom connection discovery')
                    if num_of_clients_to_trigger == 0 and adapter[PLUGIN_NAME]\
                            in all_plugins_with_custom_discovery_enabled and should_trigger_adapter:
                        yield adapter, None, None

        else:
            return []

    def __get_all_adapters(self):
        yield from self.core_configs_collection.find(
            {
                'plugin_type': ADAPTER_PLUGIN_TYPE
            }
        )

    def get_adapter_clients_count(self, adapter_unique_name: str) -> int:
        """
        :param adapter_unique_name: Adapter unique name
        :return: Returns the amount of clients in adapter
        """
        return self._get_db_connection()[adapter_unique_name][CLIENTS_COLLECTION].count_documents({})

    def get_adapter_clients_config_with_custom_discovery_count(self, adapter_unique_name: str) -> List[Dict]:
        """
        :param adapter_unique_name: Adapter unique name
        :return: Returns the amount of clients in adapter
        """
        return self._get_db_connection()[adapter_unique_name][CLIENTS_COLLECTION].count_documents({
            f'{CONNECTION_DISCOVERY}.{ENABLE_CUSTOM_DISCOVERY}': True
        })

    def get_adapter_clients(self, adapter_unique_name: str) -> List[Dict]:
        """
        :param adapter_unique_name: Adapter unique name
        :return: Returns the amount of clients in adapter
        """
        return self._get_db_connection()[adapter_unique_name][CLIENTS_COLLECTION]\
            .find({}, projection={CONNECTION_DISCOVERY: 1, CLIENT_ID: 1, LAST_FETCH_TIME: 1})

    def __check_adapter_clients_status(self):
        """
        Trigger each adapter to check its client's status and update it if necessary.
        In case a client's status changed from 'error' to 'success' it runs fetch automatically
        :return:
        """
        for adapter in self.__get_all_adapters():
            if self.get_adapter_clients_count(adapter[PLUGIN_UNIQUE_NAME]):
                self._trigger_remote_plugin_no_blocking(
                    plugin_name=adapter[PLUGIN_UNIQUE_NAME],
                    job_name='update_clients_status'
                )

    def __run_tunnel_check(self):
        logger.debug('Triggered gui with check_tunnel_status job')
        self._trigger_remote_plugin(GUI_PLUGIN_NAME, 'check_tunnel_status', blocking=False)

    def trigger_adapters_out_of_cycle(self, adapters_to_call: List[dict], log_fetch=False):
        """
        Triggers realtime adapters and correlations as long as a cycle hasn't taken place
        :return:
        """
        if check_installer_locks(unlink=False):
            # Installer is in progress, do not trigger rt adapters
            logger.debug('Installer is in progress')
            should_trigger_plugins = False
            should_fetch_adapters = False

        elif self.state.SubPhase is None:
            # Not in cycle - can do all
            should_trigger_plugins = True
            should_fetch_adapters = True
        else:
            # In cycle and can't do anything for consistency
            should_trigger_plugins = False
            should_fetch_adapters = False

        logger.debug(f'plugins - {should_trigger_plugins} and adapters - {should_fetch_adapters} '
                     f'state - {self.state}')
        data = {
            'log_fetch': log_fetch
        }
        if should_fetch_adapters:
            for adapter_to_call in adapters_to_call:
                logger.debug(f'Fetching from {adapter_to_call[PLUGIN_UNIQUE_NAME]}')
                self._trigger_remote_plugin(adapter_to_call[PLUGIN_UNIQUE_NAME],
                                            'insert_to_db',
                                            blocking=False,
                                            data=data)

        if should_trigger_plugins:
            plugins_to_call = [STATIC_CORRELATOR_PLUGIN_NAME]

            if self.__constant_alerts:
                plugins_to_call.append(REPORTS_PLUGIN_NAME)

            for plugin_unique_name in plugins_to_call:
                logger.debug(f'Executing plugin {plugin_unique_name}')
                self._trigger_remote_plugin(plugin_unique_name, blocking=False)

    def __run_realtime_adapters(self):
        adapters_to_call = list(self.__get_all_realtime_adapters())
        if not adapters_to_call:
            logger.debug('No adapters to call, not doing anything at all')
            return
        logger.debug('Starting RT cycle')
        try:
            self.trigger_adapters_out_of_cycle(adapters_to_call, log_fetch=False)
        except Exception:
            logger.exception('Error triggering realtime adapters')
        logger.debug('Finished RT cycle')

    @staticmethod
    def __promise_callback_wrapper(f, **kwargs):

        def wrapper(*args):
            return f(*args, **kwargs)

        return wrapper

    def __trigger_specific_client(self, _adapter: Dict, _client: Dict, custom_discovery: bool):

        def _specific_adapter_resolve_callback(*args, **kwargs):
            _client_id = kwargs.get('client_id')
            _custom_discovery = kwargs.get('connection_custom_discovery')
            if _custom_discovery:
                logger.debug(f'{_adapter[PLUGIN_UNIQUE_NAME]} has finished fetching data for'
                             f'client: {_client_id} after custom discovery trigger.')
            else:
                logger.debug(f'{_adapter[PLUGIN_UNIQUE_NAME]} has finished fetching data for'
                             f'client: {_client_id}')

        def _specific_adapter_reject_callback(err, **kwargs):
            _client_id = kwargs.get('client_id', {})
            logger.exception(f'Failed fetching from {_client_id}', exc_info=err)

        def _trigger_client(resolve, _):
            try:
                self._async_trigger_remote_plugin(_adapter[PLUGIN_UNIQUE_NAME], 'insert_to_db', data={
                    'client_name': _client['client_id'],
                    'connection_custom_discovery': custom_discovery
                }).then(did_fulfill=self.__promise_callback_wrapper(_specific_adapter_resolve_callback,
                                                                    client_id=_client['client_id'],
                                                                    connection_custom_discovery=custom_discovery),
                        did_reject=self.__promise_callback_wrapper(_specific_adapter_reject_callback,
                                                                   client_id=_client['client_id'])) \
                    .then(did_fulfill=resolve, did_reject=resolve)
            except Exception:
                logger.exception('Error triggering custom discovery adapter client')
                resolve()

        return Promise(_trigger_client)

    def __run_custom_discovery_adapters(self):
        adapters_to_call = list(self.get_custom_discovery_adapters())
        if not adapters_to_call:
            logger.debug('No adapters to call, not doing anything at all')
            return
        logger.info(f'Starting Custom Discovery cycle with {len(adapters_to_call)} adapters: {adapters_to_call}')

        def inserted_to_db(*args, **kwargs):
            _adapter = kwargs.get('adapter', {})
            logger.debug(f'{_adapter[PLUGIN_UNIQUE_NAME]} has finished fetching data')
            self._request_gui_dashboard_cache_clear()
            self.log_activity(AuditCategory.CustomDiscovery, AuditAction.Clean, {
                'adapter': _adapter[PLUGIN_NAME]
            })
            self._run_cleaning_phase([_adapter[PLUGIN_UNIQUE_NAME]])
            self._trigger_remote_plugin(STATIC_CORRELATOR_PLUGIN_NAME)
            self._trigger_remote_plugin(STATIC_USERS_CORRELATOR_PLUGIN_NAME)
            self._request_gui_dashboard_cache_clear()

        def connection_custom_discovery_inserted_to_db(*args, **kwargs):
            _adapter = kwargs.get('adapter', {})
            logger.debug(f'{_adapter[PLUGIN_UNIQUE_NAME]} clients has finished fetching data')

            self._trigger_remote_plugin(STATIC_CORRELATOR_PLUGIN_NAME)
            self._trigger_remote_plugin(STATIC_USERS_CORRELATOR_PLUGIN_NAME)
            self._request_gui_dashboard_cache_clear()

        def rejected(err, **kwargs):
            _adapter = kwargs.get('adapter', {})
            logger.exception(f'Failed fetching from {_adapter[PLUGIN_UNIQUE_NAME]}', exc_info=err)

        try:
            clients_trigger_promises = []
            for adapter, clients_with_discovery, clients_without_discovery in adapters_to_call:
                # When adapter has at least one connection with custom discovery enabled, all connections
                # will be triggered separately so clients won't be triggered twice.
                if clients_with_discovery or clients_without_discovery:
                    logger.debug('triggering clients custom discovery')
                    if clients_with_discovery:
                        for client, custom_discovery_configured in clients_with_discovery:
                            self.log_activity(AuditCategory.ConnectionCustomDiscovery, AuditAction.Fetch, {
                                'adapter': adapter[PLUGIN_NAME],
                                'client_id': client['client_id']
                            })
                            clients_trigger_promises.append(self.__trigger_specific_client(adapter, client, True))

                    if clients_without_discovery:
                        self.log_activity(AuditCategory.CustomDiscovery, AuditAction.Fetch, {
                            'adapter': adapter[PLUGIN_NAME]
                        })
                        for client, custom_discovery_configured in clients_without_discovery:
                            clients_trigger_promises.append(self.__trigger_specific_client(adapter, client, False))

                    # run clean phase only if adapter has custom discovery time configured, otherwise
                    # just finalize trigger.
                    # Wrapping with lambdas, to make a closure with the loop params.
                    Promise.all(clients_trigger_promises).then(
                        (lambda _adapter, _clients_without_discovery:
                         lambda _: inserted_to_db(adapter=_adapter) if _clients_without_discovery
                         else connection_custom_discovery_inserted_to_db(adapter=_adapter))
                        (adapter, clients_without_discovery))
                else:
                    logger.debug('triggering adapter custom discovery')
                    self.log_activity(AuditCategory.CustomDiscovery, AuditAction.Fetch, {
                        'adapter': adapter[PLUGIN_NAME]
                    })
                    # pylint: disable=line-too-long
                    self._async_trigger_remote_plugin(adapter[PLUGIN_UNIQUE_NAME], 'insert_to_db')\
                        .then(did_fulfill=self.__promise_callback_wrapper(inserted_to_db, adapter=adapter),
                              did_reject=self.__promise_callback_wrapper(rejected, adapter=adapter))
        except Exception:
            logger.exception('Error triggering custom discovery adapters')
        logger.info('Finished Custom Discovery cycle')

    @staticmethod
    def should_trigger_run_enforcement(trigger: Trigger):
        current_date = datetime.now()
        current_time = current_date.time()
        scheduled_run_time = datetime.strptime(trigger.period_time, '%H:%M').time()

        # check if time matches the scheduled time
        if (current_time < scheduled_run_time or
                time_diff(current_time, scheduled_run_time).seconds > RUN_ENFORCEMENT_CHECK_INTERVAL):
            return False

        if trigger.period == TriggerPeriod.daily:
            # check if X days have passed since last run
            return (not trigger.last_triggered or
                    days_diff(current_date, trigger.last_triggered) == trigger.period_recurrence)

        if trigger.period == TriggerPeriod.weekly:
            # check if weekdays match
            current_weekday = str(current_date.weekday())
            return current_weekday in trigger.period_recurrence

        if trigger.period == TriggerPeriod.monthly:
            current_day = str(current_date.day)
            tomorrow = current_date + timedelta(days=1)
            if tomorrow.month != current_date.month:
                # last day of month is marked in the recurrence as '29'
                current_day = '29'
            return current_day in trigger.period_recurrence

        return False

    def get_enforcements_to_run(self):
        scheduled_enforcements = self._get_collection(REPORTS_PLUGIN_NAME, REPORTS_PLUGIN_NAME).find({
            TRIGGERS_FIELD: {
                '$ne': []
            },
            f'{TRIGGERS_FIELD}.period': {
                '$nin': [TriggerPeriod.all.name, TriggerPeriod.never.name]
            }
        }, projection={
            'name': 1,
            TRIGGERS_FIELD: 1
        })
        for enforcement in scheduled_enforcements:
            try:
                if not enforcement.get(TRIGGERS_FIELD):
                    continue

                trigger = Trigger.from_dict(enforcement[TRIGGERS_FIELD][0])
                if self.should_trigger_run_enforcement(trigger):
                    yield {
                        'report_name': enforcement.get('name', ''),
                        'configuration_name': trigger.name
                    }
            except Exception:
                logger.exception(f'Error checking enforcement "{enforcement.get("name", "unknown")}"')

    def __run_triggered_enforcements(self):
        enforcements_to_run = list(self.get_enforcements_to_run())
        if not enforcements_to_run:
            logger.debug('No enforcements to run, not doing anything at all')
            return
        logger.info(f'Starting to trigger {len(enforcements_to_run)} Enforcements')

        def triggered(*args, **kwargs):
            logger.debug(f'Enforcement has finished running')

        def rejected(err):
            logger.exception(f'Failed running scheduled enforcement', exc_info=err)

        try:
            for enforcement_data in enforcements_to_run:
                self._async_trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'run', data=enforcement_data).then(
                    did_fulfill=triggered, did_reject=rejected)
        except Exception:
            logger.exception('Error triggering enforcements to run')
        logger.info('Finished Triggering Enforcements')

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
            try:
                self._trigger_remote_plugin(plugin[PLUGIN_UNIQUE_NAME],
                                            blocking=blocking,
                                            timeout=24 * 3600, stop_on_timeout=True)
            except ConnectionError:
                # DNS record is missing, let dns watchdog time to reset all the dns records
                logger.warning(f'Failed triggering {plugin[PLUGIN_NAME]} retrying in 80 seconds')
                time.sleep(80)
                try:
                    self._trigger_remote_plugin(plugin[PLUGIN_UNIQUE_NAME],
                                                blocking=blocking,
                                                timeout=24 * 3600, stop_on_timeout=True)
                except ConnectionError:
                    logger.critical(f'Failed triggering {plugin[PLUGIN_NAME]} probably '
                                    f'container is down for some reason')

        with ThreadPoolExecutor() as executor:

            future_for_pre_correlation_plugin = {
                executor.submit(run_trigger_on_plugin, plugin):
                    plugin[PLUGIN_NAME] for plugin in plugins_to_run
            }

            for future in as_completed(future_for_pre_correlation_plugin):
                try:
                    future.result()
                    logger.info(f'{future_for_pre_correlation_plugin[future]} Finished Execution.')
                except Exception:
                    logger.exception(f'Executing {future_for_pre_correlation_plugin[future]} Plugin Failed.')

    def _run_cleaning_phase(self, adapters: dict = None):
        """
        Trigger cleaning all devices from all adapters
        :return:
        """
        data = {
            'adapters': adapters
        }
        self._run_blocking_request(AGGREGATOR_PLUGIN_NAME, 'clean_db', timeout=3600 * 6,
                                   data=data)

    def get_history_config(self):
        """
        Get history config from database
        :return: history config, last saved history date
        """
        try:
            plugin_settings = self.plugins.get_plugin_settings(self.plugin_name)
            history_config = (plugin_settings.configurable_configs[SCHEDULER_CONFIG_NAME] or {}) \
                .get('history_settings') if plugin_settings else {}

            last_history = self.historical_devices_db_view.find_one(filter={},
                                                                    sort=[('accurate_for_datetime', -1)],
                                                                    projection={'accurate_for_datetime': 1})
            last_history_date = last_history.get('accurate_for_datetime') if last_history else None
            return history_config, last_history_date
        except Exception as e:
            logger.exception(f'Error while checking for historical data: {e}')
        return {}, None

    def _run_historical_phase(self, max_days_to_save):
        """
        Trigger saving history
        :return:
        """
        self._run_blocking_request(
            AGGREGATOR_PLUGIN_NAME,
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
        aggregator_job_id = self._run_non_blocking_request(AGGREGATOR_PLUGIN_NAME,
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
        self._wait_for_request(AGGREGATOR_PLUGIN_NAME, 'fetch_filtered_adapters',
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
        if not response or response.status_code not in (200, 403):
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
        logger.info(f'Got a stop request: Back to {Phases.Stable} Phase.')
        try:
            self.__stopping_initiated = True
            self._stop_plugins()
        finally:
            self.current_phase = Phases.Stable
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
