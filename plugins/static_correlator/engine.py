import logging
from itertools import combinations

logger = logging.getLogger(f"axonius.{__name__}")
from axonius.correlator_engine_base import CorrelatorEngineBase
from axonius.utils.parsing import get_hostname, compare_hostname, is_from_ad, \
    ips_do_not_contradict, get_normalized_ip, compare_device_normalized_hostname, \
    normalize_adapter_devices, get_serial, NORMALIZED_MACS, compare_macs, hostnames_do_not_contradict
from axonius.correlator_base import has_mac, has_hostname, has_serial, CorrelationReason
from axonius.blacklists import JUNIPER_NON_UNIQUE_MACS


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
        return [has_hostname, has_mac, has_serial]

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

        5.  {'Reason': 'They have the same MAC and IPs don\'t contradict'} - the reason for the correlation - try to make it as
                descriptive as possible please

        6. CorrelationReason.StaticAnalysis - the analysis used to discover the correlation
        """
        logger.info("Starting to correlate on MAC")
        mac_indexed = {}
        for adapter in adapters_to_correlate:
            macs = adapter.get(NORMALIZED_MACS)
            if macs:
                for mac in macs:
                    if mac and mac != '000000000000':
                        mac_indexed.setdefault(mac, []).append(adapter)

        # find contradicting hostnames with the same mac to eliminate macs. Also using predefined blacklist of known macs.
        mac_blacklist = set()
        mac_blacklist = mac_blacklist.union(JUNIPER_NON_UNIQUE_MACS)
        for mac, matches in mac_indexed.items():
            for x, y in combinations(matches, 2):
                if not hostnames_do_not_contradict(x, y):
                    mac_blacklist.add(mac)
                    break

        for mac in mac_blacklist:
            if mac in mac_indexed:
                del mac_indexed[mac]

        for matches in mac_indexed.values():
            if len(matches) >= 2:
                yield from self._bucket_correlate(matches,
                                                  [],
                                                  [],
                                                  [],
                                                  [compare_macs],
                                                  {'Reason': 'They have the same MAC'},
                                                  CorrelationReason.StaticAnalysis)

    def _correlate_hostname_ip(self, adapters_to_correlate):
        logger.info("Starting to correlate on Hostname-IP")
        filtered_adapters_list = filter(get_hostname,
                                        filter(get_normalized_ip, adapters_to_correlate))
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_hostname],
                                      [compare_device_normalized_hostname],
                                      [],
                                      [ips_do_not_contradict],
                                      {'Reason': 'They have the same hostname and IPs'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial(self, adapters_to_correlate):
        logger.info("Starting to correlate on Serial")
        filtered_adapters_list = filter(get_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_serial],
                                      [lambda a, b: a['data']['device_serial'].upper() == b['data'][
                                          'device_serial'].upper()],
                                      [],
                                      [hostnames_do_not_contradict],
                                      {'Reason': 'They have the same serial'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_with_ad(self, adapters_to_correlate):
        """
        AD correlation is a little more loose - we allow correlation based on hostname alone.
        In order to lower the false positive rate we don't use the normalized hostname but rather the full one
        """
        logger.info("Starting to correlate on Hostname-AD")
        filtered_adapters_list = filter(get_hostname, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_hostname],
                                      [compare_hostname],
                                      [is_from_ad],
                                      [],
                                      {'Reason': 'They have the same hostname and one is AD'},
                                      CorrelationReason.StaticAnalysis)

    def _raw_correlate(self, devices):
        # WARNING WARNING WARNING
        # Adding or changing any type of correlation here might require changing the appropriate logic
        # at static_correlator/service

        # since this operation is extremely costly, we normalize the adapter_devices:
        # 1. adding 2 fields to the root - NORMALIZED_IPS and NORMALIZED_MACS to allow easy access to the ips and macs
        #    of all the NICs
        # 2. uppering every field we might sort by - currently hostname and os type
        # 3. splitting the hostname into a list in order to be able to compare hostnames without depending on the domain
        adapters_to_correlate = list(normalize_adapter_devices(devices))

        # let's find devices by, hostname, and ip:
        yield from self._correlate_hostname_ip(adapters_to_correlate)

        # Now let's find devices by MAC, and IPs don't contradict (we allow empty)
        yield from self._correlate_mac(adapters_to_correlate)
        # for ad specifically we added the option to correlate on hostname basis alone (dns name with the domain)
        yield from self._correlate_with_ad(adapters_to_correlate)

        # Find adapters with the same serial
        yield from self._correlate_serial(adapters_to_correlate)

    def _post_process(self, first_name, first_id, second_name, second_id, data, reason) -> bool:
        if reason == CorrelationReason.StaticAnalysis:
            if second_name == first_name:
                # this means that some logic in the correlator logic is wrong, because
                # such correlations should have reason == "Logic"
                logger.error(
                    f"{first_name} correlated to itself, id: '{first_id}' and '{second_id}' via static analysis")
                return False
        return True
