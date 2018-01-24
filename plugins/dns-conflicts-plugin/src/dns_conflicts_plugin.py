
from datetime import timedelta, datetime
import json
import time
import threading

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.adapter_consts import DEVICES_DATA, DNS_RESOLVE_STATUS
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.devices.dns_resolvable import DNSResolveStatus
from axonius.dns_utils import query_dns, NoIpFoundError
from axonius.mixins.activatable import Activatable
from axonius.plugin_base import PluginBase, add_rule


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
        self._check_ip_conflict_now()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resolve_lock = threading.RLock()

        executors = {'default': ThreadPoolExecutor(1)}
        self.scheduler = LoggedBackgroundScheduler(self.logger, executors=executors)

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
                ad_adapter_unique_name = ad_adapter[PLUGIN_UNIQUE_NAME]
                self.logger.info(f"looking for ip conflicts from ad_adapter {ad_adapter_unique_name}")
                hosts = self._get_collection(DEVICES_DATA, db_name=ad_adapter_unique_name).\
                    find({DNS_RESOLVE_STATUS: DNSResolveStatus.Resolved.name},
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
                        self.logger.exception(f"Error finding conflicts on host{host['hostname']} . Err: {str(e)}")
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
        self._check_ip_conflict_now()
        return ""

    def _check_ip_conflict_now(self):
        jobs = self.scheduler.get_jobs()
        reset_job = next(job for job in jobs if job.name == 'find_dns_conflicts_thread')
        reset_job.modify(next_run_time=datetime.now())
        self.scheduler.wakeup()
