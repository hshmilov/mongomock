import logging

from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger

from axonius.consts.plugin_consts import CONNECTION_DISCOVERY, ENABLE_CUSTOM_DISCOVERY, DISCOVERY_CONFIG_NAME
from axonius.modules.axonius_plugins import AxoniusPlugins
from system_scheduler.custom_schedulers.discovery_scheduler import DiscoveryCustomScheduler

logger = logging.getLogger(f'axonius.{__name__}')


class CustomConnectionsScheduler(DiscoveryCustomScheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugins = AxoniusPlugins(self.db)

    def get_client_trigger(self, adapter_name: str, client_id: str) -> CronTrigger:
        """
        Get crontrigger instance for a connection
        :param adapter_name: adapter name
        :param client_id: client unique id
        :return: crontrigger instance
        """
        adapter_unique_names = self.get_plugin_unique_names(self.db, adapter_name)
        # iterating plugin unique names
        for adapter_unique_name in adapter_unique_names:
            client = self.get_adapter_client(self.db, adapter_unique_name, client_id)
            if not client:
                continue
            connection_discovery = client.get(CONNECTION_DISCOVERY, {})
            trigger = self.get_cron_trigger_from_config(connection_discovery)
            return trigger
        return None

    def init_connections_custom_discovery_scheduling(self, callback):
        """
        Init schedulers for all the connections
        :param callback: schedulers callback function
        :return:
        """
        all_plugins_with_custom_connection_discovery_enabled = self.plugins.get_plugin_names_with_config(
            DISCOVERY_CONFIG_NAME,
            {
                f'{CONNECTION_DISCOVERY}.{ENABLE_CUSTOM_DISCOVERY}': True
            }
        )
        # iterating plugins with custom discovery enabled
        for adapter in all_plugins_with_custom_connection_discovery_enabled:
            adapter_unique_names = self.get_plugin_unique_names(self.db, adapter)
            # iterating plugin unique names
            for adapter_unique_name in adapter_unique_names:
                clients = self.get_adapter_custom_discovery_clients(self.db, adapter_unique_name)
                # iterating plugin connections
                for client in clients:
                    try:
                        connection_discovery = client.get(CONNECTION_DISCOVERY, {})
                        trigger = self.get_cron_trigger_from_config(connection_discovery)
                        client_id = client.get('client_id')
                        job_id = f'{adapter}_{client_id}'
                        self.add_job(
                            job_id=job_id,
                            trigger=trigger,
                            callback=callback,
                            args=(adapter, client_id)
                        )
                    except Exception:
                        client_id = client.get('client_id')
                        logger.exception(f'Error while initiating job for {client_id}')
        self.start_scheduler()

    def update_job(self, adapter_name: str, client_id: str,
                   connection_discovery: dict = None, create: bool = False,
                   callback=None) -> Job:
        """
        update job scheduler time for a connection
        :param adapter_name: adapter name
        :param client_id: client id
        :param connection_discovery: connection discovery config
        :param create: should create a new job if not exists
        :param callback: scheduler trigger function
        :return:
        if connection discovery is provided, use it, otherwise get if from the db
        """
        job_id = f'{adapter_name}_{client_id}'
        if connection_discovery:
            new_trigger_time = self.get_cron_trigger_from_config(connection_discovery)
        else:
            new_trigger_time = self.get_client_trigger(adapter_name, client_id)
        # if new_trigger_time is none it means the job is disabled
        if not new_trigger_time:
            self.remove_job(job_id)
            return None

        job = self.scheduler.get_job(job_id)
        if not job:
            # the jobs does not exist and we dont create it
            if not create or not callback:
                return None
            # create the job
            return self.add_job(
                job_id=job_id,
                trigger=new_trigger_time,
                callback=callback,
                args=(adapter_name, client_id)
            )
        # reschedule an existing job
        job.reschedule(trigger=new_trigger_time)
        logger.info(f'updating custom connection discovery job for {client_id}: {job}')
        return job

    def remove_job_by_client_id(self, adapter_name: str, client_id: str):
        job_id = f'{adapter_name}_{client_id}'
        return super().remove_job(job_id)
