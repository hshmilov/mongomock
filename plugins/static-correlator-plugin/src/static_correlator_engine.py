"""
CorrelatorPlugin.py: A Plugin for the devices correlation process
"""
from axonius.correlator_engine_base import CorrelatorEngineBase
from axonius.device import NETWORK_INTERFACES_FIELD, SCANNER_FIELD, IPS_FIELD, MAC_FIELD, OS_FIELD


NORMALIZED_IPS = 'NORMALIZED_IPS'
NORMALIZED_MACS = 'NORMALIZED_MACS'


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


def _compare_ips(adapter_device1, adapter_device2):
    return _is_one_subset_of_the_other(adapter_device1[NORMALIZED_IPS], adapter_device2[NORMALIZED_IPS])


def _compare_macs(adapter_device1, adapter_device2):
    return _is_one_subset_of_the_other(adapter_device1[NORMALIZED_MACS], adapter_device2[NORMALIZED_MACS])


def _compare_hostname(adapter_device1, adapter_device2):
    if adapter_device1['data']['hostname'] == adapter_device2['data']['hostname']:
        return True
    return False


def is_one_a_scanner(adapter_device1, adapter_device2):
    """
    checks if one of the adapters is the result of a scanner device
    :param adapter_device1: an adapter device to check
    :param adapter_device2: an adapter device to check
    :return: True if one of the devices is the result of a scanner device, False otherwise
    """
    if adapter_device1['data'].get(SCANNER_FIELD, False) or adapter_device2['data'].get(SCANNER_FIELD, False):
        return True
    return False


def is_different_plugin(adapter_device1, adapter_device2):
    return adapter_device1['plugin_name'] != adapter_device2['plugin_name']


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
    return adapter_data.get(NETWORK_INTERFACES_FIELD) is not None and \
        len(adapter_data[NETWORK_INTERFACES_FIELD]) > 0 and \
        ((len([x.get(IPS_FIELD) for x in adapter_data[NETWORK_INTERFACES_FIELD]
               if x.get(IPS_FIELD) is not None and len(x.get(IPS_FIELD, [])) > 0]) > 0) or
         (len([x.get(MAC_FIELD) for x in adapter_data[NETWORK_INTERFACES_FIELD]
               if x.get(MAC_FIELD) is not None and len(x.get(MAC_FIELD, [])) > 0]) > 0))


