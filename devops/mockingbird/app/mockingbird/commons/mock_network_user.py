from enum import auto

from axonius.fields import ListField
from axonius.users.user_adapter import UserAdapter
from mockingbird.commons.mock_network_entity import MockNetworkEntity, MockNetworkEntityProperties


class MockNetworkUserProperties(MockNetworkEntityProperties):
    ADUser = auto()


class MockNetworkUser(UserAdapter, MockNetworkEntity):
    properties = ListField(MockNetworkUserProperties)
