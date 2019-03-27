from axonius.correlator_base import CorrelatorBase
from axonius.entities import EntityType
from axonius.utils.files import get_local_config_file
from careful_execution_correlator.engine import CarefulExecutionCorrelatorEngine


class CarefulExecutionCorrelatorService(CorrelatorBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__), *args, **kwargs)

        executor = self.request_action

        def get_remote_plugin_correlation_cmds(plugin_name):
            return self.request_remote_plugin('correlation_cmds', plugin_name).json()

        def parse_correlation_results(plugin_unique_name, results):
            return self.request_remote_plugin('parse_correlation_results', plugin_unique_name, 'post',
                                              json=results).json()

        self._correlation_engine = CarefulExecutionCorrelatorEngine(executor,
                                                                    get_remote_plugin_correlation_cmds,
                                                                    parse_correlation_results)

    def get_entities_from_ids(self, entities_ids=None):
        """
        Only devices that are either AD or AWS
        """
        if entities_ids is None:
            return list(self.devices_db.find(
                {
                    'adapters.plugin_name': {
                        '$in': ['aws_adapter', 'active_directory_adapter']
                    }
                }))
        return list(self.devices_db.find({
            'internal_axon_id': {
                '$in': entities_ids
            }
        }))

    def _correlate(self, entities: list):
        return []
        # return self._correlation_engine.correlate(entities)

    @property
    def _entity_to_correlate(self) -> EntityType:
        return EntityType.Devices