def _normalize_adapter_devices(devices):
    """
    in order to save a lot of time later - we normalize the adapter devices.
        every adapter_device with an ip or mac is given a corresponding set in the root of the adapter_device.
        we upper the hostname of every adapter_device with a hostname
        we upper the os type of every adapter_device with a os type
    :param devices: all of the devices to be correlated
    :return: a normalized list of the adapter_devices
    """
    adapters_to_correlate = []
    for device in devices:
        for adapter_device in device['adapters']:
            adapter_data = adapter_device['data']
            if _has_mac_or_ip(adapter_data):
                ips = set(_extract_all_ips(adapter_data[NETWORK_INTERFACES_FIELD]))
                macs = set(_extract_all_macs(adapter_data[NETWORK_INTERFACES_FIELD]))
                adapter_device[NORMALIZED_IPS] = ips if len(ips) > 0 else None
                adapter_device[NORMALIZED_MACS] = macs if len(macs) > 0 else None
            if adapter_data.get('hostname') is not None:
                adapter_data['hostname'] = adapter_data['hostname'].upper()
            if adapter_data.get(OS_FIELD, None) is not None and adapter_data.get(OS_FIELD, {}).get('type', '') != '':
                adapter_data[OS_FIELD]['type'] = adapter_data[OS_FIELD]['type'].upper()
            adapters_to_correlate.append(adapter_device)
    return adapters_to_correlate


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

    def __init__(self, *args, **kwargs):
        """
        The engine, transmission and steering wheel for correlations
        """
        super().__init__(*args, **kwargs)

    def _correlate_mac_ip_os(self, adapters_to_correlate):
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

        5.  {'Reason': 'They have the same OS, MAC and IPs'} - the reason for the correlation - try to make it as
                descriptive as possible please

        6. 'StaticAnalysis' - the analysis used to discover the correlation
        :param adapters_to_correlate:
        :return:
        """
        filtered_adapters_list = filter(_get_normalized_mac,
                                        filter(_get_normalized_ip,
                                               filter(_get_os_type, adapters_to_correlate)))
        yield from self._correlate(list(filtered_adapters_list),
                                   [_get_os_type],
                                   [_compare_os_type],
                                   [is_different_plugin, _compare_macs, _compare_ips],
                                   {'Reason': 'They have the same OS, MAC and IPs'},
                                   'StaticAnalysis')

    def _correlate_scanner_mac_ip(self, adapters_to_correlate):
        filtered_adapters_list = filter(_get_normalized_mac,
                                        filter(_get_normalized_ip, adapters_to_correlate))
        yield from self._correlate(list(filtered_adapters_list),
                                   [],
                                   [],
                                   [is_different_plugin, _compare_macs, _compare_ips],
                                   {'Reason': 'They have the same MAC and IPs'},
                                   'ScannerAnalysis')

    def _correlate_hostname_ip_os(self, adapters_to_correlate):
        filtered_adapters_list = filter(_get_hostname,
                                        filter(_get_normalized_ip,
                                               filter(_get_os_type, adapters_to_correlate)))
        yield from self._correlate(list(filtered_adapters_list),
                                   [_get_hostname, _get_normalized_ip, _get_os_type],
                                   [_compare_hostname, _compare_os_type],
                                   [is_different_plugin, _compare_ips],
                                   {'Reason': 'They have the same OS, hostname and IPs'},
                                   'StaticAnalysis')

    def _correlate_scanner_hostname_ip(self, adapters_to_correlate):
        filtered_adapters_list = filter(_get_hostname,
                                        filter(_get_normalized_ip, adapters_to_correlate))
        yield from self._correlate(list(filtered_adapters_list),
                                   [_get_hostname],
                                   [_compare_hostname],
                                   [is_different_plugin, is_one_a_scanner, _compare_ips],
                                   {'Reason': 'They have the same hostname and IPs'},
                                   'ScannerAnalysis')

    def _raw_correlate(self, devices):
        """
        Perform static correlations
        :param devices: axonius devices to correlate
        :return: iter(CorrelationResult or WarningResult)
        """

        # since this operation is extremely costly, we normalize the adapter_devices:
        # 1. adding 2 fields to the root - NORMALIZED_IPS and NORMALIZED_MACS to allow easy access to the ips and macs
        #    of all the NICs
        # 2. uppering every field we might sort by - currently hostname and os type
        adapters_to_correlate = _normalize_adapter_devices(devices)

        # let's find devices by, hostname, os, and ip:
        yield from self._correlate_hostname_ip_os(adapters_to_correlate)

        # Now let's find devices by MAC, os, and IP
        yield from self._correlate_mac_ip_os(adapters_to_correlate)

        # Now let's correlate scanner devices
        yield from self._correlate_scanner_mac_ip(adapters_to_correlate)

        yield from self._correlate_scanner_hostname_ip(adapters_to_correlate)

    def _post_process(self, first_name, first_id, second_name, second_id, data, reason) -> bool:
        """
        Virtual by design.
        :param first_name: plugin name of available device
        :param first_id: id of available device
        :param second_name: plugin name of correlated device
        :param second_id: id of correlated device
        :param data: object
        :param reason: given by the engine implementor
        :return: whether to use the association
        """
        if reason == 'StaticAnalysis':
            if second_name == first_name:
                # this means that some logic in the correlator logic is wrong, because
                # such correlations should have reason == "Logic"
                self.logger.error(
                    f"{first_name} correlated to itself, id: '{first_id}' and '{second_id}' via static analysis")
                return False
        return True
