# pylint: disable=too-many-lines
import base64
import functools
import logging
import threading
import time
from concurrent.futures import (ALL_COMPLETED, ThreadPoolExecutor,
                                as_completed, wait)
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Set, Dict, List
from dateutil import tz
import requests

import pytz
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import jsonify, request

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
                                          GUI_PLUGIN_NAME,
                                          ENABLE_CUSTOM_DISCOVERY, DISCOVERY_REPEAT_ON,
                                          DISCOVERY_RESEARCH_DATE_TIME,
                                          STATIC_USERS_CORRELATOR_PLUGIN_NAME,
                                          SYSTEM_SCHEDULER_PLUGIN_NAME,
                                          AGGREGATOR_PLUGIN_NAME, CONNECTION_DISCOVERY,
                                          HISTORY_REPEAT_ON, HISTORY_REPEAT_TYPE,
                                          HISTORY_REPEAT_EVERY, HISTORY_REPEAT_WEEKDAYS, HISTORY_REPEAT_RECURRENCE,
                                          HISTORY_REPEAT_EVERY_LIFECYCLE, WEEKDAYS, CLIENT_ACTIVE)
from axonius.consts.plugin_subtype import PluginSubtype
from axonius.consts.scheduler_consts import (SchedulerState, Phases, ResearchPhases,
                                             CHECK_ADAPTER_CLIENTS_STATUS_INTERVAL, TUNNEL_STATUS_CHECK_INTERVAL,
                                             RESEARCH_THREAD_ID, CORRELATION_SCHEDULER_THREAD_ID,
                                             SCHEDULER_CONFIG_NAME, SCHEDULER_SAVE_HISTORY_CONFIG_NAME)
from axonius.consts.report_consts import TRIGGERS_FIELD
from axonius.entities import EntityType
from axonius.logging.audit_helper import (AuditCategory, AuditAction)
from axonius.logging.metric_helper import log_metric
from axonius.mixins.configurable import Configurable
from axonius.mixins.triggerable import StoredJobStateCompletion, Triggerable, RunIdentifier
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.plugin_exceptions import PhaseExecutionException
from axonius.saas.input_params import read_saas_input_params
from axonius.thread_stopper import StopThreadException
from axonius.utils.backup import backup_to_s3, backup_to_external
from axonius.utils.files import get_local_config_file
from axonius.utils.root_master.root_master import root_master_restore_from_s3, \
    root_master_restore_from_smb, root_master_restore_from_azure, DISK_SPACE_FREE_GB_MANDATORY, get_central_core_module
