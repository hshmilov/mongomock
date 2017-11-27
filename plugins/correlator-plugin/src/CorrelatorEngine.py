"""
CorrelatorPlugin.py: A Plugin for the devices correlation process
"""
from collections import OrderedDict
from datetime import timedelta, datetime
import exceptions
from namedlist import namedlist
from funcy import pairwise
from promise import Promise

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

"""
Timeout until stop waiting for execution results
"""
EXECUTE_TIMEOUT = timedelta(minutes=5)


def _figure_actual_os(adapters):
    """
    Figures out the OS of the device according to the adapters.
    If they aren't consistent about the OS, return None
    :param adapters: list
    :return:
    """
    oses = list(set(adapter['data']['OS']['type'] for adapter in adapters))

    if None in oses:
        # None might be in oses if at least one adapter couldn't figure out the OS,
        # if all other adapters are consistent regarding the OS - we accept it
        oses.remove(None)

    if len(oses) == 0:
        return None  # no adapters know anything - we have no clue which OS the device is running

    if len(oses) == 1:
        return oses[0]  # no adapters disagree (except maybe those which don't know)

    raise exceptions.OSTypeInconsistency(oses)  # some adapters disagree


"""
This should be the output of the fake cmd used for adapters without a CMD 
"""
UNAVAILABLE_CMD_OUTPUT = "__NOTHING__"


def _default_shell_command(cmd):
    """
    Run something if cmd is empty
    :param cmd:
    :return:
    """
    if cmd is None or len(cmd.strip()) == 0:
        return f"echo {UNAVAILABLE_CMD_OUTPUT}"
    return cmd


def _find_contradictions(devices, devices_execution_results):
    """
    Finds devices that are correlated differently that what devices_execution_results suggests
    and remove contradicting devices
    :param devices: axonius devices to correlate
    :param devices_execution_results: see _correlator
    :return: iter(WarningResult)
    """
    to_remove_indexes = []
    for axon_device_idx, (_, execution_results) in devices_execution_results.items():
        associated_device = devices[axon_device_idx]

        for correlation_plugin_name, response_id in execution_results.items():
            # if the axonius device already contains the given adapter device
            already_correlated_adapter_device = \
                next((adapter for
                      adapter in associated_device['adapters']
                      if adapter['plugin_name'] == correlation_plugin_name),
                     None)
            if already_correlated_adapter_device is not None:
                if already_correlated_adapter_device['data']['id'] != response_id:
                    yield WarningResult(
                        f"device {associated_device['internal_axon_id']} is already correlated with " +
                        f"{correlation_plugin_name} with " +
                        f"id = {already_correlated_adapter_device['data']['id']} but execution suggests " +
                        f"its id should be {response_id}",
                        [associated_device['internal_axon_id'], correlation_plugin_name,
                         already_correlated_adapter_device['data']['id'], response_id],
                        "CORRELATION_CONTRADICTION")
                    to_remove_indexes.append(axon_device_idx)
                    break

    for i in to_remove_indexes:
        del devices_execution_results[i]


