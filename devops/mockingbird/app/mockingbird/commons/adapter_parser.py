import re

from abc import ABC
from typing import List, Generator, ClassVar

from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from mockingbird.commons.mock_network_entity import MockNetworkEntity
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.mock_network_user import MockNetworkUser, MockNetworkUserProperties
from mockingbird.commons.mock_network import MockNetworkEntities


# pylint: disable=protected-access
class AdapterParser(ABC):
    def __init__(
            self,
            plugin_class: ClassVar,
            devices_properties: List[MockNetworkDeviceProperties],
            users_properties: List[MockNetworkUserProperties]
    ):
        self.plugin_class = plugin_class
        self.plugin_name = re.sub(r'([A-Z])', r' \1', self.plugin_class.__name__).strip().lower().replace(' ', '_')
        self.__entity_properties = {
            MockNetworkEntities.MockNetworkDeviceEntity: devices_properties,
            MockNetworkEntities.MockNetworkUserEntity: users_properties
        }
        self.__entity_parsing_methods = {
            MockNetworkEntities.MockNetworkDeviceEntity: self._parse_device,
            MockNetworkEntities.MockNetworkUserEntity: self._parse_user
        }

        self.__new_entity_methods = {
            MockNetworkEntities.MockNetworkDeviceEntity: self.new_device_adapter,
            MockNetworkEntities.MockNetworkUserEntity: self.new_user_adapter
        }

    def parse_entities(self, entity_type: MockNetworkEntities,
                       entities: List[MockNetworkEntity]) -> Generator[SmartJsonClass, None, None]:
        parsed_entities = 0
        for entity in entities:
            if any(entity.does_have_property(parser_property)
                   for parser_property in self.__entity_properties[entity_type]):
                new_entity = self.__new_entity_methods[entity_type]()
                # new_entity.field = entity.field is a very common pattern, so we disable raising exceptions
                # if key is not found
                new_entity.set_raise_if_not_exist(False)
                entity.set_raise_if_not_exist(False)

                self.copy_extra_property(entity_type, new_entity, entity)

                for entity_to_yield in self.__entity_parsing_methods[entity_type](new_entity, entity):
                    yield entity_to_yield
                parsed_entities += 1
                if parsed_entities > 0 and parsed_entities % 1000 == 0:
                    print(f'[+] Parsed {parsed_entities} {self.plugin_name} entities')

    def copy_extra_property(self,
                            entity_type: MockNetworkEntities, new_entity: SmartJsonClass, entity: MockNetworkEntity):
        """
        If the entity has a specific SmartJsonClass (DeviceAdapter / UserAdapter) part in its 'extra' fields copy it.
        :return:
        """
        if entity.parser_specific_extra:
            for extra_property, extra_value in entity.parser_specific_extra.items():
                if extra_property in [val.name for val in self.__entity_properties[entity_type]]:
                    extra_value_raw = extra_value.to_dict()
                    for key, value in extra_value_raw.items():
                        new_entity._extend_names(key, value)
                    new_entity._dict = extra_value_raw

    @staticmethod
    def new_device_adapter() -> DeviceAdapter:
        pass

    @staticmethod
    def new_user_adapter() -> DeviceAdapter:
        pass

    @staticmethod
    def _parse_device(device: DeviceAdapter, network_device: MockNetworkDevice) -> DeviceAdapter:
        yield from []

    @staticmethod
    def _parse_user(user: UserAdapter, network_user: MockNetworkUser) -> UserAdapter:
        yield from []