from axonius.utils.host_utils import get_free_disk_space, check_installer_locks
from system_scheduler.custom_schedulers.adapter_connections_scheduler import CustomConnectionsScheduler
from system_scheduler.custom_schedulers.adapter_scheduler import CustomAdapterScheduler
from system_scheduler.custom_schedulers.discovery_scheduler import DiscoveryCustomScheduler
from system_scheduler.custom_schedulers.encforcements_scheduler import EnforcementsCustomScheduler

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

        self.__adapter_clients_status = LoggedBackgroundScheduler(executors={
            'default': ThreadPoolExecutorApscheduler(1)
        })

        self.__run_preferred_fields_calculation = LoggedBackgroundScheduler(executors={
            'default': ThreadPoolExecutorApscheduler(1)
        })
        self.__run_preferred_fields_calculation.add_job(func=self.__run_preferred_field_calculations,
                                                        trigger=IntervalTrigger(
                                                            hours=self._calculate_preferred_fields_interval),
                                                        next_run_time=datetime.now(),
                                                        max_instances=1)
        self.__run_preferred_fields_calculation.start()

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

        self.custom_adapter_scheduler = None
        self.custom_connection_scheduler = None
        self.custom_enforcements_scheduler = None
        self.init_custom_schedulers()

    def init_custom_schedulers(self):
        try:
            self.custom_adapter_scheduler = CustomAdapterScheduler(db=self.mongo_client)
            self.custom_adapter_scheduler.init_adapters_custom_discovery_scheduling(
                self.trigger_custom_discovery_adapter
            )
        except Exception:
            logger.critical('Error while configuring custom adapter discovery scheduler', exc_info=True)
        try:
            self.custom_connection_scheduler = CustomConnectionsScheduler(db=self.mongo_client)
            self.custom_connection_scheduler.init_connections_custom_discovery_scheduling(
                self.trigger_custom_discovery_connection
            )
        except Exception:
            logger.critical('Error while configuring custom adapter connections scheduler', exc_info=True)
        try:
            self.custom_enforcements_scheduler = EnforcementsCustomScheduler(db=self.mongo_client)
            self.custom_enforcements_scheduler.init_enforcements_custom_discovery_scheduling(
                self.trigger_custom_enforcement
            )
        except Exception:
            logger.critical('Error while configuring custom enforcements schedulers', exc_info=True)

    def run_correlations(self):
        if self.__correlation_lock.acquire(False):
            try:
                logger.info(f'Running correlation')
                self._run_plugins(self._get_plugins(PluginSubtype.Correlator), 72 * 3600)
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

    @add_rule('trigger_azure_backup')
    def trigger_azure_backup_external(self):
        return jsonify({'result': str(self.trigger_azure_backup())})

    @staticmethod
    def trigger_azure_backup():
        return str(backup_to_external(services=['azure']))

    @add_rule('trigger_root_master_azure_restore')
    def trigger_root_master_azure_restore_external(self):
        return jsonify({'result': str(self.trigger_root_master_azure_restore())})

    @staticmethod
    def trigger_root_master_azure_restore():
        return str(root_master_restore_from_azure())

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

        history_data_settings = config.get('history_data_settings') or {}
        if history_data_settings.get('save_raw_data'):
            self.__save_raw_data = True
        else:
            self.__save_raw_data = False

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
                                    'type': 'integer'
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
                            'title': 'Constantly run enforcement sets',
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
                                    'type': 'integer',
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
                },
                {
                    'name': 'history_data_settings',
                    'title': 'Historical Snapshot Data Settings',
                    'type': 'array',
                    'items': [
                        {
                            'name': 'save_raw_data',
                            'title': 'Save entity advanced view data',
                            'type': 'bool'
                        },
                    ],
                    'required': ['save_raw_data']
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
            'history_data_settings': {
                'save_raw_data': False
            }
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
                    logger.info(f'Central Core mode enabled')

                    free_disk_space_in_gb = get_free_disk_space() / (1024 ** 3)
                    if free_disk_space_in_gb < DISK_SPACE_FREE_GB_MANDATORY:
                        self.create_notification(
                            f'Central Core Failure',
                            f'Could not run central core cycle successfully due to low disk space (beginning)',
                            severity_type='error'
                        )
                        raise ValueError(f'ERROR - do not have enough free disk space to start central core cycle')

                    # 1. Restore from various places
                    if self._aws_s3_settings.get('enabled'):
                        root_master_restore_from_s3()
                    if self._smb_settings.get('enabled'):
                        root_master_restore_from_smb()
                    if self._azure_storage_settings.get('enabled'):
                        root_master_restore_from_azure()

                    # 2. Run historical phase
                    try:
                        history_config, last_history_date = self.get_history_config()
                        if self.__save_history and self.should_save_history(history_config, last_history_date):
                            # Save history.
                            _change_subphase(ResearchPhases.Save_Historical)
                            free_disk_space_in_gb = get_free_disk_space() / (1024 ** 3)
                            if free_disk_space_in_gb < MIN_GB_TO_SAVE_HISTORY:
                                logger.error(f'Can not save history - less than 15 GB on disk!')
                            else:
                                self._run_historical_phase()
                    except Exception:
                        logger.critical(f'Failed running save historical phase')
                        self.create_notification(
                            f'Central Core Failure',
                            f'Could not run central core cycle successfully due to low disk space (history-phase)',
                            severity_type='error'
                        )

                    # 3. Change to new devices_db, users_db, etc. Do not ever promote if the DB is empty!
                    central_core = get_central_core_module()
                    new_device_count = central_core.entity_db_map[EntityType.Devices].count({})
                    new_user_count = central_core.entity_db_map[EntityType.Users].count({})

                    if new_device_count == 0 and new_user_count == 0:
                        logger.critical(f'New device count and new user count is 0, not promoting!')
                        self.create_notification(
                            f'Central Core Failure',
                            f'Could not run central core - no backups were parsed! '
                            f'Please check if a recent backup has been uploaded',
                            severity_type='error'
                        )
                    else:
                        central_core.promote_central_core()
                        self._request_gui_dashboard_cache_clear(clear_slow=True)

                    # 4. Run enforcement center
                    _change_subphase(ResearchPhases.Post_Correlation)
                    post_correlation_plugins = [plugin for plugin in self._get_plugins(PluginSubtype.PostCorrelation)
                                                if plugin[PLUGIN_NAME] == REPORTS_PLUGIN_NAME]
                    if post_correlation_plugins:
                        self._run_plugins(post_correlation_plugins)
                        self._request_gui_dashboard_cache_clear()

                except Exception:
                    logger.critical(f'Could not complete root-master cycle')

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
                self._trigger_remote_plugin(AGGREGATOR_PLUGIN_NAME, 'calculate_preferred_fields', blocking=True)
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
                        self._run_historical_phase()

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
                elif self._azure_storage_settings.get('enabled') and self._azure_storage_settings.get('enable_backups'):
                    threading.Thread(target=backup_to_external, args=(['azure'],)).start()
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

    def get_adapter_clients_filtered_count(self, adapter_unique_name: str) -> List[Dict]:
        """
        Gets all active clients (connections) without custom discovery count from adapter
        :param adapter_unique_name: Adapter unique name
        :return: Returns the amount of clients in adapter
        """
        return self._get_db_connection()[adapter_unique_name][CLIENTS_COLLECTION].count_documents({
            CLIENT_ACTIVE: {'$ne': False},
            f'{CONNECTION_DISCOVERY}.{ENABLE_CUSTOM_DISCOVERY}': True
        })

    def get_adapter_active_clients(self, adapter_unique_name: str) -> List[Dict]:
        """
        Gets all active clients (connections)
        :param adapter_unique_name: Adapter unique name
        :return: Returns the active clients in adapter
        """
        return self._get_db_connection()[adapter_unique_name][CLIENTS_COLLECTION]\
            .find({CLIENT_ACTIVE: {'$ne': False}},
                  projection={CONNECTION_DISCOVERY: 1, CLIENT_ID: 1, LAST_FETCH_TIME: 1, '_id': 1})

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

    def trigger_custom_discovery_adapter(self, adapter_name: str):
        """
        Trigger custom discovery adapter
        :param adapter_name: adapter to trigger
        :return:
        """
        def inserted_to_db(*args, **kwargs):
            plugin_unique_name = kwargs.get('plugin_unique_name')
            logger.debug(f'{plugin_unique_name} has finished fetching data')
            self._request_gui_dashboard_cache_clear()
            self.log_activity(AuditCategory.CustomDiscovery, AuditAction.Clean, {
                'adapter': adapter_name
            })
            self._run_cleaning_phase([plugin_unique_name])
            self._trigger_remote_plugin(STATIC_CORRELATOR_PLUGIN_NAME)
            self._trigger_remote_plugin(STATIC_USERS_CORRELATOR_PLUGIN_NAME)
            self._trigger_remote_plugin(AGGREGATOR_PLUGIN_NAME, 'calculate_preferred_fields', blocking=True)
            self._request_gui_dashboard_cache_clear()

        def rejected(err, **kwargs):
            plugin_unique_name = kwargs.get('plugin_unique_name', {})
            logger.exception(f'Failed fetching from {plugin_unique_name}', exc_info=err)

        try:
            if check_installer_locks(unlink=False):
                logger.info(f'Installer is in progress, not triggering custom discovery cycle for {adapter_name}')
                return

            clients_to_trigger = {}
            # get adapter connections without enabled custom connection discovery
            for adapter_unique_name in \
                    DiscoveryCustomScheduler.get_plugin_unique_names(self.mongo_client, adapter_name):
                adapter_clients = DiscoveryCustomScheduler.get_adapter_clients(self.mongo_client, adapter_unique_name)
                for client in adapter_clients:
                    connection_discovery = client.get(CONNECTION_DISCOVERY, {})
                    if not connection_discovery.get(ENABLE_CUSTOM_DISCOVERY):
                        clients_to_trigger.setdefault(adapter_unique_name, []).append(client.get('client_id'))

            self.log_activity(AuditCategory.CustomDiscovery, AuditAction.Fetch, {
                'adapter': adapter_name
            })

            for adapter_unique_name, clients in clients_to_trigger.items():
                self._async_trigger_remote_plugin(adapter_unique_name, 'insert_to_db',
                                                  data={'client_names': clients}) \
                    .then(did_fulfill=functools.partial(inserted_to_db,
                                                        plugin_unique_name=adapter_unique_name),
                          did_reject=functools.partial(rejected, plugin_unique_name=adapter_unique_name))

        except Exception:
            logger.exception('Error triggering custom discovery adapters')
        logger.info('Finished Custom Discovery cycle')

    def is_connection_active(self, adapter_unique_name, client_id):
        try:
            client_data = self.mongo_client[adapter_unique_name]['clients'].find_one({
                'client_id': client_id
            })
            return client_data and client_data.get(CLIENT_ACTIVE)
        except Exception:
            logger.exception(f'Error while checking connection status for {adapter_unique_name}:{client_id}')
        return None

    def __run_preferred_field_calculations(self):
        self._trigger_remote_plugin(AGGREGATOR_PLUGIN_NAME, 'calculate_preferred_fields', blocking=True)

    def trigger_custom_discovery_connection(self, adapter_name: str, client_id: str):

        def connection_custom_discovery_inserted_to_db(*args, **kwargs):
            plugin_unique_name = kwargs.get('plugin_unique_name')
            logger.debug(f'{plugin_unique_name} has finished fetching data for client_id: {client_id}')

            self._trigger_remote_plugin(STATIC_CORRELATOR_PLUGIN_NAME)
            self._trigger_remote_plugin(STATIC_USERS_CORRELATOR_PLUGIN_NAME)
            self._request_gui_dashboard_cache_clear()

        def rejected(err, **kwargs):
            plugin_unique_name = kwargs.get('plugin_unique_name')
            client_id = kwargs.get('client_id')
            logger.exception(f'Failed fetching from plugin_unique_name {plugin_unique_name} for {client_id}',
                             exc_info=err)

        try:
            if check_installer_locks(unlink=False):
                logger.info(f'Installer is in progress, '
                            f'not triggering custom discovery connection for {adapter_name}:{client_id}')
                return
            for adapter_unique_name in \
                    DiscoveryCustomScheduler.get_plugin_unique_names(self.mongo_client, adapter_name):
                try:
                    # we are triggering the adapter with this unique job name
                    # because we dont want triggerable to think these jobs are duplicates
                    encoded_client_id = base64.b64encode(client_id.encode()).decode()
                    job_name = f'insert_to_db_{encoded_client_id}'
                    if not self.is_connection_active(adapter_unique_name, client_id):
                        logger.debug(f'{adapter_unique_name}:{client_id} is inactive, not triggering custom connection')
                        continue
                    self.log_activity(AuditCategory.ConnectionCustomDiscovery, AuditAction.Fetch, {
                        'adapter': adapter_name,
                        'client_id': client_id
                    })
                    logger.info(
                        f'triggering {adapter_unique_name} for custom connection discovery, client_id: {client_id}'
                    )
                    self._async_trigger_remote_plugin(adapter_unique_name, job_name, data={
                        'client_name': client_id,
                    }).then(
                        did_fulfill=functools.partial(connection_custom_discovery_inserted_to_db,
                                                      plugin_unique_name=adapter_unique_name, client_id=client_id),
                        did_reject=functools.partial(rejected, plugin_unique_name=adapter_unique_name)
                    )
                except Exception:
                    logger.exception('Error triggering custom discovery adapter client')

        except Exception:
            logger.exception('Error triggering custom discovery adapters')
        logger.info('Finished Custom Discovery Connection trigger')

    def trigger_custom_enforcement(self, enforcement_name):
        def triggered(*args, **kwargs):
            logger.debug(f'Custom scheduled {enforcement_name} enforcement has finished running')

        def rejected(err):
            logger.exception(f'Failed running custom scheduled enforcement {enforcement_name}', exc_info=err)

        try:
            if check_installer_locks(unlink=False):
                logger.info(f'Installer is in progress, '
                            f'not triggering custom discovery enforcement for {enforcement_name}')
                return
            enforcement = self._get_collection(REPORTS_PLUGIN_NAME, REPORTS_PLUGIN_NAME).find_one({
                'name': enforcement_name
            })
            data = {
                'report_name': enforcement.get('name', ''),
                'configuration_name': enforcement[TRIGGERS_FIELD][0].get('name')
            }
            self._async_trigger_remote_plugin(REPORTS_PLUGIN_NAME, 'run', data=data, priority=True).then(
                did_fulfill=triggered, did_reject=rejected)
        except Exception:
            logger.exception(f'Error triggering custom scheduled enforcement: {enforcement_name}')
        logger.info(f'Finished Triggering Custom Scheduled Enforcement: {enforcement_name}')

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

    def _run_plugins(self, plugins_to_run: list, timeout=24 * 3600):
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
                                            timeout=timeout, stop_on_timeout=True)
            except Exception:
                # DNS record is probably missing, let dns watchdog time to reset all the dns records
                logger.warning(f'Failed triggering {plugin[PLUGIN_NAME]} retrying in 80 seconds')
                time.sleep(80)
                try:
                    self._trigger_remote_plugin(plugin[PLUGIN_UNIQUE_NAME],
                                                blocking=blocking,
                                                timeout=timeout, stop_on_timeout=True)
                except Exception:
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

    def _run_historical_phase(self, max_days_to_save=None, save_raw_data=None):
        """
        Trigger saving history
        :return:
        """
        if max_days_to_save is None:
            max_days_to_save = self.__max_days_to_save

        if save_raw_data is None:
            save_raw_data = self.__save_raw_data

        self._run_blocking_request(
            AGGREGATOR_PLUGIN_NAME,
            'save_history',
            data={'max_days_to_save': max_days_to_save, 'save_raw_data': save_raw_data},
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

    @add_rule('update_custom_adapter_scheduler', methods=['POST'])
    def update_custom_adapter_scheduler(self):
        data = request.get_json(silent=True)
        if data is None:
            return return_error('No data received')
        adapter_name = data.get('adapter_name')
        try:
            self.custom_adapter_scheduler.update_job(adapter_name, create=True,
                                                     callback=self.trigger_custom_discovery_adapter)
        except Exception as e:
            logger.exception(f'Error while updating {adapter_name} adapter scheduler {e}')
            return return_error(str(e), non_prod_error=True, http_status=500)
        return 'OK', 200

    @add_rule('update_connection_scheduler', methods=['POST'])
    def update_custom_connection_scheduler(self):
        data = request.get_json(silent=True)
        if data is None:
            return return_error('No data received')

        client_id = data.get('client_id')
        adapter_name = data.get('adapter_name')
        connection_discovery = data.get(CONNECTION_DISCOVERY, {})
        try:
            self.custom_connection_scheduler.update_job(
                adapter_name, client_id, connection_discovery=connection_discovery,
                create=True, callback=self.trigger_custom_discovery_connection)
        except Exception as e:
            logger.exception(f'Error while updating {adapter_name}:{client_id} scheduler {e}')
            return return_error(str(e), non_prod_error=True, http_status=500)
        return 'OK', 200

    @add_rule('remove_custom_connections_scheduler_job', methods=['POST'])
    def remove_custom_connections_scheduler_job(self):
        try:
            data = request.get_json(silent=True)
            if data:
                client_id = data.get('client_id')
                adapter_name = data.get('adapter_name')
                if client_id and adapter_name:
                    self.custom_connection_scheduler.remove_job_by_client_id(adapter_name, client_id)
                else:
                    logger.exception(f'Wrong data {adapter_name}{client_id}')
            else:
                self.custom_connection_scheduler.remove_all_jobs()
        except Exception as e:
            logger.exception(f'Error while updating removing all custom connections scheduler jobs {e}')
            return return_error(str(e), non_prod_error=True, http_status=500)
        return 'OK', 200

    @add_rule('update_custom_enforcement', methods=['POST'])
    def update_custom_enforcement(self):
        data = request.get_json(silent=True)
        if data is None:
            return return_error('No data received')
        enforcement_name = data.get('enforcement_name')
        try:
            self.custom_enforcements_scheduler.update_job(enforcement_name, create=True,
                                                          callback=self.trigger_custom_enforcement)
        except Exception as e:
            logger.exception(f'Error while updating {enforcement_name} enforcement scheduler {e}')
            return return_error(str(e), non_prod_error=True, http_status=500)
        return 'OK', 200
