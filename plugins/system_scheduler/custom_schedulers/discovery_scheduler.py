import logging
from typing import List, Dict

from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import \
    ThreadPoolExecutor as ThreadPoolExecutorApscheduler

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.adapter_consts import CLIENT_ID
from axonius.consts.plugin_consts import ENABLE_CUSTOM_DISCOVERY, \
    CONNECTION_DISCOVERY, DISCOVERY_REPEAT_TYPE, DISCOVERY_REPEAT_ON_WEEKDAYS, DISCOVERY_REPEAT_EVERY_DAY, \
    DISCOVERY_RESEARCH_DATE_TIME, DISCOVERY_REPEAT_ON, DISCOVERY_REPEAT_EVERY, CLIENTS_COLLECTION, DISCOVERY_REPEAT_RATE
from axonius.db.db_client import get_db_client

from axonius.plugin_base import PluginBase

logger = logging.getLogger(f'axonius.{__name__}')

MINUTES_IN_HOUR = 60


class DiscoveryCustomScheduler:
    MAX_WORKERS = 5

    def __init__(self, db=None):
        self.db = db if db else get_db_client()
        self.scheduler = LoggedBackgroundScheduler(executors={
            'default': ThreadPoolExecutorApscheduler(self.MAX_WORKERS)
        })

    @staticmethod
    def get_cron_by_rate(rate_in_hours: float):
        """
        get crontrigger instance by repeat rate
        :param rate_in_hours: repeat rate in hours
        :return:
        """
        cron_minutes = 0
        cron_hours = '*'
        if rate_in_hours < 1:
            rate_in_minutes = int(MINUTES_IN_HOUR * rate_in_hours)
            cron_minutes = f'*/{rate_in_minutes}'
        elif rate_in_hours >= 24:
            return CronTrigger(hour=0,
                               minute=0,
                               second=0,
                               day='*')
        else:
            cron_hours = f'*/{rate_in_hours}'
        return CronTrigger(hour=cron_hours,
                           minute=cron_minutes,
                           second='0',
                           day='*')

    @staticmethod
    def get_cron_trigger_from_config(config: dict) -> CronTrigger:
        """
        Get adapter custom discovery config and return a crontrigger instance
        :param config: custom discovery config
        :return: crontrigger instance
        """
        if not config.get(ENABLE_CUSTOM_DISCOVERY):
            # discovery is disabled
            return None

        repeat_type = config.get(DISCOVERY_REPEAT_TYPE)
        if repeat_type == DISCOVERY_REPEAT_RATE:
            rate_in_hours = config.get(DISCOVERY_REPEAT_RATE)
            return DiscoveryCustomScheduler.get_cron_by_rate(rate_in_hours)

        hour, minute = config.get(repeat_type, {}). \
            get(DISCOVERY_RESEARCH_DATE_TIME).split(':')
        if repeat_type == DISCOVERY_REPEAT_ON_WEEKDAYS:
            # transform weekday names to cron names: [Sunday,monday] -> sun,mon
            repeat_days = config.get(DISCOVERY_REPEAT_ON_WEEKDAYS, {}).get(DISCOVERY_REPEAT_ON, [])
            weekdays_for_cron = ','.join([day[:3].lower() for day in
                                          repeat_days])
            return CronTrigger(hour=hour,
                               minute=minute,
                               second='0',
                               day_of_week=weekdays_for_cron)
        if repeat_type == DISCOVERY_REPEAT_EVERY_DAY:
            recurrence = config.get(DISCOVERY_REPEAT_EVERY_DAY, {}).get(DISCOVERY_REPEAT_EVERY, 1)
            return CronTrigger(hour=hour,
                               minute=minute,
                               second='0',
                               day=f'*/{recurrence}')
        return None

    @staticmethod
    def get_adapter_clients(adapter_unique_name: str) -> List[Dict]:
        """
        :param adapter_unique_name: Adapter unique name
        :return: Returns all the clients from the adapter
        """
        return PluginBase.Instance.mongo_client[adapter_unique_name][CLIENTS_COLLECTION] \
            .find({}, projection={CONNECTION_DISCOVERY: 1, CLIENT_ID: 1, '_id': 1})

    @staticmethod
    def get_adapter_custom_discovery_clients(adapter_unique_name: str) -> List[Dict]:
        """
        :param adapter_unique_name: Adapter unique name
        :return: Returns all the clients from the adapter
        """
        return PluginBase.Instance.mongo_client[adapter_unique_name][CLIENTS_COLLECTION] \
            .find({
                ENABLE_CUSTOM_DISCOVERY: True
            }, projection={CONNECTION_DISCOVERY: 1, CLIENT_ID: 1, '_id': 1})

    @staticmethod
    def get_adapter_client(adapter_unique_name: str, client_id: str) -> Dict:
        """
        :param client_id: client unique id
        :param adapter_unique_name: Adapter unique name
        :return: return the client from the adapter
        """
        return PluginBase.Instance.mongo_client[adapter_unique_name][CLIENTS_COLLECTION].find_one({
            'client_id': client_id
        }, projection={CONNECTION_DISCOVERY: 1, CLIENT_ID: 1, '_id': 1})

    @staticmethod
    def get_plugin_unique_names(plugin_name: str) -> List:
        """
        get plugin unique names for plugin
        :param plugin_name: plugin name
        :return:
        """
        for plugin in PluginBase.Instance.core_configs_collection.find({
                'plugin_name': plugin_name
        }, projection={
            'plugin_unique_name': 1
        }):
            yield plugin.get('plugin_unique_name')

    def start_scheduler(self):
        self.scheduler.start()

    def add_job(self, job_id: str, trigger: CronTrigger, callback, args) -> Job:
        """
        add job to the scheduler
        :param job_id: job id
        :param trigger: crontrigger  instance
        :param callback: scheduler callback function
        :return:
        """
        try:
            job = self.scheduler.add_job(func=callback,
                                         trigger=trigger,
                                         args=args,
                                         id=job_id,
                                         max_instances=1)
            logger.info(f'Adding {self.__class__.__name__} job for {job_id}: {job}')
        except Exception:
            logger.exception(f'Error while adding {self.__class__.__name__} job for {job_id}')
            return None
        return job

    def remove_job(self, job_id: str):
        """
        remove job from the scheduler
        :param job_id: job id
        :return:
        """
        if self.scheduler.get_job(job_id):
            logger.info(f'Remove {self.__class__.__name__} job for {job_id}')
            self.scheduler.remove_job(job_id)

    def remove_all_jobs(self):
        logger.info(f'Remove all jobs for {self.__class__.__name__}')
        self.scheduler.remove_all_jobs()
