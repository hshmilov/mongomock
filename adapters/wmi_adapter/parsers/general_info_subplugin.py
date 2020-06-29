from abc import ABC, abstractmethod
from axonius.devices.device_adapter import DeviceAdapter
from axonius.logging.logger_wrapper import LoggerWrapper
from wmi_adapter.parsers.wmi_utils import check_wmi_answers_integrity


class GeneralInfoSubplugin(ABC):
    """
    A skeleton for a general info subplugin.
    """

    def __init__(self, logger):
        """
        initialization.
        :param logger: a logger to be used.
        """
        self.logger = LoggerWrapper(logger, self.__class__.__name__)

    def get_error_logs(self):
        """
        :return: a list of error logs recorded by the logger.
        """

        return self.logger.error_messages

    @staticmethod
    @abstractmethod
    def get_wmi_smb_commands():
        """
        Returns the wmi commands needed to understand the result.
        :return: a list of strings, each string is a wmi query.
        """
        pass

    def handle_result(self, plugin_base, result, adapterdata_device: DeviceAdapter):
        """
        Parses the result of the wmi queries.

        :param plugin_base:
        :param device: the device object, from the db, on which we executed.
        :param executer_info: an object that contains the info of the adapter that executed the query:
        {"adapter_unique_name": "the plugin unique name", "adapter_unique_id": "data.id of the adapter's device"}
        :param result: a list of objects, each one is the result (in the order given by get_wmi_smb_commands).
        :param adapterdata_device: a Device object, that is used for having adapterdata tags (general-info enrichment).
        :return: the caption of the last logged user (domain+username). e.g., avidor@axonius.lan
        """
        check_wmi_answers_integrity(self.get_wmi_smb_commands(), result)
