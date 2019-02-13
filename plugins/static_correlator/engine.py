import logging
from itertools import combinations

from axonius.blacklists import ALL_BLACKLIST
from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.correlator_base import (has_ad_or_azure_name, has_cloud_id,
                                     has_hostname, has_last_used_users,
                                     has_mac, has_name, has_serial)
from axonius.correlator_engine_base import (CorrelatorEngineBase, CorrelationMarker)
from axonius.types.correlation import CorrelationReason
from axonius.utils.parsing import (NORMALIZED_MACS,
                                   asset_hostnames_do_not_contradict,
                                   compare_ad_name_or_azure_display_name,
                                   compare_asset_hosts, compare_asset_name,
                                   compare_bios_serial_serial, compare_clouds,
                                   compare_device_normalized_hostname,
                                   compare_domain, compare_hostname,
                                   compare_id, compare_last_used_users,
                                   get_ad_name_or_azure_display_name,
                                   get_asset_name, get_asset_or_host,
                                   get_bios_serial_or_serial, get_cloud_data,
                                   get_domain, get_hostname, get_id,
                                   get_last_used_users,
                                   get_normalized_hostname_str,
                                   get_normalized_ip, get_serial,
                                   hostnames_do_not_contradict,
                                   ips_do_not_contradict_or_mac_intersection,
                                   is_azuread_or_ad_and_have_name,
                                   is_only_host_adapter_not_localhost,
                                   is_different_plugin, is_from_ad_or_jamf,
                                   is_from_juniper_and_asset_name,
                                   is_from_no_mac_adapters_with_empty_mac,
                                   is_junos_space_device,
                                   is_old_device, is_sccm_or_ad,
                                   is_splunk_vpn, normalize_adapter_devices,
                                   serials_do_not_contradict, compare_macs_or_one_is_jamf,
                                   not_aruba_adapters, cloud_id_do_not_contradict,
                                   not_contain_generic_jamf_names,
                                   get_serial_no_s, compare_serial_no_s,
                                   get_bios_serial_or_serial_no_s, compare_bios_serial_serial_no_s)

logger = logging.getLogger(f'axonius.{__name__}')


