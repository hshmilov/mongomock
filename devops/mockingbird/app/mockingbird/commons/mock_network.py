import random
from enum import Enum, auto
from typing import List, Callable

import names

from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network_device import MockNetworkDevice
from mockingbird.commons.mock_network_entity import MockNetworkEntity, MockNetworkEntityProperties
from mockingbird.commons.mock_network_user import MockNetworkUser


class MockNetworkEntities(Enum):
    MockNetworkDeviceEntity = auto()
    MockNetworkUserEntity = auto()


class MockNetwork:
    """
    An object that represents a mock network.
    """

    def __init__(
            self,
            ip_start='10.21.7.4',
            public_ip_start='18.217.22.7'
    ):
        """
        Initializes the devices factory.
        :param ip_start: the first ip that we will allocate for a machine (subnet start)
        """
        self.__last_allocated_ip = mock_utils.ip2int(ip_start)
        self.__last_allocated_public_ip = mock_utils.ip2int(public_ip_start)
        self.__last_allocated_mac = 0x12443c
        self.__names = []
        self.__entities = dict()
        for entity in MockNetworkEntities:
            self.__entities[entity] = list()

        self.__entities_classes = dict()
        self.__entities_classes[MockNetworkEntities.MockNetworkDeviceEntity] = MockNetworkDevice
        self.__entities_classes[MockNetworkEntities.MockNetworkUserEntity] = MockNetworkUser

    def generate_random_names(self, count):
        for i in range(count):
            if i % 100 == 0 and i > 0:
                print(f'Random names generation: generating entity number {i}')

            name = None
            for _ in range(5):
                candidate_name = names.get_full_name()
                if candidate_name not in self.__names:
                    name = candidate_name
                    break

            if not name:
                raise ValueError(f'Could not generate a new name')
            self.__names.append(name)

    def get_random_name(self, name_i):
        return self.__names[name_i]

    def generate_ip(self):
        self.__last_allocated_ip += 1
        return mock_utils.int2ip(self.__last_allocated_ip)

    def generate_public_ip(self):
        self.__last_allocated_public_ip += 1
        return mock_utils.int2ip(self.__last_allocated_public_ip)

    def generate_mac(self, mac_type='intel'):
        mac_address_prefix = {
            'intel': '88:53:2E:',
            'dell': '50:9A:4C:'
        }

        if mac_type == 'random':
            mac_type = random.choice(mac_address_prefix.keys())

        assert mac_type in mac_address_prefix

        self.__last_allocated_mac += 1
        mac_address_suffix = '{:02X}:{:02X}:{:02X}'.format(
            (self.__last_allocated_mac >> 16) & 0xFF,
            (self.__last_allocated_mac >> 8) & 0xFF,
            self.__last_allocated_mac & 0xFF
        )
        return mac_address_prefix[mac_type] + mac_address_suffix

    def __add_entity(self, entity_type: MockNetworkEntities, entity: MockNetworkEntity):
        self.__entities[entity_type].append(entity)

    def get_devices(self) -> List[MockNetworkDevice]:
        return self.__entities[MockNetworkEntities.MockNetworkDeviceEntity]

    def get_users(self) -> List[MockNetworkUser]:
        return self.__entities[MockNetworkEntities.MockNetworkUserEntity]

    def dump_devices(self) -> List[dict]:
        return [mock_utils.recursive_remove_none(device.to_dict()) for device in self.get_devices()]

    def dump_users(self) -> List[dict]:
        return [mock_utils.recursive_remove_none(user.to_dict()) for user in self.get_users()]

    def create_entities(
            self,
            entity_type: MockNetworkEntities,
            amount: int,
            entity_generator: callable,
            stage_name: str = None
    ):
        """
        create entities according to an entity generator function.
        :param MockNetworkEntities entity_type: the type of the given entity
        :param int amount: the amount of entities
        :param entity_generator: function(i, network, entity)
        :param stage_name: optional name of stage for logging
        :return: the id's of the inserted devices
        """
        current_id = len(self.__entities[entity_type])
        for i in range(amount):
            entity = self.__entities_classes[entity_type](set(), set())
            entity_generator(i, self, entity)

            if i > 0 and i % 1000 == 0:
                print(f'[+] Generated {i} entities{(" in stage " + stage_name) if stage_name else ""}')

            self.__add_entity(entity_type, entity)

        return list(range(current_id, current_id + amount))

    def create_devices(self, amount: int, device_generator: callable, stage_name: str = None):
        return self.create_entities(MockNetworkEntities.MockNetworkDeviceEntity, amount, device_generator, stage_name)

    def create_users(self, amount: int, user_generator: callable, stage_name: str = None):
        return self.create_entities(MockNetworkEntities.MockNetworkUserEntity, amount, user_generator, stage_name)

    def update_entities(
            self, entity: MockNetworkEntities,
            ids: List[int],
            entity_generator: callable,
            *args,
            stage_name=None,
            **kwargs
    ):
        '''
        update entites according to an entity generator function.
        :param MockNetworkEntities entity: the type of the given entity
        :param int ids: the id's of the entities
        :param entity_generator: function(i, network, entity)
        :param stage_name: optional name of stage for logging
        :param args: args to pass to the updating function
        :param kwargs: extra params to pass to the updating function
        :return: the id's of the inserted devices
        '''
        for i, device_id in enumerate(ids):
            device = self.__entities[entity][device_id]
            entity_generator(device, *args, **kwargs)

            if i > 0 and i % 5000 == 0:
                print(f'[+] Updated {i} entities{(" in stage " + stage_name) if stage_name else ""}')

    def update_devices(self, ids: List[int], device_generator: callable, *args, stage_name=None, **kwargs):
        return self.update_entities(
            MockNetworkEntities.MockNetworkDeviceEntity, ids, device_generator, *args, stage_name=stage_name, **kwargs)

    def update_users(self, ids: List[int], user_generator: callable, *args, stage_name=None, **kwargs):
        return self.update_entities(
            MockNetworkEntities.MockNetworkUserEntity, ids, user_generator, *args, stage_name=stage_name, **kwargs)

    def update_param_by_stats(
            self,
            list_of_entities_ids: List[int],
            stats: dict,
            update_function: Callable,
            update_function_func: Callable,
    ):
        value = stats.get('value')
        items_type = stats.get('items-type')
        items = stats.get('items')

        # Update everything we have with the required value
        if value:
            print(f'{value}: {len(list_of_entities_ids)} entities will be updated')
            update_function(list_of_entities_ids, update_function_func, param=value)

        # Now, if we have subgroups, lets handle them
        if not items_type:
            return

        entities_index = 0
        for item in items:
            percentage = item.get('percentage')
            amount = item.get('amount')
            total_amount = amount if amount else int(len(list_of_entities_ids) * percentage)
            if items_type == 'groups':
                assert entities_index + total_amount <= len(list_of_entities_ids), 'items amount overflown!'
                selected_ids = list_of_entities_ids[entities_index:entities_index + total_amount]
            elif items_type == 'standalone':
                selected_ids = random.sample(list_of_entities_ids, k=total_amount)
            else:
                raise ValueError(f'Unknown items type {items_type}')

            self.update_param_by_stats(
                selected_ids,
                item['stats'],
                update_function,
                update_function_func
            )
            entities_index += total_amount

    def update_entities_by_properties(
            self, list_of_entities_ids: List[int],
            stats: dict,
            entity_type: MockNetworkEntities,
    ):
        for entity_property, entity_stats_list in stats.items():
            entities_with_property = [
                self.__entities[entity_type][entity_id] for entity_id in list_of_entities_ids
                if self.__entities[entity_type][entity_id].does_have_property(entity_property)
            ]
            entities_index = 0
            for entity_stats_group in entity_stats_list:
                percentage = entity_stats_group['percentage']
                total_amount = int(len(entities_with_property) * percentage)
                assert entities_index + total_amount <= len(entities_with_property), f'items amount overflown! ' \
                    f'last percentage is {percentage}'
                entity_stats_group_args = entity_stats_group.get('args') or ()
                entity_stats_group_kwargs = entity_stats_group.get('kwargs') or {}
                entity_stats_group_function = entity_stats_group['function']

                print(
                    f'{entity_property.name}: '
                    f'{len(entities_with_property[entities_index:entities_index + total_amount])} entities will be '
                    f'updated with {entity_stats_group_function}, {entity_stats_group_args}, '
                    f'{entity_stats_group_kwargs}'
                )
                for entity_to_update in entities_with_property[entities_index:entities_index + total_amount]:
                    entity_stats_group_function(
                        entity_to_update,
                        entity_property,
                        *entity_stats_group_args,
                        **entity_stats_group_kwargs
                    )

                entities_index += total_amount

    @staticmethod
    def add_properties_to_entity(entity: MockNetworkEntity, param):
        if isinstance(param, MockNetworkEntityProperties):
            param = [param]
        for param_i in param:
            entity.add_property(param_i)

    def set_devices_properties(self, list_of_devices_ids: List[int], stats: dict):
        self.update_param_by_stats(
            list_of_devices_ids, stats, self.update_devices, self.add_properties_to_entity
        )

    def set_users_properties(self, list_of_users_ids: List[int], stats: dict):
        self.update_param_by_stats(
            list_of_users_ids, stats, self.update_users, self.add_properties_to_entity
        )

    def set_devices_attributes(self, list_of_devices_ids: List[int], stats: dict):
        self.update_entities_by_properties(list_of_devices_ids, stats, MockNetworkEntities.MockNetworkDeviceEntity)

    def set_users_attributes(self, list_of_devices_ids: List[int], stats: dict):
        self.update_entities_by_properties(list_of_devices_ids, stats, MockNetworkEntities.MockNetworkUserEntity)