class CorrelatorEngine(object):
    def __init__(self, logger, executor, get_remote_plugin_correlation_cmds, parse_correlation_results):
        """
        The engine, transmission and steering wheel for correlations
        :param logger:                              logger for logs and stuff
        :type executor: func
        :param executor:                            executor must implement `request_action` the same way
                                                    it's implemented in PluginBase
                                                    this is IoC that helps testing and changing executors
        :type get_remote_plugin_correlation_cmds:   func
        :param get_remote_plugin_correlation_cmds:  must implement correlation_cmds(plugin_name)
        :type parse_correlation_results:            func
        :param parse_correlation_results:           must implement parse_correlation_results(plugin_name, results)
        """
        super().__init__()

        self.logger = logger

        self._executor = executor
        self._get_remote_plugin_correlation_cmds = get_remote_plugin_correlation_cmds

        def _parse_correlation_results(adapter, result, os_type):
            if result.strip() == UNAVAILABLE_CMD_OUTPUT:
                return None
            return parse_correlation_results(adapter,
                                             {'result': result,
                                              'os': os_type}
                                             )

        self._parse_correlation_results = _parse_correlation_results

    def _raw_correlate(self, devices):
        """
        Perform correlation over the online devices provided.
        This does no validation over correlations: it doesn't check that correlations made are consistent, but
        it does check that the execution is consistent with `devices`.
        For example, this might try to correlate a device with a another device (returned from execution) even if
        the second device isn't known to the system.
        :param devices: axonius devices to correlate
        :return: iter(CorrelationResult or WarningResult)
        """
        # refer to https://axonius.atlassian.net/wiki/spaces/AX/pages/90472522/Correlation+Implementation

        # Stage (2):
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
                assert a['plugin_unique_name'] != b[
                    'plugin_unique_name'], f"Two exact adapters were found, {a} and {b}"
                yield CorrelationResult(associated_adapter_devices=[(a['plugin_unique_name'], a['data']['id']),
                                                                    (b['plugin_unique_name'], b['data']['id'])],
                                        data={
                                            'Reason': 'The same device is viewed ' +
                                                      'by two instances of the same adapter'},
                                        reason='Logic')

        # Stage (3):
        # Build plugin -> cmd dict1

        # all adapters distinct by plugin_name (duplicates are ignored)
        all_adapters = {adapter_device['plugin_name']: adapter_device for adapter_device in all_adapter_devices}

        adapters_cmds = OrderedDict({
            adapter['plugin_name']: self._get_remote_plugin_correlation_cmds(adapter['plugin_unique_name']) or {}
            for adapter in all_adapters.values()
        })

        self.logger.debug(f"Adapter cmds: {adapters_cmds}")

        # Stage (4):
        promises = {}

        for i, device in enumerate(devices):
            try:
                os_type = _figure_actual_os(device['adapters'])
            except exceptions.OSTypeInconsistency as e:
                oses, = e.args
                yield WarningResult(
                    f"device {device['internal_axon_id']} exists with inconsistent OSes across adapters",
                    [device['internal_axon_id'], oses],
                    "OS_INCONSISTENCY")
                continue

            try:
                # the order is preserved over the OrderedDict adapters_cmds
                # unavailable adapter-cmd will have a default cmd
                # so the the amount of cmds will equal the amount of adapters
                # (and because the order is preserved, we can then match the results of the cmds to the
                # adapter dict)
                cmd = [_default_shell_command(adapter_cmd.get(os_type)) for
                       adapter_cmd in adapters_cmds.values()]
            except exceptions.UnsupportedOS:
                continue

            promises[i] = (self._executor('execute_shell', device['internal_axon_id'],
                                          data_for_action={
                                              'shell_command': {os_type: cmd}
            }), os_type)
        started_time = datetime.now()
        try:
            # Promise.all is a promise that's resolved when all promises are resolved
            # and it's rejected if even one of the promises are rejected,
            # because we want to wait until timeout OR all promises finished,
            # we mustn't include the already rejected promises in Promise.all(...)
            while True:
                remaining_time = EXECUTE_TIMEOUT.total_seconds() - (datetime.now() - started_time).total_seconds()
                promises_to_wait_for = [p for p, _ in promises.values() if p and p.is_pending]

                self.logger.info(f"Waiting for {remaining_time} " +
                                 f"seconds for execution results on {len(promises_to_wait_for)} promises")

                promiseAll = Promise.all(promises_to_wait_for)
                Promise.wait(promiseAll, remaining_time)
                if promiseAll.is_fulfilled:
                    break

        except Exception as e:
            # the exception thrown by this library aren't the best
            if e.args and e.args[0] == 'Timeout':
                yield WarningResult(f"Timeout reached while waiting for execution results", "", "EXECUTION_TIMEOUT")
            else:
                raise

        # dict(axon_device_idx) ->
        #   (plugin_unique_name, dict(plugin_name) -> id )
        #
        # in plain words
        # * axon_device_idx                 - (int) in devices
        # * plugin_unique_name              - the adapter_device that actually responded to the execution request
        # * dict(plugin_name) -> id         - the results of this execution, by plugin
        devices_execution_results = {}
        for device_index, (promise, os_type) in promises.items():
            if promise.is_fulfilled and promise.value['output'].get('result') == 'Success' and \
                    'product' in promise.value['output']:
                # dict(plugin_name) -> id
                # for 'device_index'
                adapter_to_id = {
                    adapter: self._parse_correlation_results(adapter, result, os_type)
                    for adapter, result in
                    zip(adapters_cmds.keys(), promise.value['output']['product'])
                }

                # removing None values - those aren't real executions
                devices_execution_results[device_index] = promise.value['responder'], {k: v for k, v in
                                                                                       adapter_to_id.items() if
                                                                                       v is not None}

        # find contradictions, report them and remove offending devices
        yield from _find_contradictions(devices, devices_execution_results)

        # actually produce correlations according to the data
        for axon_device_idx, (responder_plugin_unique_name, execution_results) in \
                devices_execution_results.items():
            associated_device = devices[axon_device_idx]

            for correlation_plugin_name, response_id in execution_results.items():
                # on most cases that aren't first-run for devices that were already correlated,
                # we will get all the existing correlations here.
                # we already removed all contradictions before.
                if any(adapter['plugin_name'] == correlation_plugin_name
                       for adapter in associated_device['adapters']):
                    continue

                responder_plugin_device = next(adapter for
                                               adapter in associated_device['adapters']
                                               if adapter['plugin_unique_name'] == responder_plugin_unique_name)
                responder_adapter_id = responder_plugin_device['data']['id']
                yield CorrelationResult(
                    associated_adapter_devices=[(responder_plugin_unique_name, responder_adapter_id),
                                                (correlation_plugin_name, response_id)],
                    data={
                        'Reason': f"{responder_plugin_unique_name} executed code " +
                                  f"and found out it sees {correlation_plugin_name} " +
                                  f"as {response_id}"})

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

            if result.reason == 'Execution':
                if second_name == first_name:
                    # this means that some logic in the correlator logic is wrong, because
                    # such correlations should have reason == "Logic"
                    self.logger.error(
                        f"{first_name} correlated to itself, id: '{first_id}' and '{second_id}' via execution")
                    continue

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
                                                        any(adapter_device['plugin_unique_name'] == first_name and
                                                            adapter_device['data']['id'] == first_id for
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