class StaticCorrelatorEngine(CorrelatorEngineBase):
    """
    For efficiency reasons this engine assumes a different structure (let's refer to it as compact structure)
    of axonius devices.
    Each adapter device should have
    {
        plugin_name: "",
        plugin_unique_name: "",
        data: {
            id: "",
            OS: {
                type: "",
                whatever...
            },
            hostname: "",
            network_interfaces: [
                {
                    IP: ["127.0.0.1", ...],
                    whatever...
                },
                ...
            ]
        }
    }
    """
    @property
    def _correlation_preconditions(self):
        # this is the least of all acceptable preconditions for correlatable devices - if none is satisfied there's no
        # way to correlate the devices and so it won't be added to adapters_to_correlate
        return [has_hostname, has_name, has_mac, has_serial, has_cloud_id, has_ad_or_azure_name, has_last_used_users]

    def _correlate_mac(self, adapters_to_correlate):
        """
        To write a correlator rule we do a few things:
        1.  list(filtered_adapters_list) -
                filter in only adapters we can actually later correlate - for example here we can only correlate
                adapters with mac, ip and os - having already normalized them we can use the normalized field for
                efficiency

        2.  [get_os_type] - since the first comparison is pairwise we want to sort according to something we can decide
                between to adapters whether they share it or not just using sorting - i.e. not lists or sets. The great
                thing here is every parameter we can use would decrease the number of permutations by a huge factor.

        3.  [compare_os_type] - this is the respective list of comparators for the sorting lambdas, in this case since
                the only way to sort was os type (as mac and ip are both sets) we only compare the os before inserting
                into the bucket

        4.  [is_different_plugin, compare_macs, _compare_ips] - the list of comparators to use on a pair from the
                bucket - a pair that has made it through this list is considered a correlation so choose wisely!

        5.  {'Reason': 'They have the same MAC and IPs don\'t contradict'} - the reason for the correlation -
                try to make it as descriptive as possible please

        6. CorrelationReason.StaticAnalysis - the analysis used to discover the correlation
        """

        logger.info('Starting to correlate on MAC')
        mac_indexed = {}
        for adapter in adapters_to_correlate:
            # Don't add to the MAC comparisons devices that haven't seen for more than 30 days
            if is_old_device(adapter, number_of_days=5):
                continue
            macs = adapter.get(NORMALIZED_MACS)
            if macs:
                for mac in macs:
                    if mac and mac != '000000000000':
                        mac_indexed.setdefault(mac, []).append(adapter)

        # find contradicting hostnames with the same mac to eliminate macs.
        # Also using predefined blacklist of known macs.
        mac_blacklist = set()
        mac_blacklist = mac_blacklist.union(ALL_BLACKLIST)
        for mac, matches in mac_indexed.items():
            for x, y in combinations(matches, 2):
                if (not hostnames_do_not_contradict(x, y)) and (not is_different_plugin(x, y)
                                                                or (get_domain(x) and get_domain(y)
                                                                    and compare_domain(x, y))):
                    mac_blacklist.add(mac)
                    break

        for mac in mac_blacklist:
            if mac in mac_indexed:
                del mac_indexed[mac]

        for matches in mac_indexed.values():
            if 30 >= len(matches) >= 2:
                yield from self._bucket_correlate(matches,
                                                  [],
                                                  [],
                                                  [],
                                                  [compare_macs_or_one_is_jamf],
                                                  {'Reason': 'They have the same MAC'},
                                                  CorrelationReason.StaticAnalysis)

    def _correlate_hostname_ip(self, adapters_to_correlate):
        logger.info('Starting to correlate on Hostname-IP')
        filtered_adapters_list = filter(get_normalized_hostname_str,
                                        filter(get_normalized_ip, adapters_to_correlate))
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      [],
                                      [ips_do_not_contradict_or_mac_intersection,
                                       not_aruba_adapters,
                                       cloud_id_do_not_contradict],
                                      {'Reason': 'They have the same hostname and IPs'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_hostname_user(self, adapters_to_correlate):
        logger.info('Starting to correlate on Hostname-LastUsedUser')
        filtered_adapters_list = filter(get_normalized_hostname_str,
                                        filter(get_last_used_users, adapters_to_correlate))
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      [],
                                      [compare_last_used_users,
                                       not_aruba_adapters,
                                       serials_do_not_contradict],
                                      {'Reason': 'They have the same hostname and LastUsedUser'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_hostname_domain(self, adapters_to_correlate):
        logger.info('Starting to correlate on Hostname-Domain')
        filtered_adapters_list = filter(get_normalized_hostname_str, filter(get_domain, adapters_to_correlate))
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      [],
                                      [compare_domain,
                                       not_aruba_adapters,
                                       serials_do_not_contradict],
                                      {'Reason': 'They have the same hostname and domain'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_hostname_only_host_adapter(self, adapters_to_correlate):
        logger.info('Starting to correlate on Hostname-DeepSecurity')
        filtered_adapters_list = filter(get_normalized_hostname_str, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      [is_only_host_adapter_not_localhost],
                                      [not_aruba_adapters],
                                      {'Reason': 'They have the same hostname and one is DeepSecurity'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial(self, adapters_to_correlate):
        logger.info('Starting to correlate on Serial')
        filtered_adapters_list = filter(get_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_serial],
                                      [lambda a, b: a['data']['device_serial'].upper() == b['data'][
                                          'device_serial'].upper()],
                                      [],
                                      [asset_hostnames_do_not_contradict],
                                      {'Reason': 'They have the same serial'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial_no_s(self, adapters_to_correlate):
        logger.info('Starting to correlate on Serial no s')
        filtered_adapters_list = filter(get_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_serial_no_s],
                                      [compare_serial_no_s],
                                      [],
                                      [asset_hostnames_do_not_contradict],
                                      {'Reason': 'They have the same serial even with S at the beginning'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_cloud_instances(self, adapters_to_correlate):
        logger.info('Starting to correlate on Cloud Instances')
        filtered_adapters_list = filter(get_cloud_data, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_cloud_data],
                                      [compare_clouds],
                                      [],
                                      [],
                                      {'Reason': 'They are the same cloud instance'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial_with_bios_serial(self, adapters_to_correlate):
        logger.info('Starting to correlate on Bios Serial')
        filtered_adapters_list = filter(get_bios_serial_or_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_bios_serial_or_serial],
                                      [compare_bios_serial_serial],
                                      [],
                                      [hostnames_do_not_contradict],
                                      {'Reason': 'Bios serial or serials are equal'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial_with_bios_serial_no_s(self, adapters_to_correlate):
        logger.info('Starting to correlate on Bios Serial No S')
        filtered_adapters_list = filter(get_bios_serial_or_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_bios_serial_or_serial_no_s],
                                      [compare_bios_serial_serial_no_s],
                                      [],
                                      [hostnames_do_not_contradict],
                                      {'Reason': 'Bios serial or serials are equal with no S'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_with_ad(self, adapters_to_correlate):
        """
        AD correlation is a little more loose - we allow correlation based on hostname alone.
        In order to lower the false positive rate we don't use the normalized hostname but rather the full one
        """
        logger.info('Starting to correlate on Hostname-AD-JAMF')
        filtered_adapters_list = filter(get_hostname, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_hostname],
                                      [compare_hostname],
                                      [is_from_ad_or_jamf],
                                      [not_aruba_adapters,
                                       serials_do_not_contradict,
                                       not_contain_generic_jamf_names],
                                      {'Reason': 'They have the same hostname and one is AD'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_with_no_mac_adapters(self, adapters_to_correlate):
        """
        EPO (and more adaptrers) correlation is a little more loose - we allow correlation based on hostname alone,
        but only where theres is no MAC.
        In order to lower the false positive rate we don't use the normalized hostname but rather the full one
        """
        logger.info('Starting to correlate on Hostname-No-Mac-ADAPTERS')
        filtered_adapters_list = filter(get_hostname, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_hostname],
                                      [compare_hostname],
                                      [is_from_no_mac_adapters_with_empty_mac],
                                      [not_aruba_adapters],
                                      {'Reason': 'They have the same hostname and one is No MACs Adapters with no MAC'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_with_juniper(self, adapters_to_correlate):
        """
        juniper correlation is a little more loose - we allow correlation based on asset name alone,
        """
        logger.info('Starting to correlate on asset-name juniper')
        filtered_adapters_list = filter(is_from_juniper_and_asset_name, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_name],
                                      [compare_asset_name],
                                      [is_junos_space_device],
                                      [],
                                      {'Reason': 'Juniper devices with same asset name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_ad_sccm_id(self, adapters_to_correlate):
        """
        We want to get all the devices with hostname (to reduce amount),
         then check if one adapter is SCCM and one is AD and to compare their ID
        """
        logger.info('Starting to correlate on SCCM-AD')
        filtered_adapters_list = filter(is_sccm_or_ad, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_id],
                                      [compare_id],
                                      [],
                                      [],
                                      {'Reason': 'They have the same ID and one is AD and the second is SCCM'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_ad_azure_ad(self, adapters_to_correlate):
        """
        Correlate Azure AD and AD
        """
        logger.info('Starting to correlate on AD-AzureAD')
        filtered_adapters_list = filter(is_azuread_or_ad_and_have_name, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_ad_name_or_azure_display_name],
                                      [compare_ad_name_or_azure_display_name],
                                      [],
                                      [],
                                      {'Reason': 'They have the same display name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_asset_host(self, adapters_to_correlate):
        """
        Correlating by asset first + IP
        :param adapters_to_correlate:
        :return:
        """
        logger.info('Starting to correlate on Asset-Host')
        filtered_adapters_list = filter(get_asset_or_host, filter(get_normalized_ip, adapters_to_correlate))
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_or_host],
                                      [compare_asset_hosts],
                                      [get_asset_name],
                                      [ips_do_not_contradict_or_mac_intersection,
                                       not_aruba_adapters],
                                      {'Reason': 'They have the same Asset name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_splunk_vpn_hostname(self, adapters_to_correlate):
        logger.info('Starting to correlate on Splunk VPN')
        filtered_adapters_list = filter(is_splunk_vpn, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      [],
                                      [],
                                      {'Reason': 'They have the same Normalized hostname and both are Splunk VPN'},
                                      CorrelationReason.StaticAnalysis)

    def _raw_correlate(self, entities):
        # WARNING WARNING WARNING
        # Adding or changing any type of correlation here might require changing the appropriate logic
        # at static_correlator/service

        # since this operation is extremely costly, we normalize the adapter_devices:
        # 1. adding 2 fields to the root - NORMALIZED_IPS and NORMALIZED_MACS to allow easy access to the ips and macs
        #    of all the NICs
        # 2. uppering every field we might sort by - currently hostname and os type
        # 3. splitting the hostname into a list in order to be able to compare hostnames without depending on the domain
        adapters_to_correlate = list(normalize_adapter_devices(entities))

        # let's find devices by, hostname, and ip:
        yield from self._correlate_hostname_ip(adapters_to_correlate)

        # for ad specifically we added the option to correlate on hostname basis alone (dns name with the domain)
        yield from self._correlate_with_ad(adapters_to_correlate)

        # Find adapters that share the same cloud type and cloud id
        yield from self._correlate_cloud_instances(adapters_to_correlate)

        # Find SCCM or Ad adapters with the same ID
        yield from self._correlate_ad_sccm_id(adapters_to_correlate)

        # Find azure ad and ad with the same display name
        yield from self._correlate_ad_azure_ad(adapters_to_correlate)

        # EPO devices on VPN netwrok will almost conflict on IP+MAC with other Agents.
        # If no mac on EPO allow correlation by full host name
        yield from self._correlate_with_no_mac_adapters(adapters_to_correlate)

        # juniper correlation is a little more loose - we allow correlation based on asset name alone,
        yield from self._correlate_with_juniper(adapters_to_correlate)

        yield from self._correlate_hostname_domain(adapters_to_correlate)

        yield from self._correlate_hostname_user(adapters_to_correlate)

        yield from self._correlate_asset_host(adapters_to_correlate)

        yield from self._correlate_hostname_only_host_adapter(adapters_to_correlate)

        yield from self._correlate_splunk_vpn_hostname(adapters_to_correlate)

        yield from self._correlate_serial(adapters_to_correlate)

        yield from self._correlate_serial_with_bios_serial(adapters_to_correlate)
        yield from self._correlate_serial_with_bios_serial_no_s(adapters_to_correlate)
        yield from self._correlate_serial_no_s(adapters_to_correlate)
        # Find adapters with the same serial
        # Now let's find devices by MAC, and IPs don't contradict (we allow empty)

        # Correlating mac must happen after all the other correlations are DONE.
        # the actual linking is happend in _process_correlation_result in other thread,
        # so in order to solve the race condition we yield marker here and
        # wait for all correlation to end until the marker in _map_correlation
        yield CorrelationMarker()

        yield from self._correlate_mac(adapters_to_correlate)

    @staticmethod
    def _post_process(first_name, first_id, second_name, second_id, data, reason) -> bool:
        if reason == CorrelationReason.StaticAnalysis:
            if second_name == first_name:
                # this means that some logic in the correlator logic is wrong, because
                # such correlations should have reason == "Logic"
                logger.error(
                    f'{first_name} correlated to itself, id: \'{first_id}\' and \'{second_id}\' via static analysis')
                return False
        return True

    @staticmethod
    def _bigger_picture_decision(first_axonius_device, second_axonius_device,
                                 first_adapter_device, second_adapter_device) -> bool:
        # Don't correlate devices that have AD in them but are not correlated according to AD
        # AX-2107
        ad_in_first = any(x[PLUGIN_NAME] == 'active_directory' for x in first_axonius_device['adapters'])
        ad_in_second = any(x[PLUGIN_NAME] == 'active_directory' for x in second_axonius_device['adapters'])
        if ad_in_first and ad_in_second:
            if first_adapter_device[PLUGIN_NAME] != 'active_directory' or \
                    second_adapter_device[PLUGIN_NAME] != 'active_directory':
                return False

        return True
