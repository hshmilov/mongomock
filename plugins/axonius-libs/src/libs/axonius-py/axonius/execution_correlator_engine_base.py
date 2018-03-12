"""
ExecutionCorrelationEngineBase.py: A base class that implements execution based correlation
"""
from collections import OrderedDict
from datetime import timedelta, datetime
from promise import Promise

from axonius.correlator_base import WarningResult, CorrelationResult, UnsupportedOS, figure_actual_os, \
    OSTypeInconsistency
from axonius.correlator_engine_base import CorrelatorEngineBase
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME

"""
Timeout until stop waiting for execution results
"""
EXECUTE_TIMEOUT = timedelta(minutes=5)

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


class ExecutionCorrelatorEngineBase(CorrelatorEngineBase):
    def __init__(self, executor, get_remote_plugin_correlation_cmds, parse_correlation_results, *args, **kwargs):
        """
        The engine, transmission and steering wheel for correlations
        :type executor: func
        :param executor:                            executor must implement `request_action` the same way
                                                    it's implemented in PluginBase
                                                    this is IoC that helps testing and changing executors
        :type get_remote_plugin_correlation_cmds:   func
        :param get_remote_plugin_correlation_cmds:  must implement correlation_cmds(plugin_name)
        :type parse_correlation_results:            func
        :param parse_correlation_results:           must implement parse_correlation_results(plugin_name, results)
        """
        super().__init__(*args, **kwargs)

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

    def _prefilter_device(self, devices) -> iter:
        """
        Virtual by design.
        :param devices: axonius devices to correlate
        :return: device to pass the device to _correlate
        """
        # this is the least of all acceptable preconditions for correlatable devices - if none is satisfied there's no
        # way to correlate the devices and so it won't be added to adapters_to_correlate
        self.correlation_preconditions = [figure_actual_os]
        return super()._prefilter_device(devices)

    def _raw_correlate(self, devices):
        # refer to https://axonius.atlassian.net/wiki/spaces/AX/pages/90472522/Correlation+Implementation
        all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]

        # Stage (3):
        # Build plugin -> cmd dict

        # all adapters distinct by plugin_name (duplicates are ignored)
        all_adapters = {adapter_device['plugin_name']: adapter_device for adapter_device in all_adapter_devices}

        adapters_cmds = OrderedDict({
            adapter['plugin_name']: self._get_remote_plugin_correlation_cmds(adapter[PLUGIN_UNIQUE_NAME]) or {}
            for adapter in all_adapters.values()
        })

        self.logger.debug(f"Adapter cmds: {adapters_cmds}")

        # Stage (4):
        promises = {}

        for i, device in enumerate(devices):
            # this will not be None and not raise
            # because CorrelatorBase won't allow such devices to pass
            os_type = figure_actual_os(device['adapters'])

            try:
                # the order is preserved over the OrderedDict adapters_cmds
                # unavailable adapter-cmd will have a default cmd
                # so the the amount of cmds will equal the amount of adapters
                # (and because the order is preserved, we can then match the results of the cmds to the
                # adapter dict)
                cmd = [_default_shell_command(adapter_cmd.get(os_type)) for
                       adapter_cmd in adapters_cmds.values()]
            except UnsupportedOS:
                self.logger.info(f"Device {device['internal_axon_id']} has unsupported OS")
                continue
            data_for_action = {
                'shell_commands': {os_type: cmd}
            }
            promises[i] = (self._executor('execute_shell', device['internal_axon_id'],
                                          data_for_action=data_for_action), os_type)
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
                    zip(adapters_cmds.keys(), [i["data"] for i in promise.value['output']['product']])
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
                                               if adapter[PLUGIN_UNIQUE_NAME] == responder_plugin_unique_name)
                responder_adapter_id = responder_plugin_device['data']['id']
                yield CorrelationResult(
                    associated_adapters=[(responder_plugin_unique_name, responder_adapter_id),
                                         (correlation_plugin_name, response_id)],
                    data={
                        'Reason': f"{responder_plugin_unique_name} executed code " +
                                  f"and found out it sees {correlation_plugin_name} " +
                                  f"as {response_id}"})

    def _post_process(self, first_name, first_id, second_name, second_id, data, reason) -> bool:
        if reason == 'Execution':
            if second_name == first_name:
                # this means that some logic in the correlator logic is wrong, because
                # such correlations should have reason == "Logic"
                self.logger.error(
                    f"{first_name} correlated to itself, id: '{first_id}' and '{second_id}' via execution")
                return False
        return True
