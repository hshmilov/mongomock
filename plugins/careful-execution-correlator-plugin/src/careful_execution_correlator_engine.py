"""
CarefulExecutionCorrelatorEngine.py: A Plugin for the devices correlation process
"""
import itertools

from axonius.correlator_base import figure_actual_os
from axonius.execution_correlator_engine_base import ExecutionCorrelatorEngineBase


class CarefulExecutionCorrelatorEngine(ExecutionCorrelatorEngineBase):
    """
    Careful execution correlation means we're trying to minimize the amount of code executions we issue
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _prefilter_device(self, devices) -> iter:
        """
        Allow only devices that for them exists another device
        where the OS match and the intersection of their IP addresses is not empty.
        :param devices: axonius devices to correlate
        :return: device to pass the device to _correlate
        """
        devices = list(super()._prefilter_device(devices))

        def extract_all_ips_from_network_interfaces(network_ifs):
            if network_ifs is None:
                return
            for network_if in network_ifs:
                for ip in network_if.get('IP', []):
                    yield ip

        def extract_all_ips_from_axonius_device(device) -> set:
            return set(itertools.chain(
                *(extract_all_ips_from_network_interfaces(x['data'].get('network_interfaces'))
                  for x in
                  device['adapters'])))

        for axon_device1 in devices:
            plugins_connected = [adapter['plugin_name'] for adapter in axon_device1['adapters']]
            if ('ad_adapter' in plugins_connected) == ('aws_adapter' in plugins_connected):
                # Don't run on already correlated device
                # We currently want to work only on ad, aws on execution
                # TODO: Remove on next version (AX-325)
                continue
            if 'ad_adapter' not in plugins_connected and 'aws_adapter' not in plugins_connected:
                continue  # We currently want to work only on ad, aws on execution  TODO: Think about other adapters
            if 'ad_adapter' in plugins_connected and 'aws_adapter' in plugins_connected:
                continue  # Don't run on already correlated device  TODO: Remove on next version (AX-325)
            device1_ips = extract_all_ips_from_axonius_device(axon_device1)
            for axon_device2 in devices:
                if axon_device1['internal_axon_id'] == axon_device2['internal_axon_id']:
                    continue
                if figure_actual_os(axon_device1['adapters']) != figure_actual_os(axon_device2['adapters']):
                    continue

                device2_ips = extract_all_ips_from_axonius_device(axon_device2)
                if device1_ips.intersection(device2_ips):
                    yield axon_device1
                    break
