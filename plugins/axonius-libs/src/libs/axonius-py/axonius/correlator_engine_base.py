from typing import List, NewType, Tuple, Iterable, Callable
from types import FunctionType
from abc import ABC, abstractmethod

import itertools
from funcy import pairwise

from axonius.correlator_base import CorrelationResult
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.plugin_exceptions import PluginException

adapter_device = NewType('adapter_device', dict)
pair_comparator = NewType('lambda x,y -> bool', FunctionType)
parameter_function = NewType('lambda x -> paramter of x', Callable)
device_pair = NewType('DevicePair', Tuple)


def _compare_devices(devices_iterator: Iterable[device_pair], comparators: List[pair_comparator], data_dict: dict,
                     reason: str):
    """
    goes over the devices_iterator and compares each pair using all the comparators, if a pair has passed all the
        comparators a correlation is yielded
    :param Iterable[device_pair]|devices_iterator: the devices pairs to compare
    :param List[pair_comparator]|comparators: the comparators to use
    :param dict|data_dict: the data to pass with the correlation
    :param str|reason: the reason for the correlation being made
    :return: yields a correlation if a pair of devices goes through all the comparators successfully
    """
    for device1, device2 in devices_iterator:

        if all(compare(device1, device2) for compare in comparators):
            # If we reached here that means that we should join this two devices according to this rule.
            yield CorrelationResult(associated_adapter_devices=[(device1[PLUGIN_UNIQUE_NAME], device1['data']['id']),
                                                                (device2['plugin_name'], device2['data']['id'])],
                                    data=data_dict,  # not copying as they all have the same data
                                    reason=reason)


def _process_product(bucket1: List[adapter_device], bucket2: List[adapter_device], comparators: List[pair_comparator],
                     data_dict: dict, reason: str):
    """
    process the product of bucket1 and bucket2, this means that no inner bucket compares are made just in between
        buckets
    See doc for _compare_devices for elaboration
    """
    return _compare_devices(itertools.product(bucket1, bucket2), comparators, data_dict, reason)


def _process_combinations(bucket: List[adapter_device], comparators: List[pair_comparator],
                          data_dict: dict, reason: str):
    """
    process the combinations of bucket, this means that each device in the bucket is compared to all others.
    See doc for _compare_devices for elaboration
    """
    return _compare_devices(itertools.combinations(bucket, 2), comparators, data_dict, reason)


def _process_preconditioned_bucket(bucket: List[adapter_device],
                                   pair_correlation_preconditions: List[parameter_function],
                                   inner_bucket_comparators: List[pair_comparator], data_dict: dict, reason: str):
    """
    separates the bucket into 2 -
        1. containing the devices with the precondition for a correlation
        2. all the rest
        This way, we minimize the combinations we compare - i.e. only pairs where one is satisfies the preconditions are
        compared.
        for example if we want to correlate a scanner - there's no reason to go over pairs where no device is a scanner
        same goes for ad.
    :param bucket: the bucket of devices to potentially correlate
    :param pair_correlation_preconditions: the precondition at least one of the correlated pair should hold
    :param inner_bucket_comparators: the comparators for the pair once at least one satisfies the preconditions
    :param dict|data_dict: the data to pass with the correlation
    :param str|reason: the reason for the correlation being made
    :return: yields a correlation if a pair of devices goes through all the comparators successfully
    """
    preconditioned_bucket = list()
    rest_of_devices = list()
    for adapter_device in bucket:
        if any(precondition(adapter_device) for precondition in pair_correlation_preconditions):
            preconditioned_bucket.append(adapter_device)
        else:
            rest_of_devices.append(adapter_device)
    # processes the product of the two buckets
    yield from _process_product(preconditioned_bucket, rest_of_devices, inner_bucket_comparators, data_dict, reason)
    # process possible correlations where both devices satisfy the precondition
    yield from _process_combinations(preconditioned_bucket, inner_bucket_comparators, data_dict, reason)


def _prefilter_devices(devices, correlation_preconditions):
    for device in devices:
        try:
            adapters = device['adapters']
            if any(correlation_precondition(adapters) for correlation_precondition in correlation_preconditions):
                yield device
        except Exception:
            pass


