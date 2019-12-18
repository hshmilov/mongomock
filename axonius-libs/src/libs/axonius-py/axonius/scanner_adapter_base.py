import logging

from axonius.consts.plugin_subtype import PluginSubtype

logger = logging.getLogger(f'axonius.{__name__}')
"""
ScannerAdapterBase is an abstract class all scanner adapters should inherit from.
See https://axonius.atlassian.net/wiki/spaces/AX/pages/415858710/ScannerAdapter+Design
"""
from axonius.plugin_base import EntityType
import uuid
import copy
from abc import ABC
from typing import Tuple, List, Iterable

from axonius.mixins.feature import Feature

from axonius.adapter_base import AdapterBase
from axonius.consts.adapter_consts import IGNORE_DEVICE

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME, PLUGIN_UNIQUE_NAME, PLUGIN_NAME
from axonius.utils.parsing import pair_comparator, is_different_plugin, parameter_function, normalize_adapter_device, \
    extract_all_macs, get_hostname, macs_do_not_contradict, hostnames_do_not_contradict, os_do_not_contradict, \
    ips_do_not_contradict, NORMALIZED_IPS, remove_duplicates_by_reference, \
    NORMALIZED_MACS, NORMALIZED_HOSTNAME_STRING, not_snow_adapters, not_airwatch_adapters


def newest(devices):
    """
    Return the newest deviceaccording to accurate_for_datetime
    If empty, returns None
    """
    devices = list(devices)
    if not devices:
        return None
    return max(devices, key=lambda device: device['accurate_for_datetime'])


