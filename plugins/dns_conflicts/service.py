from datetime import datetime
import json
import time
import threading

from axonius.consts.adapter_consts import DEVICES_DATA, DNS_RESOLVE_STATUS
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.devices.dns_resolvable import DNSResolveStatus
from axonius.dns_utils import query_dns, NoIpFoundError
from axonius.mixins.triggerable import Triggerable
from axonius.plugin_base import PluginBase, add_rule, return_error
from axonius.utils.files import get_local_config_file


class DnsConflictsService(PluginBase, Triggerable):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)

        self.resolve_lock = threading.RLock()
        self.trigger_activate_if_needed()

    def _triggered(self, job_name: str, post_json: dict, *args):
        if job_name != 'execute':
            self.logger.error(f"Got bad trigger request for non-existent job: {job_name}")
            return return_error("Got bad trigger request for non-existent job", 400)
        else:
            return self.check_ip_conflict_now()

    def _find_all_dns_conflicts(self):
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
            self.add_label_to_device((adapter_unique_name, device_id), "IP_CONFLICT")
            self.add_data_to_device((adapter_unique_name, device_id), "Ip Conflicts", json.dumps(available_ips))

    @add_rule('find_conflicts', methods=['POST'], should_authenticate=False)
    def check_ip_conflict_now(self):
        self._find_all_dns_conflicts()
        return ""
