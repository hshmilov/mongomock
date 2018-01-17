"""
CorrelatorPlugin.py: A Plugin for the devices correlation process
"""
from funcy import pairwise
import itertools

from axonius.correlator_base import CorrelationResult
from axonius.correlator_engine_base import CorrelatorEngineBase
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.consts.adapter_consts import SCANNER_FIELD


def _are_ips_compatible(first_list, second_list):
    def extract_all_ips(network_ifs):
        if network_ifs is None:
            return
        for network_if in network_ifs:
            for ip in network_if.get('IP', []):
                yield ip

    first_set = set(extract_all_ips(first_list))
    second_set = set(extract_all_ips(second_list))

    if len(first_set) == 0 or len(second_set) == 0:
        return False
    return first_set.issubset(second_set) or second_set.issubset(first_set)


def _are_macs_compatible(first_list, second_list):
    def extract_all_macs(network_ifs):
        if network_ifs is None:
            return
        for network_if in network_ifs:
            current_mac = network_if.get('MAC', '')
            if current_mac != '' and current_mac is not None:
                yield current_mac.upper().replace('-', '').replace(':', '')

    first_set = set(extract_all_macs(first_list))
    second_set = set(extract_all_macs(second_list))

    if len(first_set) == 0 or len(second_set) == 0:
        return False
    return first_set.issubset(second_set) or second_set.issubset(first_set)


def _correlate_mac_ip(all_adapter_devices):
    # Remove Nones
    all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                           if adapter_device['data'].get('OS', {}).get('type') is not None]
    for x, y in itertools.combinations(all_adapter_devices, 2):
        if not _are_ips_compatible(x['data']['network_interfaces'], y['data']['network_interfaces']):
            continue
        if not _are_macs_compatible(x['data']['network_interfaces'], y['data']['network_interfaces']):
            continue
        if x['data']['OS']['type'].upper() != y['data']['OS']['type'].upper():
            continue
        # If we reached here that means that we should join this two devices according to this rule.
        yield CorrelationResult(associated_adapter_devices=[(x[PLUGIN_UNIQUE_NAME], x['data']['id']),
                                                            (y['plugin_name'], y['data']['id'])],
                                data={
                                    'Reason': 'They have the same OS, MAC and IPs'},
                                reason='StaticAnalysis')


def _correlate_hostname_ip(all_adapter_devices):
    # Remove Nones
    all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                           if adapter_device['data'].get('hostname') is not None]
    all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                           if adapter_device['data'].get('OS', {}).get('type') is not None]
    all_adapter_devices.sort(key=lambda adapter_device: adapter_device['data']['hostname'].upper())
    all_adapter_devices.sort(key=lambda adapter_device: adapter_device['data']['OS']['type'].upper())

    def process_bucket(bucket):
        for x, y in itertools.combinations(bucket, 2):
            if _are_ips_compatible(x['data']['network_interfaces'], y['data']['network_interfaces']):
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


def _correlate_scanner_mac_ip(all_adapter_devices):
    # Remove Nones
    all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                           if len(adapter_device['data']['network_interfaces']) > 0 and
                           len([x.get('MAC') for x in adapter_device['data']['network_interfaces']
                                if len(x.get('MAC', '')) > 0]) > 0]
    for x, y in itertools.combinations(all_adapter_devices, 2):
        if not (x['data'].get(SCANNER_FIELD, False) or y['data'].get(SCANNER_FIELD, False)):
            continue
        if not _are_ips_compatible(x['data']['network_interfaces'], y['data']['network_interfaces']):
            continue
        if not _are_macs_compatible(x['data']['network_interfaces'], y['data']['network_interfaces']):
            continue
        # If we reached here that means that we should join this two devices according to this rule.
        yield CorrelationResult(associated_adapter_devices=[(x[PLUGIN_UNIQUE_NAME], x['data']['id']),
                                                            (y['plugin_name'], y['data']['id'])],
                                data={
                                    'Reason': 'They have the same MAC and IPs'},
                                reason='ScannerAnalysisMacIP')


def _correlate_scanner_hostname_ip(all_adapter_devices):
    # Remove Nones
    all_adapter_devices = [adapter_device for adapter_device in all_adapter_devices
                           if adapter_device['data'].get('hostname') is not None]
    all_adapter_devices.sort(key=lambda adapter_device: adapter_device['data']['hostname'].upper())

    def process_bucket(bucket):
        for x, y in itertools.combinations(bucket, 2):
            if not (x['data'].get(SCANNER_FIELD, False) or y['data'].get(SCANNER_FIELD, False)):
                continue
            if _are_ips_compatible(x['data']['network_interfaces'], y['data']['network_interfaces']):
                yield CorrelationResult(associated_adapter_devices=[(x[PLUGIN_UNIQUE_NAME], x['data']['id']),
                                                                    (y['plugin_name'], y['data']['id'])],
                                        data={
                                            'Reason': 'They have the same hostname and IPs'},
                                        reason='ScannerAnalysisMacIP')

    if len(all_adapter_devices) < 2:
        return

    bucket = [all_adapter_devices[0]]
    for a, b in pairwise(all_adapter_devices):
        if a['data']['hostname'].upper() != b['data']['hostname'].upper() \
                or b['data']['hostname'] is None:
            yield from process_bucket(bucket)
            bucket = []
        bucket.append(b)
    if len(bucket) > 1:
        yield from process_bucket(bucket)


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

        # lets find devices by, hostname, os, and ip:
        yield from _correlate_hostname_ip(all_adapter_devices)

        # Now lets find devices by MAC, os, and IP
        yield from _correlate_mac_ip(all_adapter_devices)

        # Now lets correlate scanner devices
        yield from _correlate_scanner_mac_ip(all_adapter_devices)
        yield from _correlate_scanner_hostname_ip(all_adapter_devices)

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
