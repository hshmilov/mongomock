import logging
from collections import defaultdict
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool
from typing import List, Iterable

from dataclasses import dataclass

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, STATIC_CORRELATOR_PLUGIN_NAME
from axonius.correlator_base import CorrelatorBase
from axonius.entities import EntityType, AdapterDeviceId
from axonius.types.correlation import CorrelationResult, CorrelationReason
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import calculate_normalized_hostname
from static_correlator.engine import (CorrelationMarker,
                                      StaticCorrelatorEngine)

logger = logging.getLogger(f'axonius.{__name__}')


@dataclass()
class ErroneousCorrelation:
    internal_axon_id: str
    groups_to_split: List[List[AdapterDeviceId]]


class StaticCorrelatorService(CorrelatorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=STATIC_CORRELATOR_PLUGIN_NAME, *args, **kwargs)

        self._correlation_engine = StaticCorrelatorEngine()

    def get_entities_from_ids(self, entities_ids=None):
        """ return devices in the form requested by the StaticCorrelatorEngine, as follows:
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
         } """
        if entities_ids is None:
            match = {}
        else:
            match = {
                'internal_axon_id': {
                    '$in': entities_ids
                }
            }

        fields_to_get = ('id', 'os', 'name', 'hostname', 'network_interfaces', 'device_serial',
                         'last_seen', 'bios_serial', 'domain', 'cloud_provider', 'cloud_id', 'ad_name',
                         'azure_display_name',
                         'last_used_users', 'nessus_no_scan_id', 'private_dns_name', 'macs_no_ip',
                         'node_id', 'azure_ad_id', 'azure_device_id', 'fetch_proto',
                         'associated_adapter_plugin_name', 'value', 'type', 'name', 'aws_device_type')
        projection = {
            f'adapters.data.{field}': True for field in fields_to_get
        }
        projection.update({
            f'tags.data.{field}': True for field in fields_to_get
        })

        return list(self.devices_db.find(match, projection={
            'internal_axon_id': True,
            'adapters.plugin_name': True,
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
            'tags.plugin_name': True,
            f'tags.{PLUGIN_UNIQUE_NAME}': True,
            'tags.associated_adapters': True,
            'tags.name': True,
            **projection
        }))

    # pylint: disable=arguments-differ
    def _correlate(self, entities: list, use_markers=False):
        return self._correlation_engine.correlate(entities, use_markers=use_markers,
                                                  correlation_config={'correlate_ad_sccm': self._correlate_ad_sccm,
                                                                      'csv_full_hostname': self._csv_full_hostname})

    # pylint: enable=arguments-differ

    def _map_correlation(self, entities_to_correlate):
        """ In static correlator we want slightly different map correlation
            _correlate_mac must be called after all other correlations """

        # pylint: disable=stop-iteration-return
        def first_part_iter(correlation_iter):
            """ generator for the first part of the correlation """
            while True:
                result = next(correlation_iter)
                if isinstance(result, CorrelationMarker):
                    # First marker is the start of mac correlation
                    break
                yield result

        # pylint: enable=stop-iteration-return

        correlation_iter = self._correlate(entities_to_correlate, use_markers=True)

        with Pool(processes=2 * cpu_count()) as pool:
            logger.info('Waiting for correlation')
            pool.map(self._process_correlation_result, first_part_iter(correlation_iter))
            pool.map(self._process_correlation_result, correlation_iter)
            logger.info('Done!')

    @property
    def _entity_to_correlate(self) -> EntityType:
        return EntityType.Devices

    def __find_erroneous_devices(self) -> Iterable[ErroneousCorrelation]:
        """
        Returns an iterator of erroneous correlations

        E.g if an iterator yields ( (device1,), (device2,) ) it means we need to seperate device1, device2 into
        its own group
        :return:
        """
        cursor = self.devices_db.find({
            'adapters.data.hostname': {
                '$exists': True,
            }
        }, projection={
            'internal_axon_id': True,
            'adapters.data.hostname': True,
            'adapters.data.id': True,
            f'adapters.{PLUGIN_UNIQUE_NAME}': True,
        })

        # Loop over all potentially wrong devices
        for axonius_device in cursor:

            # map from hostnames to adapter devices
            hostname_to_devices_map = defaultdict(list)
            for adapter_device in axonius_device['adapters']:
                hostname = calculate_normalized_hostname(adapter_device)
                if hostname:
                    hostname_to_devices_map[hostname].append(adapter_device)

            # if not all non-empty hostnames are the same
            if len(hostname_to_devices_map) > 1:
                res = ErroneousCorrelation(axonius_device['internal_axon_id'], [])

                # sorted ascending

                # lambda is necessary! bug in pylint
                # pylint: disable=unnecessary-lambda
                sorted_by_length = sorted(hostname_to_devices_map.values(), key=lambda v: len(v))
                # pylint: enable=unnecessary-lambda

                for devices in sorted_by_length[:-1]:
                    # yield a group of devices to separate
                    res.groups_to_split.append([AdapterDeviceId(device[PLUGIN_UNIQUE_NAME], device['data']['id'])
                                                for device
                                                in devices])
                yield res

    def detect_errors(self, should_fix_errors: bool):
        """
        If implemented, will respond to 'detect_errors' triggers, and will detect errors on made correlations
        :param should_fix_errors: Whether or not to try to fix the errors
        """
        axonius_devices_count = 0
        for err in self.__find_erroneous_devices():
            axonius_devices_count += 1
            logger.info(f'Found correlation error: {err}')

            if should_fix_errors:
                for group in err.groups_to_split:
                    for adapter_device in group:
                        self.unlink_adapter(EntityType.Devices,
                                            adapter_device.plugin_unique_name,
                                            adapter_device.data_id)

                    if len(group) > 1:
                        devices_to_link = [(adapter_device.plugin_unique_name, adapter_device.data_id)
                                           for adapter_device
                                           in group]
                        correlation_result = CorrelationResult(devices_to_link,
                                                               {
                                                                   'reason': 'Split due to error',
                                                               },
                                                               CorrelationReason.DetectedError)
                        self.link_adapters(EntityType.Devices, correlation_result)
        return {
            'devices_cleared': axonius_devices_count
        }
