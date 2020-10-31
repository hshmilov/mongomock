import logging

from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger

from axonius.modules.axonius_plugins import AxoniusPlugins
from axonius.consts.plugin_consts import ENABLE_CUSTOM_HISTORY, HISTORY_REPEAT_TYPE, HISTORY_REPEAT_TIME, \
    HISTORY_REPEAT_WEEKDAYS, HISTORY_REPEAT_EVERY_DAY, HISTORY_REPEAT_ON, HISTORY_REPEAT_RECURRENCE,\
    HISTORY_REPEAT_EVERY_LIFECYCLE, HISTORY_CONFIG_NAME
from axonius.consts.scheduler_consts import SCHEDULER_CONFIG_NAME
from system_scheduler.custom_schedulers.discovery_scheduler import CustomScheduler

logger = logging.getLogger(f'axonius.{__name__}')


class HistoryScheduler(CustomScheduler):
    JOB_NAME = 'history'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugins = AxoniusPlugins(self.db)

    def get_trigger_time(self) -> CronTrigger:
        """
        Get trigger time for the history scheduler job
        :return: crontrigger
        """
        config = self.plugins.system_scheduler.configurable_configs[SCHEDULER_CONFIG_NAME]
        trigger = self.get_cron_trigger_from_config(config.get(HISTORY_CONFIG_NAME, {}))
        return trigger

    @staticmethod
    def get_cron_trigger_from_config(config: dict) -> CronTrigger:
        """
        Get custom history schedule config and return a crontrigger instance
        :param config: custom history config
        :return: crontrigger instance
        """
        if not config.get(ENABLE_CUSTOM_HISTORY):
            # history is disabled
            return None

        repeat_type = config.get(HISTORY_REPEAT_TYPE)

        if repeat_type == HISTORY_REPEAT_EVERY_LIFECYCLE:
            return None

        hour, minute = config.get(repeat_type, {}).get(HISTORY_REPEAT_TIME).split(':')

        if repeat_type == HISTORY_REPEAT_WEEKDAYS:
            repeat_days = config.get(HISTORY_REPEAT_WEEKDAYS, {}).get(HISTORY_REPEAT_ON, [])
            return CustomScheduler.get_weekdays_cron_trigger(repeat_days, hour, minute)

        if repeat_type == HISTORY_REPEAT_EVERY_DAY:
            recurrence = config.get(HISTORY_REPEAT_EVERY_DAY, {}).get(HISTORY_REPEAT_RECURRENCE, 1)
            return CustomScheduler.get_repeat_every_x_days_cron_trigger(recurrence, hour, minute)

        return None

    def init_history_custom_scheduling(self, callback):
        """
        init scheduler custom history jobs
        :param callback: scheduler callback function
        :return:
        """
        try:
            trigger = self.get_trigger_time()
            if trigger:
                self.add_job(job_id=self.JOB_NAME,
                             trigger=trigger,
                             callback=callback,
                             args=None)
        except Exception:
            logger.exception(f'Error while initiating history job')

        self.start_scheduler()

    def update_job(self, create: bool = False, callback=None) -> Job:
        """
        Update history job
        :param create: should create if the job not exists
        :param callback: scheduler callback function
        :return:
        """
        job = self.scheduler.get_job(self.JOB_NAME)
        if not job:
            if not create or not callback:
                return None
            trigger = self.get_trigger_time()
            # custom history schedule is disabled.
            if not trigger:
                return None
            return self.add_job(job_id=self.JOB_NAME,
                                trigger=trigger,
                                callback=callback,
                                args=None)
        new_trigger_time = self.get_trigger_time()
        if not new_trigger_time:
            self.remove_job(self.JOB_NAME)
            return None
        job.reschedule(trigger=new_trigger_time)
        logger.info(f'Updating {self.__class__.__name__} custom history job for {self.JOB_NAME}: {job}')
        return job
