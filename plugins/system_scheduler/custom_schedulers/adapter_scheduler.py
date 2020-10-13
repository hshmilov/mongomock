import logging

from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger

from axonius.consts.plugin_consts import ADAPTER_DISCOVERY, DISCOVERY_CONFIG_NAME, ENABLE_CUSTOM_DISCOVERY
from axonius.modules.axonius_plugins import AxoniusPlugins
from system_scheduler.custom_schedulers.discovery_scheduler import DiscoveryCustomScheduler

logger = logging.getLogger(f'axonius.{__name__}')


class CustomAdapterScheduler(DiscoveryCustomScheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugins = AxoniusPlugins(self.db)

    def get_adapter_trigger_time(self, adapter_name: str) -> CronTrigger:
        """
        Get trigger time for the adapter
        :param adapter_name: adapter name
        :return: crontrigger
        """
        plugin_settings = self.plugins.get_plugin_settings(adapter_name)
        discovery_config = plugin_settings.configurable_configs.discovery_configuration[ADAPTER_DISCOVERY]
        trigger = self.get_cron_trigger_from_config(discovery_config)
        return trigger

    def init_adapters_custom_discovery_scheduling(self, callback):
        """
        init scheduler custom discovery jobs for adapters
        :param callback: scheduler callback function
        :return:
        """
        all_plugins_with_custom_discovery_enabled = self.plugins.get_plugin_names_with_config(
            DISCOVERY_CONFIG_NAME,
            {
                f'{ADAPTER_DISCOVERY}.{ENABLE_CUSTOM_DISCOVERY}': True
            }
        )
        for adapter_name in all_plugins_with_custom_discovery_enabled:
            try:
                trigger = self.get_adapter_trigger_time(adapter_name)
                self.add_job(job_id=adapter_name,
                             trigger=trigger,
                             callback=callback,
                             args=(adapter_name,))
            except Exception:
                logger.exception(f'Error while initiating job for {adapter_name}')

        self.start_scheduler()

    def update_job(self, adapter_name: str, create: bool = False, callback=None) -> Job:
        """
        Update custom discovery job
        :param adapter_name: adapter name
        :param create: should create if the job not exists
        :param callback: scheduler callback function
        :return:
        """
        job = self.scheduler.get_job(adapter_name)
        if not job:
            if not create or not callback:
                return None
            trigger = self.get_adapter_trigger_time(adapter_name)
            # custom adapter discovery is disabled
            if not trigger:
                return None
            return self.add_job(job_id=adapter_name,
                                trigger=trigger,
                                callback=callback,
                                args=(adapter_name,))
        new_trigger_time = self.get_adapter_trigger_time(adapter_name)
        if not new_trigger_time:
            self.remove_job(adapter_name)
            return None
        job.reschedule(trigger=new_trigger_time)
        logger.info(f'updating adapter custom discovery job for {adapter_name}: {job}')
        return job
