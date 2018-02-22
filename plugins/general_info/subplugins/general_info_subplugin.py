from abc import ABC, abstractmethod
from axonius.devices.device import Device


class GeneralInfoSubplugin(ABC):
    """
    A skeleton for a general info subplugin.
    """

    def __init__(self, plugin_base_delegate):
        """
        initialization.
        :param plugin_base_delegate: the "self" of a relevant plugin base.
        """
        self.plugin_base = plugin_base_delegate
        self.logger = self.plugin_base.logger

    @abstractmethod
    def get_wmi_commands(self):
        """
        Returns the wmi commands needed to understand the result.
        :return: a list of strings, each string is a wmi query.
        """
        pass

    @abstractmethod
    def handle_result(self, device, executer_info, result, adapterdata_device: Device):
        """
        Parses the result of the wmi queries.

        :param device: the device object, from the db, on which we executed.
        :param executer_info: an object that contains the info of the adapter that executed the query:
        {"adapter_unique_name": "the plugin unique name", "adapter_unique_id": "data.id of the adapter's device"}
        :param result: a list of objects, each one is the result (in the order given by get_wmi_commands).
        :param adapterdata_device: a Device object, that is used for having adapterdata tags (general-info enrichment).
        :return: the caption of the last logged user (domain+username). e.g., avidor@axonius.lan
        """
        pass
