from axonius.correlator_engine_base import CorrelatorEngineBase
from axonius.correlator_base import has_mac, has_hostname
from axonius.parsing_utils import normalize_hostname, compare_normalized_hostnames
from axonius.device import NETWORK_INTERFACES_FIELD, SCANNER_FIELD, IPS_FIELD, MAC_FIELD, OS_FIELD


# NORMALIZED_IPS/MACS fields will hold the set of IPs and MACs an adapter devices has extracted.
# Without it, in order to compare IPs and MACs we would have to go through the list of network interfaces and extract
# them each time.
NORMALIZED_IPS = 'normalized_ips'
NORMALIZED_MACS = 'normalized_macs'
# Unfortunately there's no normalized way to return a hostname - currently many adapters return hostname.domain.
# However in non-windows systems, the hostname itself can contain "." which means there's no way to tell which part is
# the hostname when splitting.
# The problem starts as some adapters yield a hostname with a default domain added to it even when a domain exists, and
# some don't return a domain at all.
# In order to ignore that and allow proper hostname comparison we want to remove the default domains.
# Currently (28/01/2018) this means removing LOCAL and WORKGROUP.
# Also we want to split the hostname on "." and make sure one split list is the beginning of the other.
NORMALIZED_HOSTNAME = 'normalized_hostname'
DEFAULT_DOMAIN_EXTENSIONS = ['.LOCAL', '.WORKGROUP']


def _extract_all_ips(network_ifs):
    """
    :param network_ifs: the network_ifs as appear in the axonius device scheme
    :return: yields every ip in the network interfaces
    """
    if network_ifs is None:
        return
    for network_if in network_ifs:
        for ip in network_if.get(IPS_FIELD) or []:
            yield ip


def _extract_all_macs(network_ifs):
    """
    :param network_ifs: the network_ifs as appear in the axonius device scheme
    :return: yields every mac in the network interfaces
    """
    if network_ifs is None:
        return
    for network_if in network_ifs:
        current_mac = network_if.get(MAC_FIELD, '')
        if current_mac != '' and current_mac is not None:
            yield current_mac.upper().replace('-', '').replace(':', '')


def _is_one_subset_of_the_other(first_set, second_set):
    """
    :param first_set: a set
    :param second_set: a set
    :return: True if one of the sets is a subset of the other
    """
    if len(first_set) == 0 or len(second_set) == 0:
        return False
    return first_set.issubset(second_set) or second_set.issubset(first_set)


def _compare_os_type(adapter_device1, adapter_device2):
    if adapter_device1['data'][OS_FIELD]['type'] == adapter_device2['data'][OS_FIELD]['type']:
        return True
    return False


def _ips_do_not_contradict(adapter_device1, adapter_device2):
    device1_ips = adapter_device1.get(NORMALIZED_IPS)
    device2_ips = adapter_device2.get(NORMALIZED_IPS)
    return not device1_ips or not device2_ips or _is_one_subset_of_the_other(device1_ips, device2_ips)


def _compare_macs(adapter_device1, adapter_device2):
    return _is_one_subset_of_the_other(adapter_device1[NORMALIZED_MACS], adapter_device2[NORMALIZED_MACS])


def _compare_hostname(adapter_device1, adapter_device2):
    if adapter_device1['data']['hostname'] == adapter_device2['data']['hostname']:
        return True
    return False


def _compare_normalized_hostname(adapter_device1, adapter_device2) -> bool:
    """
    See compare_normalized_hostnames docs
    :param adapter_device1: first device
    :param adapter_device2: second device
    :return:
    """
    return compare_normalized_hostnames(adapter_device1[NORMALIZED_HOSTNAME], adapter_device2[NORMALIZED_HOSTNAME])


def is_a_scanner(adapter_device):
    """
    checks if the adapters is the result of a scanner device
    :param adapter_device: an adapter device to check
    """
    if adapter_device['data'].get(SCANNER_FIELD, False):
        return True
    return False


def is_different_plugin(adapter_device1, adapter_device2):
    return adapter_device1['plugin_name'] != adapter_device2['plugin_name']


def is_from_ad(adapter_device):
    return adapter_device['plugin_name'] == 'ad_adapter'


def _get_normalized_mac(adapter_device):
    return adapter_device.get(NORMALIZED_MACS)


def _get_normalized_ip(adapter_device):
    return adapter_device.get(NORMALIZED_IPS)


def _get_os_type(adapter_device):
    return (adapter_device['data'].get(OS_FIELD) or {}).get('type')


def _get_hostname(adapter_device):
    return adapter_device['data'].get('hostname')


def _has_mac_or_ip(adapter_data):
    """
    checks if one of the network interfaces in adapter data has a MAC or ip
    :param adapter_data: the data of the adapter to test
    :return: True if there's at least one MAC or IP
    """
    return any(x.get(IPS_FIELD) or x.get(MAC_FIELD) for x in (adapter_data.get(NETWORK_INTERFACES_FIELD) or []))


