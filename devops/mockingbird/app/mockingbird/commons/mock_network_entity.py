from enum import Enum

from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass


class MockNetworkEntityProperties(Enum):
    pass


class MockNetworkEntity(SmartJsonClass):
    parser_specific_extra = Field(dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_raise_if_not_exist(False)

    def add_property(self, mock_entity_property: MockNetworkEntityProperties):
        if mock_entity_property not in self.properties:
            self.properties.append(mock_entity_property)

    def does_have_property(self, mock_entity_property: MockNetworkEntityProperties):
        return mock_entity_property.name in self.properties  # pylint: disable=unsupported-membership-test

    def add_specific(self, adapter_property: MockNetworkEntityProperties, smart_json_class: SmartJsonClass):
        if not self.parser_specific_extra:
            self.parser_specific_extra = {}
        self.parser_specific_extra[adapter_property.name] = smart_json_class

    def get_specific(self, adapter_property: MockNetworkEntityProperties):
        return self.parser_specific_extra.get(adapter_property.name) if self.parser_specific_extra else None
