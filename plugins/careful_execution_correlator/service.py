from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME
from axonius.correlator_base import CorrelatorBase
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
                                                                    parse_correlation_results,
                                                                    logger=self.logger)

    def get_devices_from_ids(self, devices_ids=None):
        """
        Only devices that are either AD or AWS
        :param devices_ids:
        :return:
        """
        with self._get_db_connection(True) as db:
            aggregator_db = db[AGGREGATOR_PLUGIN_NAME]
            if devices_ids is None:
                return list(aggregator_db['devices_db'].find(
                    {
                        'adapters.plugin_name': {
                            '$in': ['aws_adapter', 'ad_adapter']
                        }
                    }))
            else:
                return list(aggregator_db['device_db'].find({
                    'internal_axon_id': {
                        "$in": devices_ids
                    }
                }))

    def _correlate(self, devices: list):
        return self._correlation_engine.correlate(devices)
