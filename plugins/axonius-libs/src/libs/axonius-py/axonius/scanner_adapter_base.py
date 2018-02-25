"""
ScannerAdapterBase is an abstract class all scanner adapters should inherit from.
See https://axonius.atlassian.net/wiki/spaces/AX/pages/415858710/ScannerAdapter+Design
"""
import uuid
from abc import ABC
from typing import Tuple

from axonius.mixins.feature import Feature

from axonius.adapter_base import AdapterBase
from axonius.consts.adapter_consts import IGNORE_DEVICE, SCANNER_ADAPTER_PLUGIN_SUBTYPE, ADAPTER_PLUGIN_TYPE

from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME, PLUGIN_UNIQUE_NAME


class ScannerCorrelatorBase(object):
    def __init__(self, all_devices, plugin_unique_name, *args, **kwargs):
        """
        Base scanner correlator; base behavior is correlating with hostname
        :param all_devices: all axonius devices from DB
        """
        super().__init__(*args, **kwargs)
        self._all_devices = all_devices
        self._all_adapter_devices = [adapter for adapters in all_devices for adapter in adapters['adapters']]

        self._plugin_unique_name = plugin_unique_name

    def _find_correlation_with_self(self, parsed_device) -> str:
        """
        virtual by design

        find, if possible, a previous instance of a scanner result that refers
        to the given parsed_device
        :param parsed_device:
        :return: id of previous instance
        """
        hostname = parsed_device.get('hostname', '').strip()
        if not hostname:
            return
        for adapter_device in self._all_adapter_devices:
            if adapter_device[PLUGIN_UNIQUE_NAME] == self._plugin_unique_name:
                if adapter_device['data']['hostname'] == hostname:
                    return adapter_device['data']['id']

    def _find_correlation_with_real_adapter(self, parsed_device) -> Tuple[str, str]:
        """
        virtual by design

        :param parsed_device:
        :return:
        """
        hostname = parsed_device.get('hostname', '').strip()
        if not hostname:
            return
        for adapter_device in self._all_adapter_devices:
            if adapter_device['data'].get('hostname') == hostname:
                return adapter_device[PLUGIN_UNIQUE_NAME], adapter_device['data']['id']

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
            parsed_device['id'] = self_correlation
            return None

        # (In any case but A):
        # The device wasn't found to be the same as from a previous result
        # (i.e. this should be the first time this device is seen) so it gets an arbitrary Id
        parsed_device['id'] = uuid.uuid4().hex

        remote_correlation = self._find_correlation_with_real_adapter(parsed_device)
        if remote_correlation:
            # Case B: in this case we can correlate with something else
            return remote_correlation

        if not parsed_device.get('hostname'):
            # Case C: this device will never be able to correlate with anything in the future - ignore it
            return IGNORE_DEVICE

        # Case D: no association at all :( - just store the device, perhaps it will fall under case A
        # and in the future something will correlate us
        return None


class ScannerAdapterBase(AdapterBase, Feature, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _try_query_devices_by_client(self, *args, **kwargs):
        with self._get_db_connection(True) as db:
            aggregator_db = db[AGGREGATOR_PLUGIN_NAME]
            devices = aggregator_db['devices_db'].find()
        scanner = self._get_scanner_correlator(devices, self.plugin_unique_name)
        raw_devices, parsed_devices = super()._try_query_devices_by_client(*args, **kwargs)
        for device in parsed_devices:
            device['correlates'] = scanner.find_correlation(device)
        return raw_devices, parsed_devices

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
