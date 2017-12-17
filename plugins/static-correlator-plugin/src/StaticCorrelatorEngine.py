"""
CorrelatorPlugin.py: A Plugin for the devices correlation process
"""
from datetime import timedelta, datetime
import exceptions
from namedlist import namedlist
from funcy import pairwise

# the reason for these data types is that it allows separation of the code that figures out correlations
# and code that links devices (aggregator) or sends notifications.

"""
Represent a link that should take place.

associated_adapter_devices  - tuple between unique adapter name and id, e.g.
    (
        ("aws_adapter_30604", "i-0549ca2d6c2e42a70"),
        ("esx_adapter_14575", "527f5691-de18-6657-783e-56fd1a5322cd")
    )

data                        - associated data with this link, e.g. {"reason": "they look the same"}
reason                      - 'Execution' or 'Logic'
                              'Execution' means the second part has plugin_name
                              'Logic' means the second part has plugin_unique_name
"""
CorrelationResult = namedlist('CorrelationResult', ['associated_adapter_devices', 'data', ('reason', 'Execution')])

"""
Represents a warning that should be passed on to the GUI.
"""
WarningResult = namedlist('WarningResult', ['title', 'content', ('notification_type', 'basic')])


class StaticCorrelatorEngine(object):
    def __init__(self, logger):
        """
        The engine, transmission and steering wheel for correlations
        :param logger:                              logger for logs and stuff
        """
        super().__init__()

        self.logger = logger

    def _raw_correlate(self, devices):
        """
        Perform static correlations
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
        all_adapter_devices.sort(key=lambda adapter_device: adapter_device['id'])
        # that was just O(nlogn)

        # it's now assured that if two adapter_devices have the same plugin_name and id, they are consecutive.
        for a, b in pairwise(all_adapter_devices):
            if a['plugin_name'] == b['plugin_name'] and a['id'] == b['id']:
                assert a['plugin_unique_name'] != b['plugin_unique_name'], \
                    f"Two exact adapters were found, {a['plugin_unique_name']} and {b['plugin_unique_name']}"
                self.logger.warning(f"Found two identical plugins with same id. plugin1: "
                                    f"{a['plugin_unique_name']}, plugin2: {b['plugin_unique_name']}, id: {a['id']}")
                yield CorrelationResult(associated_adapter_devices=[(a['plugin_unique_name'], a['id']),
                                                                    (b['plugin_unique_name'], b['id'])],
                                        data={
                                            'Reason': 'The same device is viewed ' +
                                                      'by two instances of the same adapter'},
                                        reason='Logic')

        # let's find devices by, hostname, os, and ip:
        # Remove Nones
        all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                               if adapter_device['hostname'] is not None]
        all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                               if adapter_device['OS']['type'] is not None]
        all_adapter_devices.sort(key=lambda adapter_device: adapter_device['hostname'].upper())
        all_adapter_devices.sort(key=lambda adapter_device: adapter_device['OS']['type'].upper())

        def are_ips_compatible(first_list, second_list):
            def extract_all_ips(network_ifs):
                for network_if in network_ifs:
                    for ip in network_if['IP']:
                        yield ip
            first_set = set(extract_all_ips(first_list))
            second_set = set(extract_all_ips(second_list))
            return first_set.issubset(second_set) or second_set.issubset(first_set)

        def process_bucket(bucket):
            for indexx, x in enumerate(bucket):
                for indexy, y in enumerate(bucket):
                    if indexx <= indexy:
                        continue
                    if are_ips_compatible(x['network_interfaces'], y['network_interfaces']):
                        self.logger.info(f"Found connection between {x['plugin_unique_name']}-{x['id']} "
                                         f"and {y['plugin_unique_name']}-{y['id']}")
                        yield CorrelationResult(associated_adapter_devices=[(x['plugin_unique_name'], x['id']),
                                                                            (y['plugin_unique_name'], y['id'])],
                                                data={
                                                    'Reason': 'They have the same OS, hostname and IPs'},
                                                reason='StaticAnalysis')

        if len(all_adapter_devices) < 2:
            return

        bucket = []
        bucket.append(all_adapter_devices[0])
        for a, b in pairwise(all_adapter_devices):
            if a['hostname'].upper() != b['hostname'].upper() or a['OS']['type'].upper() != b['OS']['type'].upper() \
                    or b['hostname'] is None or b['OS']['type'] is None:
                yield from process_bucket(bucket)
                bucket = []
            bucket.append(b)
        if len(bucket) > 1:
            yield from process_bucket(bucket)

    def correlate(self, devices):
        """
        This calls `_raw_correlate` and also does some significant post processing.
        Post processing involves checking that correlations made are only between available devices
        and also performs logic to deduce valid correlations (between available devices) from correlations made
        with unavailable devices.
        An "unavailable device" is a device not known to the system, i.e. not in `devices`.
        :param devices: axonius devices to correlate, assumes to contain 'OS', 'hostname' and 'network_interfaces'
        :return: iter(CorrelationResult or WarningResult)
        """
        all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]
        correlations_done_already = []

        correlations_with_unavailable_devices = []

        for result in self._raw_correlate(devices):
            if not isinstance(result, CorrelationResult):
                yield result  # only post process correlation results
                continue

            (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices

            # "first" is always the device used for correlation
            # "second" is always the device found by execution or logic

            if result.reason == 'StaticAnalysis':
                if second_name == first_name:
                    # this means that some logic in the correlator logic is wrong, because
                    # such correlations should have reason == "Logic"
                    self.logger.error(
                        f"{first_name} correlated to itself, id: '{first_id}' and '{second_id}' via execution")
                    continue

                # Checking if this devices are already correlated
                should_skip = False
                for to_check_adapters in devices:
                    all_ids = [one_adapter['id'] for one_adapter in to_check_adapters['adapters']]
                    if first_id in all_ids and second_id in all_ids:
                        should_skip = True
                        # This two devices are already correlated
                        break
                if should_skip:
                    continue

                # TODO: this is a slow query, it makes the algorithm O(n^2)
                # we need to store `all_adapter_devices` in a sorted array
                # and use binarysearch, but python isn't too friendly here so I postpone this
                correlated_adapter_device_from_db = next((adapter for adapter in all_adapter_devices
                                                          if adapter['plugin_unique_name'] == second_name and
                                                          adapter['id'] == second_id), None)

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
                                                        any(adapter_device['plugin_unique_name'] == first_name and
                                                            adapter_device['id'] == first_id for
                                                            adapter_device in axon_device['adapters'])), None)
                if correlation_base_axonius_device is None:
                    raise RuntimeError(f"Base responder for correlation doesn't exist, {first_name} {first_id}")

                if any(tag['tagname'] == 'strongly_unbound_with' and [second_name, second_id] in tag['tagvalue'] for
                       tag
                       in correlation_base_axonius_device['tags']):
                    continue

                second_name = correlated_adapter_device_from_db['plugin_unique_name']
                result.associated_adapter_devices = ((first_name, first_id), (second_name, second_id))

            if (second_name, second_id) in correlations_done_already:
                # skip correlations done twice
                continue

            else:
                correlations_done_already.append((second_name, second_id))
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
