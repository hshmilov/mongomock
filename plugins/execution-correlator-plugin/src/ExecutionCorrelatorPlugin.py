"""
ExecutionCorrelatorPlugin.py: A Plugin for the devices correlation process
"""
from axonius.CorrelatorBase import CorrelatorBase
from ExecutionCorrelatorEngine import ExecutionCorrelatorEngine


class ExecutionCorrelatorPlugin(CorrelatorBase):
    def __init__(self, *args, **kwargs):
        """
        Check CorrelatorBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

        executor = self.request_action

        def get_remote_plugin_correlation_cmds(plugin_name):
            return self.request_remote_plugin('correlation_cmds', plugin_name).json()

        def parse_correlation_results(plugin_unique_name, results):
            return self.request_remote_plugin('parse_correlation_results', plugin_unique_name, 'post',
                                              json=results).json()

        self._correlation_engine = ExecutionCorrelatorEngine(executor,
                                                             get_remote_plugin_correlation_cmds,
                                                             parse_correlation_results,
                                                             logger=self.logger)

    def _correlate(self, devices: list):
        """
        Correlate across the given devices
        :return:
        """
        return self._correlation_engine.correlate(devices)