class CorrelatorEngineBase(ABC):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.correlation_preconditions = None

    def _prefilter_device(self, devices) -> iter:
        """
        Virtual by design.
        :param devices: axonius devices to correlate
        :return: device to pass the device to _correlate
        """
        assert self.correlation_preconditions, "Correlation preconditions were not defined"
        return _prefilter_devices(devices, self.correlation_preconditions)

    def _bucket_creator(self, adapters_to_correlate: List[adapter_device], sort_order: List[parameter_function],
                        bucket_insertion_comparators: List[pair_comparator]):
        """
        Performs an initial sort and pairwise comparison in order to minimize the buckets.
            Buckets are filled with adapter_devices which pass the bucket_insertion_comparators.
            When a device misses the bucket, we pass the bucket for further inspection to see if any correlations occur.
            If you can - for performance purposes use sort order and bucket_insertion_comparators as to lower the amount
            of combinations as much as possible
        for further details also see _process_combinations docs
        :param adapters_to_correlate: a list of the adapters to correlate
        :param sort_order: a list of sorting lambdas in order of the wanted sort
        :param bucket_insertion_comparators: a list of comparators of type lambda x,y -> bool
                for which an adapter_device would enter the bucket
        """

        if len(adapters_to_correlate) < 2:
            return

        for func in reversed(sort_order):
            adapters_to_correlate.sort(key=func)

        bucket = [adapters_to_correlate[0]]
        pair_number = 0
        num_of_pairs = len(adapters_to_correlate)
        print_count = max(int(float(num_of_pairs) / 100), 100)
        for a, b in pairwise(adapters_to_correlate):
            if pair_number % print_count == 0:
                self.logger.info(f"Correlating outer bucket of #pair: {pair_number} out of {num_of_pairs}")
            if all(compare(a, b) for compare in bucket_insertion_comparators):
                bucket.append(b)
            else:
                if len(bucket) > 1:
                    yield bucket
                bucket = [b]
            pair_number += 1
        if len(bucket) > 1:
            yield bucket

    def _bucket_correlate(self, adapters_to_correlate: List[adapter_device], sort_order: List[parameter_function],
                          bucket_insertion_comparators: List[pair_comparator],
                          pair_correlation_preconditions: List[parameter_function],
                          inner_bucket_comparators: List[pair_comparator], data_dict: dict, reason: str):
        """
        see docs for _bucket_creator and _process_preconditioned_bucket
        :param adapters_to_correlate: a list of the adapters to correlate
        :param sort_order: a list of sorting lambdas in order of the wanted sort
        :param bucket_insertion_comparators: a list of comparators of type lambda x,y -> bool
                for which an adapter_device would enter the bucket
        :param pair_correlation_preconditions: the precondition at least one of the correlated pair should hold
        :param inner_bucket_comparators: the comparators for the pair once at least one satisfies the preconditions
        :param dict|data_dict: the data to pass with the correlation
        :param str|reason: the reason for the correlation being made
        :return: yields a correlation if a pair of devices goes through all the comparators successfully
        """
        for bucket in self._bucket_creator(adapters_to_correlate, sort_order, bucket_insertion_comparators):
            if pair_correlation_preconditions:
                yield from _process_preconditioned_bucket(bucket, pair_correlation_preconditions,
                                                          inner_bucket_comparators, data_dict, reason)
            else:
                yield from _process_combinations(bucket, inner_bucket_comparators, data_dict, reason)

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
        all_adapter_devices.sort(key=lambda adapter_device: str(adapter_device['data']['id']))
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
        logic_correlations = self._preprocess_devices(devices)
        all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]
        devices = list(self._prefilter_device(devices))
        correlations_done_already = list()

        correlations_with_unavailable_devices = list()

        self.logger.info(f"Correlating {len(devices)} devices")
        for result in itertools.chain(logic_correlations, self._raw_correlate(devices)):
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

                if any(tag['name'] == 'strongly_unbound_with' and [second_name, second_id] in tag['data'] for
                       tag
                       in correlation_base_axonius_device['tags']):
                    continue

                second_name = correlated_adapter_device_from_db[PLUGIN_UNIQUE_NAME]
                result.associated_adapter_devices = [(first_name, first_id), (second_name, second_id)]
            sorted_associated_adapter_devices = sorted(result.associated_adapter_devices)
            if sorted_associated_adapter_devices in correlations_done_already:
                self.logger.debug(f"result is the same as old one : {result}")
                # skip correlations done twice
                continue

            else:
                correlations_done_already.append(sorted_associated_adapter_devices)
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
