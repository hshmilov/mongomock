from abc import ABC, abstractmethod

import itertools
from funcy import pairwise

from axonius.CorrelatorBase import CorrelationResult, figure_actual_os, OSTypeInconsistency
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


class CorrelatorEngineBase(ABC):
    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    def _prefilter_device(self, devices) -> iter:
        """
        Virtual by design.
        :param devices: axonius devices to correlate
        :return: device to pass the device to _correlate
        """
        for device in devices:
            try:
                os = figure_actual_os(device['adapters'])
                if os is not None:
                    yield device
            except OSTypeInconsistency:
                self.logger.error("OS inconsistent over correlated devices", device['internal_axon_id'])

    def _preprocess_devices(self, devices):
        """
        Virtual by design.
        :param devices: axonius devices to correlate
        :return: iter(CorrelationResult or WarningResult)
        """
        # Find out if there are adapter-devices that have the same plugin_name
        # and the same id (but different plugin_unique_name).
        # This means they are seen by two different instances of the same plugin, so they are the same.

        # get all adapter_devices irrespective of axonius devices
        all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]

        # sort by 'plugin_name'
        all_adapter_devices.sort(key=lambda adapter_device: adapter_device['plugin_name'])
        # then by 'id'
        all_adapter_devices.sort(key=lambda adapter_device: adapter_device['data']['id'])
        # that was just O(nlogn)

        # it's now assured that if two adapter_devices have the same plugin_name and id, they are consecutive.
        for a, b in pairwise(all_adapter_devices):
            if a['plugin_name'] == b['plugin_name'] and a['data']['id'] == b['data']['id']:
                assert a[PLUGIN_UNIQUE_NAME] != b[PLUGIN_UNIQUE_NAME], \
                    f"Two exact adapters were found, {a[PLUGIN_UNIQUE_NAME]} and {b[PLUGIN_UNIQUE_NAME]}"
                yield CorrelationResult(associated_adapter_devices=[(a[PLUGIN_UNIQUE_NAME], a['data']['id']),
                                                                    (b[PLUGIN_UNIQUE_NAME], b['data']['id'])],
                                        data={
                                            'Reason': 'The same device is viewed ' +
                                                      'by two instances of the same adapter'},
                                        reason='Logic')

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
        return True

    @abstractmethod
    def _raw_correlate(self, devices):
        """
        Perform correlation over the online devices provided.
        This does no validation over correlations: it doesn't check that correlations made are consistent, but
        it does check that the execution is consistent with `devices`.
        For example, this might try to correlate a device with a another device even if
        the second device isn't known to the system.
        :param devices: axonius devices to correlate
        :return: iter(CorrelationResult or WarningResult)
        """
        pass

    def correlate(self, devices):
        """
        This calls `_raw_correlate` and also does some significant post processing.
        Post processing involves checking that correlations made are only between available devices
        and also performs logic to deduce valid correlations (between available devices) from correlations made
        with unavailable devices.
        An "unavailable device" is a device not known to the system, i.e. not in `devices`.
        :param devices: axonius devices to correlate
        :return: iter(CorrelationResult or WarningResult)
        """
        devices = list(self._prefilter_device(devices))
        all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]
        correlations_done_already = []

        correlations_with_unavailable_devices = []

        self.logger.info(f"Correlating {len(devices)} devices")
        for result in itertools.chain(self._preprocess_devices(devices), self._raw_correlate(devices)):
            if not isinstance(result, CorrelationResult):
                yield result  # only post process correlation results
                continue

            (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices

            # "first" is always the device used for correlation
            # "second" is always the device found by execution or logic

            if not self._post_process(first_name, first_id, second_name, second_id, result.data, result.reason):
                continue

            if result.reason != 'Logic':
                # TODO: this is a slow query, it makes the algorithm O(n^2)
                # we need to store `all_adapter_devices` in a sorted array
                # and use binarysearch, but python isn't too friendly here so I postpone this
                correlated_adapter_device_from_db = next((adapter for adapter in all_adapter_devices
                                                          if adapter['plugin_name'] == second_name and
                                                          adapter['data']['id'] == second_id), None)

                if correlated_adapter_device_from_db is None:
                    # this means that the correlation was with a device that we don't see
                    # e.g. if we ran the AD code to figure out the AD-ID on a device seen by AWS
                    # but that device isn't seen by one of our AD clients, we will get an AD-ID
                    # we don't know, so it by itself can't produce any correlation.
                    # However, if we also see the *same* AD-ID from a different axonius-device, say
                    # from ESX, so we can deduce that the ESX device and the AWS device are the same,
                    # without actually "using" the AD device!
                    correlations_with_unavailable_devices.append(result.associated_adapter_devices)
                    continue

                # figure out if the correlation violates a `strongly_unbound_with` rule
                # https://axonius.atlassian.net/browse/AX-152
                correlation_base_axonius_device = next((axon_device for
                                                        axon_device in devices
                                                        if
                                                        any(adapter_device[PLUGIN_UNIQUE_NAME] == first_name and
                                                            adapter_device['data']['id'] == first_id for
                                                            adapter_device in axon_device['adapters'])), None)
                if correlation_base_axonius_device is None:
                    raise RuntimeError(f"Base responder for correlation doesn't exist, {first_name} {first_id}")

                if any(tag['tagname'] == 'strongly_unbound_with' and [second_name, second_id] in tag['tagvalue'] for
                       tag
                       in correlation_base_axonius_device['tags']):
                    continue

                second_name = correlated_adapter_device_from_db[PLUGIN_UNIQUE_NAME]
                result.associated_adapter_devices = ((first_name, first_id), (second_name, second_id))

            if result.associated_adapter_devices in correlations_done_already:
                # skip correlations done twice
                continue

            else:
                correlations_done_already.append(result.associated_adapter_devices)
                yield result

        # sort all correlations src->dst ("src" - device used for correlation and "dst" - device found by
        # logic or execution) by dst
        # this means that in the sorted list, only following values might have the same dst
        sorted_unavailable_devices_correlations = \
            sorted(
                sorted(correlations_with_unavailable_devices, key=lambda x: x[1][0]),
                key=lambda x: x[1][1])

        for a, b in pairwise(sorted_unavailable_devices_correlations):
            # because the iterator is now sorted by dst, we can use pairwise to find src->dst, src2->dst
            # type correlations and then deduce src->src2 correlations
            if a[1] == b[1]:
                # this means they've got the same dst!
                yield CorrelationResult((a[0], b[0]),
                                        data={
                                            "Reason": f"{a[1]} is a nonexistent device correlated " +
                                                      f"to both {a[0]} and {b[0]}"},
                                        reason="NonexistentDeduction")
