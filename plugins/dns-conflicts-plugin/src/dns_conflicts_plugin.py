from axonius.PluginBase import PluginBase, add_rule
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import timedelta, datetime
import time
from axonius.dns_utils import query_dns, NoIpFoundError
import json
from axonius.mixins.Activatable import Activatable
import threading


class DnsConflictsPlugin(PluginBase, Activatable):
    def _is_work_in_progress(self) -> bool:

        if self.resolve_lock.acquire(False):
            self.resolve_lock.release()
            return False
        return True

    def _stop_activatable(self):
        self.scheduler.pause()

    def _start_activatable(self):
        self.scheduler.resume()
        self.check_ip_conflict_now()

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self.resolve_lock = threading.RLock()

        executors = {'default': ThreadPoolExecutor(1)}
        self.scheduler = BackgroundScheduler(executors=executors)

        # Thread for resetting the resolving process
        self.scheduler.add_job(func=self._find_dns_conflicts_thread,
                               trigger=IntervalTrigger(
                                   seconds=60 * 60 * 12),  # Every 12 hours
                               next_run_time=datetime.now() + timedelta(minutes=1),
                               name='find_dns_conflicts_thread',
                               id='find_dns_conflicts_thread',
                               max_instances=1)
        self.scheduler.start()
        self.scheduler.pause()

    def _find_dns_conflicts_thread(self):
        """ Thread for finding dns conflicts.
        This thread will try to find ip contradiction between different dns servers. If it finds such contradiction,
        The related device will get tagged with 'IP_CONFLICT' tag
        """
        self.logger.info("Find conflicts thread had started")
        with self.resolve_lock:
            ad_adapters = self.get_plugin_by_name('ad_adapter', verify_single=False)

            for ad_adapter in ad_adapters:
                ad_adapter_unique_name = ad_adapter['plugin_unique_name']
                self.logger.info(f"looking for ip conflicts from ad_adapter {ad_adapter_unique_name}")
                hosts = self._get_collection("devices_data",
                                             db_name=ad_adapter_unique_name).find({'RESOLVE_STATUS': 'RESOLVED'},
                                                                                  projection={'_id': True,
                                                                                              'id': True,
                                                                                              'raw.AXON_DNS_ADDR': True,
                                                                                              'raw.AXON_DOMAIN_NAME': True,
                                                                                              'raw.AXON_DC_ADDR': True,
                                                                                              'hostname': True})
                self.logger.info(
                    f"Starting to search for dns conflicts for {hosts.count()} devices from {ad_adapter_unique_name}")

                for host in hosts:
                    try:
                        time_before_resolve = datetime.now()
                        dc_name = host['raw']['AXON_DC_ADDR']
                        dns_name = host['raw']['AXON_DNS_ADDR']
                        domain_name = host['raw']['AXON_DOMAIN_NAME']

                        self.logger.info(f"Inspecting host {host}")

                        self._find_dns_conflicts(ad_adapter_unique_name,
                                                 host['hostname'],
                                                 host['id'],
                                                 {"dns_name": dns_name, "domain_name": domain_name, "dc_name": dc_name})
                    except Exception as e:
                        self.logger.error(f"Error finding conflicts on host{host['hostname']} . Err: {str(e)}")
                    finally:
                        # Waiting at least 50[ms] before each request
                        resolve_time = (datetime.now() - time_before_resolve).microseconds / 1e6  # seconds
                        time_to_sleep = max(0.0, 0.05 - resolve_time)
                        time.sleep(time_to_sleep)

    def _find_dns_conflicts(self, adapter_unique_name, device_name, device_id, client_config, timeout=1):
        """ Function for finding dns resolving conflicts in Active Directory
        :param adapter_unique_name: unique name of the adapter we are working with
        :param device_name: The name of the device we try to find conflicts on
        :param device_id: Device of the device we are checking for conflicts
        :param client_config: Clients config dict. must contain 'dc_name', 'dns_name' and 'domain_name'
        :param timeout: Timeout for the dns query
        """
        full_device_name = device_name

        dc_as_dns_address = client_config["dc_name"]
        dns_server_address = client_config.get("dns_name")

        available_ips = dict()  # Dict is used only to remove duplicates
        # Try default dns server
        try:
            available_ips[query_dns(full_device_name, timeout)] = 'default'
        except NoIpFoundError:
            pass
        # Try dc as dns
        try:
            available_ips[query_dns(full_device_name, timeout, dc_as_dns_address)] = 'dc_as_dns_address'
        except NoIpFoundError:
            pass
        # Try other dns (if provided)
        try:
            if dns_server_address is not None and dns_server_address != dc_as_dns_address:
                available_ips[query_dns(full_device_name, timeout, dns_server_address)] = 'dns_server_address'
        except NoIpFoundError:
            pass

        self.logger.info(f"found ips {available_ips} for device {full_device_name}")

        if len(available_ips) > 1:
            # If we have more than one key in available_ips that means that this device got two different IP's
            # i.e duplicate! we need to tag this device
            self.logger.info(f"Found ip conflict. details: {str(available_ips)}")
            self._tag_device(device_id, tagname="IP_CONFLICT", tagvalue=json.dumps(available_ips),
                             adapter_unique_name=adapter_unique_name)

    @add_rule('find_conflicts', methods=['POST'], should_authenticate=False)
    def check_ip_conflict_now(self):
        jobs = self.scheduler.get_jobs()
        reset_job = next(job for job in jobs if job.name == 'find_dns_conflicts_thread')
        reset_job.modify(next_run_time=datetime.now())
        self.scheduler.wakeup()
        return ""
