"""
ExecutionCorrelatorPlugin.py: A Plugin for the devices correlation process
"""
from axonius.ExecutionCorrelatorEngineBase import ExecutionCorrelatorEngineBase


class ExecutionCorrelatorEngine(ExecutionCorrelatorEngineBase):
    def __init__(self, *args, **kwargs):
        """
        Basic execution correlation
        """
        super().__init__(*args, **kwargs)