class ScannerCorrelatorBase(object):
    def __init__(self, all_devices, plugin_name, *args, **kwargs):
        """
        Base scanner correlator; base behavior is correlating with hostname
        :param all_devices: all axonius devices from DB
        """
        super().__init__(*args, **kwargs)
        self._plugin_name = plugin_name
        try:
            self._all_devices = list(all_devices)
        except Exception:
            logger.critical(f'Problem in correlation engine scanner', exc_info=True)
            self._all_devices = []
        # not using `normalize_adapter_devices` to not correlate with adapterdata
        self._all_adapter_devices = [normalize_adapter_device(adapter) for adapters in self._all_devices for adapter in
                                     adapters['adapters']]
        self._all_adapter_devices_from_same_plugin = [x for x in self._all_adapter_devices if
                                                      x[PLUGIN_NAME] == self._plugin_name]

        # all adapters indexed by IPs
        self._all_adapters_by_ips = {}
        for adapter in self._all_adapter_devices:
            ips = adapter.get(NORMALIZED_IPS)
            if ips:
                for ip in ips:
                    if ip and ip != '127.0.0.1':
                        self._all_adapters_by_ips.setdefault(ip, []).append(adapter)

        self._all_adapters_by_mac_from_same_plugin = {}
        for adapter in self._all_adapter_devices_from_same_plugin:
            macs = adapter.get(NORMALIZED_MACS)
            if macs:
                for mac in macs:
                    if mac:
                        self._all_adapters_by_mac_from_same_plugin.setdefault(mac, []).append(adapter)

        self._all_adapters_by_hostname_from_same_plugin = {}
        for adapter in self._all_adapter_devices_from_same_plugin:
            hostname = adapter.get(NORMALIZED_HOSTNAME_STRING)
            if hostname:
                self._all_adapters_by_hostname_from_same_plugin.setdefault(hostname, []).append(adapter)

    def find_suitable(self, parsed_device, normalizations: List[parameter_function] = [],
                      predicates: List[pair_comparator] = [], adapter_list: list = None) -> Tuple[str, str]:
        """
        Returns all devices that are compatible with all given predicates
        :param parsed_device: Compare with this device
        :param normalizations: a list of transformations to perform on each device before checking the predicates
        :param predicates: a list of predicates that a pair of devices have to fulfil to be "suitable"
        :param adapter_list: If given, will use this instead of self._all_adapter_devices
        :return: iterator(parsed_devices)
        """
        for normalization in normalizations:
            parsed_device = normalization(parsed_device)

        for device in adapter_list if adapter_list is not None else self._all_adapter_devices:
            for normalization in normalizations:
                device = normalization(device)
            if all(predict(parsed_device, device) for predict in predicates):
                yield device

    def find_suitable_newest(self, *args, **kwargs) -> Tuple[str, str]:
        """
        Returns newest from find_suitable - see find_suitable docs
        :return: parsed_devices
        """
        newest_device = newest(self.find_suitable(*args, **kwargs))
        if not newest_device:
            return None
        return newest_device[PLUGIN_UNIQUE_NAME], newest_device['data']['id']

    def find_suitable_newest_by_ip(self, parsed_device, *args, **kwargs) -> Tuple[str, str]:
        """
        Returns newest from find_suitable - see find_suitable docs
        Also checks that there's overlaps in the IPs
        :return: parsed_devices
        """
        ips = parsed_device.get(NORMALIZED_IPS)
        if not ips:
            return None
        devices_to_search = []
        for ip in ips:
            devices_per_ip = self._all_adapters_by_ips.get(ip)
            if devices_per_ip:
                devices_to_search += devices_per_ip
        devices_to_search = remove_duplicates_by_reference(devices_to_search)
        return self.find_suitable_newest(parsed_device, *args, **kwargs, adapter_list=devices_to_search)

    def find_suitable_no_ip_and_host_contradictions(self, parsed_device, *args, **kwargs) -> Tuple[str, str]:
        devices = list(self.find_suitable(parsed_device, *args, **kwargs))
        if len(devices) > 0:
            device = next(filter(lambda dev: ips_do_not_contradict(dev, parsed_device)
                                 and hostnames_do_not_contradict(dev, parsed_device), devices), None)
        else:
            return None
        return None if device is None else (device[PLUGIN_UNIQUE_NAME], device['data']['id'])

    def _find_correlation_with_self(self, parsed_device) -> Tuple[str, str]:
        """
        virtual by design

        find, if possible, a previous instance of a scanner result that refers
        to the given parsed_device
        :param parsed_device:
        :return: Tuple(UNIQUE_PLUGIN_NAME, id)
        """
        macs = parsed_device.get(NORMALIZED_MACS) or []
        hostname = parsed_device.get(NORMALIZED_HOSTNAME_STRING)

        adapters_with_same_mac = [adapter
                                  for mac in macs
                                  for adapter in
                                  self._all_adapters_by_mac_from_same_plugin.get(mac, [])]

        # Not using the full fledged compare_hostname here:
        # if a device exists in the DB from this scanner, and this scanner has a MAC, it will almost certainly
        # be exactly the same mac, so this heuristic is unnecessary and saves a lot of complication.
        adapters_with_same_hostname = self._all_adapters_by_hostname_from_same_plugin.get(hostname, [])

        adapters_with_same_mac = remove_duplicates_by_reference(adapters_with_same_mac)

        return self.find_suitable_no_ip_and_host_contradictions(parsed_device,
                                                                adapter_list=adapters_with_same_mac) or \
            self.find_suitable_no_ip_and_host_contradictions(parsed_device,
                                                             adapter_list=adapters_with_same_hostname)

    def _find_correlation_with_real_adapter(self, parsed_device) -> Tuple[str, str]:
        """
        virtual by design

        :param parsed_device:
        :return: Tuple(UNIQUE_PLUGIN_NAME, id)
        """
        return self.find_suitable_newest_by_ip(parsed_device=parsed_device,
                                               normalizations=[],
                                               predicates=[is_different_plugin,
                                                           macs_do_not_contradict,
                                                           hostnames_do_not_contradict,
                                                           os_do_not_contradict,
                                                           not_snow_adapters,
                                                           not_airwatch_adapters])

    def find_correlation(self, parsed_device) -> Tuple[str, str]:
        """
        Find a correlation for the given device, assign ID if not available on given device
        :param parsed_device: parsed device
        :return: (plugin_unique_name, id)
        """
        # if a scanner has a hostname or macs this will act as its ID
        my_macs = set(extract_all_macs(parsed_device['data'].get('network_interfaces')))
        hostname = get_hostname(parsed_device)
        # generate a fake id
        if parsed_device['data'].get('id'):
            device_has_id = True
        else:
            device_has_id = False
            parsed_device['data']['id'] = uuid.uuid4().hex
        if (hostname or my_macs or parsed_device['data'].get('name')) and device_has_id:
            return None

        parsed_device_copy = copy.deepcopy(parsed_device)  # Deepcopy to prevent changes on parsed device
        parsed_device_copy = normalize_adapter_device(parsed_device_copy)

        remote_correlation = self._find_correlation_with_real_adapter(parsed_device_copy)
        if remote_correlation:
            # If a remote correlation is found (but a self correction is not)
            # it might be because of an edge case: self correlation is weaker than remote correlation.
            # To handle this case gracefully the axonius device found will be checked to see if it has
            # an adapter device from the current scanner (by PLUGIN_NAME). If that is the case,
            # the ID of the current scanner device will be set to the found device and no correlation will be made.
            plugin_unique_name, adapter_device_id = remote_correlation
            correlation_base_axonius_device = next((axon_device for
                                                    axon_device in self._all_devices
                                                    if
                                                    any(adapter_device[PLUGIN_UNIQUE_NAME] == plugin_unique_name and
                                                        adapter_device['data']['id'] == adapter_device_id for
                                                        adapter_device in axon_device['adapters'])), None)
            newest_device = newest(filter(lambda dev: parsed_device[PLUGIN_NAME] == dev[PLUGIN_NAME],
                                          correlation_base_axonius_device['adapters']))
            if newest_device is not None:
                logger.debug(f"Found remote correlation but not self correlation - {newest_device['data']['id']}")
                # updating a current adapter correlation so no new one will be created - basically a different kind
                # of self correlation
                parsed_device['data']['id'] = newest_device['data']['id']
                return None
            if not my_macs and not hostname:
                # If we have no mac or hostname we should not use the original id, due to complex scenarios
                # that have been seen by ofri, in which wrong correlations can occur. Thus we generate a new id.
                parsed_device['data']['id'] = uuid.uuid4().hex
            return remote_correlation

        # the device has only a fake ID and no correlations - ignore it
        return None if my_macs or hostname or device_has_id else IGNORE_DEVICE


