from enum import Enum


class PluginSubtype(Enum):
    NotRunning = 'NotRunning'
    PreCorrelation = 'Pre-Correlation'
    PostCorrelation = 'Post-Correlation'
    Correlator = 'Correlator'
    ScannerAdapter = 'ScannerAdapter'
    Core = 'Core'
    AdapterBase = 'AdapterBase'
    Execution = 'Execution'