def _normalize_adapter_devices(devices):
    """
    in order to save a lot of time later - we normalize the adapter devices.
        every adapter_device with an ip or mac is given a corresponding set in the root of the adapter_device.
        we upper the hostname of every adapter_device with a hostname
        we upper the os type of every adapter_device with a os type
    :param devices: all of the devices to be correlated
    :return: a normalized list of the adapter_devices
    """
    for device in devices:
        for adapter_device in device['adapters']:
            adapter_data = adapter_device['data']
            if _has_mac_or_ip(adapter_data):
                ips = set(_extract_all_ips(adapter_data[NETWORK_INTERFACES_FIELD]))
                macs = set(_extract_all_macs(adapter_data[NETWORK_INTERFACES_FIELD]))
                adapter_device[NORMALIZED_IPS] = ips if len(ips) > 0 else None
                adapter_device[NORMALIZED_MACS] = macs if len(macs) > 0 else None
            # Save the normalized hostname so we can later easily compare.
            # See further doc near definition of NORMALIZED_HOSTNAME.
            adapter_device[NORMALIZED_HOSTNAME] = normalize_hostname(adapter_device['data'])
            if adapter_data.get(OS_FIELD) is not None and adapter_data.get(OS_FIELD, {}).get('type'):
                adapter_data[OS_FIELD]['type'] = adapter_data[OS_FIELD]['type'].upper()
            yield adapter_device


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

    def _prefilter_device(self, devices):
        # this is the least of all acceptable preconditions for correlatable devices - if none is satisfied there's no
        # way to correlate the devices and so it won't be added to adapters_to_correlate
        self.correlation_preconditions = [has_hostname, has_mac]
        return super()._prefilter_device(devices)

    def _correlate_mac_ip_no_contradiction(self, adapters_to_correlate):
        """
        To write a correlator rule we do a few things:
        1.  list(filtered_adapters_list) -
                filter in only adapters we can actually later correlate - for example here we can only correlate
                adapters with mac, ip and os - having already normalized them we can use the normalized field for
                efficiency

        2.  [_get_os_type] - since the first comparison is pairwise we want to sort according to something we can decide
                between to adapters whether they share it or not just using sorting - i.e. not lists or sets. The great
                thing here is every parameter we can use would decrease the number of permutations by a huge factor.

        3.  [_compare_os_type] - this is the respective list of comparators for the sorting lambdas, in this case since
                the only way to sort was os type (as mac and ip are both sets) we only compare the os before inserting
                into the bucket

        4.  [is_different_plugin, _compare_macs, _compare_ips] - the list of comparators to use on a pair from the
                bucket - a pair that has made it through this list is considered a correlation so choose wisely!

        5.  {'Reason': 'They have the same MAC and IPs don\'t contradict'} - the reason for the correlation - try to make it as
                descriptive as possible please

        6. 'StaticAnalysis' - the analysis used to discover the correlation
        """
        self.logger.info("Starting to correlate on MAC-IP")
        filtered_adapters_list = filter(_get_normalized_mac, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [],
                                      [],
                                      [],
                                      [is_different_plugin, _compare_macs, _ips_do_not_contradict],
                                      {'Reason': 'They have the same MAC and IPs don\'t contradict'},
                                      'StaticAnalysis')

    def _correlate_hostname_ip(self, adapters_to_correlate):
        self.logger.info("Starting to correlate on Hostname-IP")
        filtered_adapters_list = filter(_get_hostname,
                                        filter(_get_normalized_ip, adapters_to_correlate))
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [_get_hostname],
                                      [_compare_normalized_hostname],
                                      [],
                                      [is_different_plugin, _ips_do_not_contradict],
                                      {'Reason': 'They have the same hostname and IPs'},
                                      'StaticAnalysis')

    def _correlate_with_ad(self, adapters_to_correlate):
        """
        AD correlation is a little more loose - we allow correlation based on hostname alone.
        In order to lower the false positive rate we don't use the normalized hostname but rather the full one
        """
        self.logger.info("Starting to correlate on Hostname-AD")
        filtered_adapters_list = filter(_get_hostname, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [_get_hostname],
                                      [_compare_hostname],
                                      [is_from_ad],
                                      [],
                                      {'Reason': 'They have the same hostname and one is AD'},
                                      'ScannerAnalysis')

    def _raw_correlate(self, devices):
        # since this operation is extremely costly, we normalize the adapter_devices:
        # 1. adding 2 fields to the root - NORMALIZED_IPS and NORMALIZED_MACS to allow easy access to the ips and macs
        #    of all the NICs
        # 2. uppering every field we might sort by - currently hostname and os type
        # 3. splitting the hostname into a list in order to be able to compare hostnames without depending on the domain
        adapters_to_correlate = list(_normalize_adapter_devices(devices))

        # let's find devices by, hostname, and ip:
        yield from self._correlate_hostname_ip(adapters_to_correlate)

        # Now let's find devices by MAC, and IPs don't contradict (we allow empty)
        yield from self._correlate_mac_ip_no_contradiction(adapters_to_correlate)
        # for ad specifically we added the option to correlate on hostname basis alone (dns name with the domain)
        yield from self._correlate_with_ad(adapters_to_correlate)

    def _post_process(self, first_name, first_id, second_name, second_id, data, reason) -> bool:
        if reason == 'StaticAnalysis':
            if second_name == first_name:
                # this means that some logic in the correlator logic is wrong, because
                # such correlations should have reason == "Logic"
                self.logger.error(
                    f"{first_name} correlated to itself, id: '{first_id}' and '{second_id}' via static analysis")
                return False
        return True
