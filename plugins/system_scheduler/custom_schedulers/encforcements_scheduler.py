import calendar
import logging

from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger

from axonius.consts.plugin_consts import REPORTS_PLUGIN_NAME
from axonius.consts.report_consts import TRIGGERS_FIELD
from axonius.types.enforcement_classes import Trigger, TriggerPeriod
from system_scheduler.custom_schedulers.discovery_scheduler import CustomScheduler

logger = logging.getLogger(f'axonius.{__name__}')

MINUTES_IN_HOUR = 60


class EnforcementsCustomScheduler(CustomScheduler):

    @staticmethod
    def get_cron_trigger_from_config(config: dict) -> CronTrigger:
        """
        Get adapter custom discovery config and return a crontrigger instance
        :param config:
        :return: crontrigger instance
        """
        trigger = Trigger.from_dict(config)
        hour, minute = trigger.period_time.split(':')

        if trigger.period == TriggerPeriod.daily:
            recurrence = trigger.period_recurrence
            return CronTrigger(hour=hour,
                               minute=minute,
                               second='0',
                               day=f'*/{recurrence}')

        if trigger.period == TriggerPeriod.weekly:
            scheduled_weekdays = [calendar.day_name[int(x)] for x in trigger.period_recurrence]
            weekdays_for_cron = ','.join([day[:3].lower() for day in
                                          scheduled_weekdays])
            return CronTrigger(hour=hour,
                               minute=minute,
                               second='0',
                               day_of_week=weekdays_for_cron)

        if trigger.period == TriggerPeriod.monthly:
            return CronTrigger(hour=hour,
                               minute=minute,
                               second='0',
                               day_of_week=','.join(str(x) for x in trigger.period_recurrence))
        return None

    def init_enforcements_custom_discovery_scheduling(self, callback):
        """
        init scheduler custom discovery jobs for adapters
        :param callback: scheduler callback function
        :return:
        """
        scheduled_enforcements = self.db[REPORTS_PLUGIN_NAME][REPORTS_PLUGIN_NAME].find({
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
                enforcement_name = enforcement.get('name')
                trigger = self.get_cron_trigger_from_config(enforcement[TRIGGERS_FIELD][0])
                self.add_job(job_id=enforcement_name,
                             trigger=trigger,
                             callback=callback,
                             args=(enforcement_name,))
            except Exception:
                logger.exception(f'Error initiating job for enforcement "{enforcement.get("name", "unknown")}"')

        self.start_scheduler()

    def get_enforcement_trigger_time(self, enforcement_name):
        enforcement = self.db[REPORTS_PLUGIN_NAME][REPORTS_PLUGIN_NAME].find_one({
            'name': enforcement_name
        })
        if not enforcement:
            return None
        return self.get_cron_trigger_from_config(enforcement[TRIGGERS_FIELD][0])

    def update_job(self, enforcement_name: str, create: bool = False, callback=None) -> Job:
        """
        Update custom discovery job
        :param enforcement_name:
        :param create: should create if the job not exists
        :param callback: scheduler callback function
        :return:
        """
        job = self.scheduler.get_job(enforcement_name)
        if not job:
            if not create or not callback:
                return None
            trigger = self.get_enforcement_trigger_time(enforcement_name)
            return self.add_job(job_id=enforcement_name,
                                trigger=trigger,
                                callback=callback,
                                args=(enforcement_name,))
        new_trigger_time = self.get_enforcement_trigger_time(enforcement_name)
        if not new_trigger_time:
            self.remove_job(enforcement_name)
            return None
        job.reschedule(trigger=new_trigger_time)
        logger.info(f'updating {self.__class__.__name__} custom discovery job for {enforcement_name}: {job}')
        return job
