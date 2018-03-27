"""
ScannerAdapterBase is an abstract class all scanner adapters should inherit from.
See https://axonius.atlassian.net/wiki/spaces/AX/pages/415858710/ScannerAdapter+Design
"""
import uuid
from abc import ABC
from typing import Tuple, List

from axonius.mixins.feature import Feature

from axonius.adapter_base import AdapterBase
from axonius.consts.adapter_consts import IGNORE_DEVICE, SCANNER_ADAPTER_PLUGIN_SUBTYPE, ADAPTER_PLUGIN_TYPE

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME, PLUGIN_UNIQUE_NAME, PLUGIN_NAME
from axonius.parsing_utils import pair_comparator, is_different_plugin, parameter_function, normalize_adapter_device, \
    extract_all_macs, get_hostname, compare_ips, macs_do_not_contradict, hostnames_do_not_contradict, \
    inverse_function, or_function, compare_macs, compare_device_normalized_hostname, ips_do_not_contradict


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
    def __init__(self, logger, all_devices, *args, **kwargs):
        """
        Base scanner correlator; base behavior is correlating with hostname
        :param all_devices: all axonius devices from DB
        """
        super().__init__(*args, **kwargs)
        self.logger = logger
        self._all_devices = list(all_devices)
        self._all_adapter_devices = [adapter for adapters in self._all_devices for adapter in adapters['adapters']]

    def find_suitable(self, parsed_device, normalizations: List[parameter_function],
                      predicates: List[pair_comparator]) -> Tuple[str, str]:
        """
        Returns all devices that are compatible with all given predicates
        :return: iterator(parsed_devices)
        """
        for normalization in normalizations:
            parsed_device = normalization(parsed_device)

        for device in self._all_adapter_devices:
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

    def find_suitable_no_ip_contrdictions(self, parsed_device, *args, **kwargs) -> Tuple[str, str]:
        devices = list(self.find_suitable(parsed_device, *args, **kwargs))
        if len(devices) > 1:
            device = next(filter(lambda dev: ips_do_not_contradict(dev, parsed_device), devices), None)
        elif len(devices) == 0:
            return None
        else:
            device = devices[0]
        return None if device is None else (device[PLUGIN_UNIQUE_NAME], device['data']['id'])

    def _find_correlation_with_self(self, parsed_device) -> Tuple[str, str]:
        """
        virtual by design

        find, if possible, a previous instance of a scanner result that refers
        to the given parsed_device
        :param parsed_device:
        :return: Tuple(UNIQUE_PLUGIN_NAME, id)
        """
        return self.find_suitable_no_ip_contrdictions(parsed_device,
                                                      normalizations=[normalize_adapter_device],
                                                      predicates=[inverse_function(is_different_plugin),
                                                                  or_function(compare_macs,
                                                                              compare_device_normalized_hostname)])

    def _find_correlation_with_real_adapter(self, parsed_device) -> Tuple[str, str]:
        """
        virtual by design

        :param parsed_device:
        :return: Tuple(UNIQUE_PLUGIN_NAME, id)
        """
        return self.find_suitable_newest(parsed_device,
                                         normalizations=[normalize_adapter_device],
                                         predicates=[is_different_plugin, compare_ips,
                                                     macs_do_not_contradict,
                                                     hostnames_do_not_contradict])

    def find_correlation(self, parsed_device) -> Tuple[str, str]:
        """
        Find a correlation for the given device, assign ID if not available on given device
        :param parsed_device: parsed device
        :return: (plugin_unique_name, id)
        """
        self_correlation = self._find_correlation_with_self(parsed_device)
        if self_correlation:
            # Case "A": The device has been found to be the same as a previous result
            # meaning that it should get an `id` but not a "correlate" field
            _, self_correlation_id = self_correlation
            parsed_device['data']['id'] = self_correlation_id
            return None

        # generate a fake id
        parsed_device['data']['id'] = uuid.uuid4().hex

        remote_correlation = self._find_correlation_with_real_adapter(parsed_device)
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
                self.logger.debug(f"Found remote correlation but not self correlation - {newest_device['data']['id']}")
                # updating a current adapter correlation so no new one will be created - basically a different kind
                # of self correlation
                parsed_device['data']['id'] = newest_device['data']['id']
                return None
            return remote_correlation

        # if a scanner has a hostname or macs this will act as its ID
        my_macs = set(extract_all_macs(parsed_device['data'].get('network_interfaces')))
        hostname = get_hostname(parsed_device)

        # the device has only a fake ID and no correlations - ignore it
        return None if my_macs or hostname else IGNORE_DEVICE


class ScannerAdapterBase(AdapterBase, Feature, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _try_query_data_by_client(self, client_name, entity_type):
        raw_data, parsed_data = super()._try_query_data_by_client(client_name, entity_type)

        if entity_type == "devices":
            with self._get_db_connection(True) as db:
                aggregator_db = db[AGGREGATOR_PLUGIN_NAME]
                devices = aggregator_db['devices_db'].find()
            scanner = self._get_scanner_correlator(self.logger, devices)

            num_of_devices = len(parsed_data)
            print_modulo = max(int(num_of_devices / 10), 1)
            device_number = 0
            for device in parsed_data:
                device['correlates'] = scanner.find_correlation({"data": device,
                                                                 PLUGIN_UNIQUE_NAME: self.plugin_unique_name,
                                                                 PLUGIN_NAME: self.plugin_name,
                                                                 'plugin_type': self.plugin_type})
                if device_number % print_modulo == 0:
                    self.logger.info(f"Got {device_number} devices out of {num_of_devices}.")
                device_number += 1
        return raw_data, parsed_data

    @property
    def plugin_type(self):
        return ADAPTER_PLUGIN_TYPE

    @property
    def plugin_subtype(self):
        return SCANNER_ADAPTER_PLUGIN_SUBTYPE

    @classmethod
    def specific_supported_features(cls) -> list:
        return ["ScannerAdapter"]

    @property
    def _get_scanner_correlator(self):
        return ScannerCorrelatorBase
