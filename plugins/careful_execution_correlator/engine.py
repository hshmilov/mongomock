import itertools
from typing import Iterable

from axonius.correlator_base import figure_actual_os
from axonius.devices.device import NETWORK_INTERFACES_FIELD, IPS_FIELD
from axonius.execution_correlator_engine_base import ExecutionCorrelatorEngineBase


def take_uncorrecelated_ad_and_aws(devices) -> Iterable[dict]:
    """
    Returns only devices that have an AD or AWS plugin, but not both
    """
    for axon_device1 in devices:
        plugins_connected = [adapter['plugin_name'] for adapter in axon_device1['adapters']]
        if ('ad_adapter' in plugins_connected) == ('aws_adapter' in plugins_connected):
            # Don't run on already correlated device or devices that aren't AD or AWS
            # We currently want to work only on ad, aws on execution
            # TODO: Remove on next version (AX-325)
            continue
        yield axon_device1


class CarefulExecutionCorrelatorEngine(ExecutionCorrelatorEngineBase):
    """
    Careful execution correlation means we're trying to minimize the amount of code executions we issue
    """

    def _prefilter_device(self, devices) -> iter:
        # Allow only devices that for them exists another device
        # where the OS match and the intersection of their IP addresses is not empty.
        devices = list(super()._prefilter_device(devices))

        def extract_all_ips_from_network_interfaces(network_ifs):
            if network_ifs is None:
                return
            for network_if in network_ifs:
                for ip in network_if.get(IPS_FIELD, []):
                    yield ip

        def extract_all_ips_from_axonius_device(device) -> set:
            return set(itertools.chain(
                *(extract_all_ips_from_network_interfaces(x['data'].get(NETWORK_INTERFACES_FIELD))
                  for x in
                  device['adapters'])))

        devices = list(take_uncorrecelated_ad_and_aws(devices))

        for axon_device1 in devices:
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