class ScannerAdapterBase(AdapterBase, Feature, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __correlate_devices(self, parsed_data) -> Iterable:
        """
        Uses the DB and the `_get_scanner_correlator` logic to correlate the devices
        """
        devices = self.devices_db.find(projection={
            'adapters.accurate_for_datetime': 1,
            f'adapters.{PLUGIN_NAME}': 1,
            f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
            'adapters.data.id': 1,
            'adapters.data.network_interfaces.ips': 1,
        })
        scanner = self._get_scanner_correlator(devices, self.plugin_name)
        device_count = 0

        for device in parsed_data:
            device['correlates'] = scanner.find_correlation({"data": device,
                                                             PLUGIN_UNIQUE_NAME: self.plugin_unique_name,
                                                             PLUGIN_NAME: self.plugin_name,
                                                             'plugin_type': self.plugin_type})
            yield device
            device_count += 1
            if device_count % 1000 == 0:
                logger.info(f"Got {device_count} devices.")

    def _try_query_data_by_client(self, client_name, entity_type: EntityType, use_cache=True):
        raw_data, parsed_data = super()._try_query_data_by_client(client_name, entity_type)
        if entity_type == EntityType.Devices:
            return raw_data, self.__correlate_devices(parsed_data)
        return raw_data, parsed_data

    @property
    def plugin_subtype(self) -> PluginSubtype:
        return PluginSubtype.ScannerAdapter

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["ScannerAdapter"]

    @property
    def _get_scanner_correlator(self):
        return ScannerCorrelatorBase
