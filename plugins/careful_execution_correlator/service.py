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

    def _correlate(self, devices: list):
        return self._correlation_engine.correlate(devices)
