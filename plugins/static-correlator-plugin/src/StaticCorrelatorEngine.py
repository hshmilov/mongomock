"""
CorrelatorPlugin.py: A Plugin for the devices correlation process
"""
from funcy import pairwise

from axonius.CorrelatorBase import CorrelationResult
from axonius.CorrelatorEngineBase import CorrelatorEngineBase
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


class StaticCorrelatorEngine(CorrelatorEngineBase):
    """
    For efficiency reasons this engine assumes a different structure (let's refer to it as compact structure)
    of axonius devices.
    Each adapter device should have
    {
        plugin_name: "",
        plugin_unique_name: "",
        data: {
            id: "",
            OS: {
                type: "",
                whatever...
            },
            hostname: "",
            network_interfaces: [
                {
                    IP: ["127.0.0.1", ...],
                    whatever...
                },
                ...
            ]
        }
    }
    """

    def __init__(self, *args, **kwargs):
        """
        The engine, transmission and steering wheel for correlations
        """
        super().__init__(*args, **kwargs)

    def _raw_correlate(self, devices):
        """
        Perform static correlations
        :param devices: axonius devices to correlate
        :return: iter(CorrelationResult or WarningResult)
        """
        all_adapter_devices = [adapter for adapters in devices for adapter in adapters['adapters']]

        # let's find devices by, hostname, os, and ip:

        # Remove Nones
        all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                               if adapter_device['data'].get('hostname') is not None]
        all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                               if adapter_device['data']['OS']['type'] is not None]
        all_adapter_devices.sort(key=lambda adapter_device: adapter_device['data']['hostname'].upper())
        all_adapter_devices.sort(key=lambda adapter_device: adapter_device['data']['OS']['type'].upper())

        def are_ips_compatible(first_list, second_list):
            def extract_all_ips(network_ifs):
                if network_ifs is None:
                    return
                for network_if in network_ifs:
                    for ip in network_if.get('IP', []):
                        yield ip

            first_set = set(extract_all_ips(first_list))
            second_set = set(extract_all_ips(second_list))
            return first_set.issubset(second_set) or second_set.issubset(first_set)

        def process_bucket(bucket):
            for indexx, x in enumerate(bucket):
                for indexy, y in enumerate(bucket):
                    if indexx <= indexy:
                        continue
                    if are_ips_compatible(x['data']['network_interfaces'], y['data']['network_interfaces']):
                        yield CorrelationResult(associated_adapter_devices=[(x[PLUGIN_UNIQUE_NAME], x['data']['id']),
                                                                            (y['plugin_name'], y['data']['id'])],
                                                data={
                                                    'Reason': 'They have the same OS, hostname and IPs'},
                                                reason='StaticAnalysis')

        if len(all_adapter_devices) < 2:
            return

        bucket = [all_adapter_devices[0]]
        for a, b in pairwise(all_adapter_devices):
            if a['data']['hostname'].upper() != b['data']['hostname'].upper() or a['data']['OS']['type'].upper() != \
                    b['data']['OS']['type'].upper() \
                    or b['data']['hostname'] is None or b['data']['OS']['type'] is None:
                yield from process_bucket(bucket)
                bucket = []
            bucket.append(b)
        if len(bucket) > 1:
            yield from process_bucket(bucket)

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
        if reason == 'StaticAnalysis':
            if second_name == first_name:
                # this means that some logic in the correlator logic is wrong, because
                # such correlations should have reason == "Logic"
                self.logger.error(
                    f"{first_name} correlated to itself, id: '{first_id}' and '{second_id}' via static analysis")
                return False
        return True
