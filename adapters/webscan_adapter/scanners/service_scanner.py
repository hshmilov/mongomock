from abc import ABC
from axonius.devices.device_adapter import DeviceAdapter
from axonius.logging.logger_wrapper import LoggerWrapper


class ServiceScanner(ABC):
    """
    A skeleton for a service scanner plugin.
    """

    def __init__(self, url, logger, domain=None):
        """
        initialization.
        :param logger: a logger to be used.
        :param url: URL to scan
        """
        self.logger = LoggerWrapper(logger, self.__class__.__name__)
        self.url = url
        self.results = None
        self.domain = domain

    def scan(self):
        """
        Scan service and return its data
        :return: results data
        """

    def parse(self, device: DeviceAdapter):
        """
        parses the scanner results
        :param device: device to parse the results into
        :return: None
        """
