import logging
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, STATIC_CORRELATOR_PLUGIN_NAME
from axonius.correlator_base import CorrelatorBase
from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD, OS_FIELD
from axonius.entities import EntityType
from axonius.utils.files import get_local_config_file
from static_correlator.engine import (CorrelationMarker,
                                      StaticCorrelatorEngine)

logger = logging.getLogger(f'axonius.{__name__}')


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
        return list(self.devices_db.aggregate([
            {'$match': match},
            {'$project': {
                'internal_axon_id': 1,
                'adapters': {
                    '$map': {
                        'input': '$adapters',
                        'as': 'adapter',
                        'in': {
                            'plugin_name': '$$adapter.plugin_name',
                            PLUGIN_UNIQUE_NAME: '$$adapter.plugin_unique_name',
                            'data': {
                                'id': '$$adapter.data.id',
                                OS_FIELD: '$$adapter.data.os',
                                'name': '$$adapter.data.name',
                                'hostname': '$$adapter.data.hostname',
                                NETWORK_INTERFACES_FIELD: '$$adapter.data.network_interfaces',
                                'device_serial': '$$adapter.data.device_serial',
                                'last_seen': '$$adapter.data.last_seen',
                                'bios_serial': '$$adapter.data.bios_serial',
                                'domain': '$$adapter.data.domain',
                                'cloud_provider': '$$adapter.data.cloud_provider',
                                'cloud_id': '$$adapter.data.cloud_id',
                                'ad_name': '$$adapter.data.ad_name',
                                'azure_display_name': '$$adapter.data.azure_display_name',
                                'last_used_users': '$$adapter.data.last_used_users',
                                'nessus_no_scan_id': '$$adapter.data.nessus_no_scan_id'
                            }
                        }
                    }
                },
                'tags': 1
            }}
        ]))

    # pylint: disable=arguments-differ
    def _correlate(self, entities: list, use_markers=False):
        return self._correlation_engine.correlate(entities, use_markers=use_markers)
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
